from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4
from ryu.topology.api import get_switch, get_link
from ryu.topology import event
from collections import defaultdict
import time

# --- CONFIGURAZIONE ---
ROUTER_MAC = '00:00:00:00:fe:fe'

class L3Router(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L3Router, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        
        self.arp_table = {}
        self.adjacency = defaultdict(lambda: defaultdict(lambda: None))
        self.switches = []
        self.datapaths = {}

    # --- FUNZIONE DI STAMPA TOPOLOGIA ---
    def print_current_topology(self):
        """
        Stampa la topologia corrente in modo leggibile
        """
        sorted_switches = sorted(self.switches)
        num_links = sum(len(n) for n in self.adjacency.values()) // 2 # diviso 2 perché i link sono bidirezionali

        print("\n" + "="*60)
        print(f" [TOPOLOGY UPDATE] Switches: {len(sorted_switches)} | Links Detected: {num_links}")
        print("="*60)
        
        if not sorted_switches:
            print(" Waiting for switches...")
            return

        for dpid in sorted_switches:
            # Crea una stringa con i vicini
            neighbors = []
            if dpid in self.adjacency:
                for peer_dpid, port_no in self.adjacency[dpid].items():
                    neighbors.append(f"-> sw{peer_dpid} (p:{port_no})")
            
            # Formattazione per allineamento
            neighbors_str = ", ".join(neighbors)
            print(f" SW{dpid:<2} connects to: {neighbors_str}")
        
        print("="*60 + "\n")

    # --- TOPOLOGY DISCOVERY ---
    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave, 
                 event.EventPortAdd, event.EventPortDelete, 
                 event.EventLinkAdd, event.EventLinkDelete])
    def update_topology(self, ev):
        # Aggiorna lista switch
        switch_list = get_switch(self.topology_api_app, None)
        self.switches = [sw.dp.id for sw in switch_list]
        self.datapaths = {sw.dp.id: sw.dp for sw in switch_list}
        
        # Aggiorna adiacenze
        link_list = get_link(self.topology_api_app, None)
        
        # Salviamo la vecchia topologia per vedere se è cambiato qualcosa prima di stampare (per evitare spam inutile)
        # Ma per sicurezza ristampiamo sempre quando c'è un evento
        self.adjacency.clear()
        for link in link_list:
            self.adjacency[link.src.dpid][link.dst.dpid] = link.src.port_no
            self.adjacency[link.dst.dpid][link.src.dpid] = link.dst.port_no
            
        # CHIAMA LA FUNZIONE DI STAMPA
        self.print_current_topology()

    # --- DIJKSTRA ---
    def get_path(self, src, dst):
        if src == dst:
            return [src]
            
        distances = {d: float('inf') for d in self.switches}
        previous = {d: None for d in self.switches}
        distances[src] = 0
        Q = set(self.switches)

        while Q:
            u = min(Q, key=lambda x: distances[x])
            Q.remove(u)
            if distances[u] == float('inf'): break
            if u == dst: break

            for v in self.adjacency[u]:
                if v in Q:
                    alt = distances[u] + 1
                    if alt < distances[v]:
                        distances[v] = alt
                        previous[v] = u

        path = []
        u = dst
        while u is not None:
            path.insert(0, u)
            u = previous[u]
        return path if path and path[0] == src else None

    # --- ARP PROBE (SAFE FLOOD) ---
    def send_arp_probe(self, target_ip):
        # print(f"--- Sending ARP Probe for {target_ip} ---")
        e = ethernet.ethernet(dst='ff:ff:ff:ff:ff:ff', src=ROUTER_MAC, ethertype=ether_types.ETH_TYPE_ARP)
        a = arp.arp(opcode=arp.ARP_REQUEST, src_mac=ROUTER_MAC, src_ip='0.0.0.0',
                    dst_mac='00:00:00:00:00:00', dst_ip=target_ip)
        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()

        for dpid in self.switches:
            dp = self.datapaths[dpid]
            # Filtro base: inviamo flood, ma la logica del routing eviterà loop sui pacchetti IP
            # L'ARP storm è mitigato dal fatto che è un probe controllato
            non_edge_ports = set(self.adjacency[dpid].values())
            
            sw_obj_list = get_switch(self.topology_api_app, dpid)
            if not sw_obj_list: continue
            sw_obj = sw_obj_list[0]
            
            actions = []
            for port in sw_obj.ports:
                if port.port_no > ofproto_v1_3.OFPP_MAX: continue
                # Invia SOLO se la porta non è collegata a un altro switch (Edge Port)
                if port.port_no not in non_edge_ports:
                    actions.append(dp.ofproto_parser.OFPActionOutput(port.port_no))
            
            if actions:
                out = dp.ofproto_parser.OFPPacketOut(datapath=dp, buffer_id=dp.ofproto.OFP_NO_BUFFER,
                                          in_port=dp.ofproto.OFPP_CONTROLLER, actions=actions, data=p.data)
                dp.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        if eth.ethertype == ether_types.ETH_TYPE_LLDP: return

        # --- GESTIONE ARP ---
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            a = pkt.get_protocol(arp.arp)
            self.arp_table[a.src_ip] = (dpid, in_port, eth.src)

            if a.opcode == arp.ARP_REQUEST:
                pkt_reply = packet.Packet()
                pkt_reply.add_protocol(ethernet.ethernet(dst=eth.src, src=ROUTER_MAC, ethertype=ether_types.ETH_TYPE_ARP))
                pkt_reply.add_protocol(arp.arp(opcode=arp.ARP_REPLY, 
                                             src_mac=ROUTER_MAC, src_ip=a.dst_ip,
                                             dst_mac=eth.src, dst_ip=a.src_ip))
                pkt_reply.serialize()
                out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=ofproto_v1_3.OFPP_CONTROLLER, 
                                          actions=[parser.OFPActionOutput(in_port)], data=pkt_reply.data)
                dp.send_msg(out)
            return

        # --- GESTIONE IP (ROUTING L3) ---
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt.src not in self.arp_table:
                self.arp_table[ip_pkt.src] = (dpid, in_port, eth.src)

            if ip_pkt.dst in self.arp_table:
                dst_dpid, dst_port, dst_mac = self.arp_table[ip_pkt.dst]
                path_nodes = self.get_path(dpid, dst_dpid)
                
                if not path_nodes: return

                # DEFINIAMO L'AZIONE TTL UNA VOLTA PER TUTTE
                dec_ttl = parser.OFPActionDecNwTtl()

                # CASO 1: Destinazione sullo stesso switch
                if len(path_nodes) == 1:
                     actions = [dec_ttl, # <--- AGGIUNTO QUI
                                parser.OFPActionSetField(eth_src=ROUTER_MAC),
                                parser.OFPActionSetField(eth_dst=dst_mac),
                                parser.OFPActionOutput(dst_port)]
                     match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ip_pkt.dst)
                     dp.send_msg(parser.OFPFlowMod(datapath=dp, match=match, priority=10, instructions=[parser.OFPInstructionActions(ofproto_v1_3.OFPIT_APPLY_ACTIONS, actions)]))
                     dp.send_msg(parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data))
                     return

                # CASO 2: Percorso Multi-Hop
                
                # A. Configurazione PRIMO switch (Ingress)
                next_node = path_nodes[1]
                out_port = self.adjacency[dpid][next_node]
                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ip_pkt.dst)
                
                # <--- AGGIUNTO QUI: Il primo switch deve decrementare!
                actions = [dec_ttl, parser.OFPActionOutput(out_port)] 
                
                dp.send_msg(parser.OFPFlowMod(datapath=dp, match=match, priority=10, instructions=[parser.OFPInstructionActions(ofproto_v1_3.OFPIT_APPLY_ACTIONS, actions)]))

                # B. Configurazione SWITCH SUCCESSIVI
                for i in range(1, len(path_nodes)):
                    curr = path_nodes[i]
                    curr_dp = self.datapaths[curr]
                    
                    if i == len(path_nodes) - 1:
                        # Ultimo switch (Egress)
                        curr_actions = [
                                        dec_ttl, # <--- C'era, OK.
                                        parser.OFPActionSetField(eth_src=ROUTER_MAC),
                                        parser.OFPActionSetField(eth_dst=dst_mac),
                                        parser.OFPActionOutput(dst_port)]
                    else:
                        # Switch Intermedi (Transit)
                        nxt = path_nodes[i+1]
                        # <--- AGGIUNTO QUI: FONDAMENTALE PER I SALTI INTERMEDI
                        curr_actions = [dec_ttl, parser.OFPActionOutput(self.adjacency[curr][nxt])]
                    
                    curr_dp.send_msg(parser.OFPFlowMod(datapath=curr_dp, match=match, priority=10, instructions=[parser.OFPInstructionActions(ofproto_v1_3.OFPIT_APPLY_ACTIONS, curr_actions)]))

                # C. Invia il pacchetto originale (PacketOut)
                dp.send_msg(parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data))
            else:
                self.send_arp_probe(ip_pkt.dst)


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(parser.OFPFlowMod(datapath=dp, match=match, priority=0, instructions=inst))