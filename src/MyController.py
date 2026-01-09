from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, arp
from ryu.lib import hub

import time

class Project10Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Project10Controller, self).__init__(*args, **kwargs)
        
        # Coordinate switch (DPID) per l'euristica di A*
        self.coords = {
            1: (2.0, 2.0), 2: (3.0, 2.0), 3: (4.0, 2.0),
            4: (2.0, 1.0), 5: (3.0, 1.0), 6: (4.0, 1.0),
            7: (2.0, 0.0), 8: (3.0, 0.0), 9: (4.0, 0.0)
        }

        # Mappa IP -> (DPID dello switch a cui è collegato, porta dello switch)
        self.host_map = {
            '10.0.0.1': (1, 1),   # H1 su SW1 porta 1
            '10.0.0.2': (1, 2),   # H2 su SW1 porta 2
            '11.0.0.1': (7, 3),   # H3 su SW7 porta 3
            '192.168.1.1': (3, 3),# H4 su SW3 porta 3
            '10.8.1.1': (9, 3)    # H5 su SW9 porta 3
        }

        # Grafo: { sorgente: { destinazione: porta_uscita } }
        # Basato sui link della tua topologia Mininet
        self.adj = {
            1: {2: 3, 4: 4}, 2: {1: 3, 3: 4, 5: 5}, 3: {2: 4, 6: 5},
            4: {1: 3, 5: 4, 7: 5}, 5: {2: 3, 4: 4, 6: 5, 8: 6}, 6: {3: 3, 5: 4, 9: 5},
            7: {4: 4, 8: 5}, 8: {7: 4, 5: 5, 9: 6}, 9: {8: 4, 6: 5}
        }

        self.link_stats = {}      # { (dpid, port): last_byte_count }
        self.link_weights = {}    # { (u, v): peso }
        self.datapaths = {}
        
        # Inizializza tutti i pesi dei link a 1 (stato di riposo)
        for u in self.adj:
            for v in self.adj[u]:
                self.link_weights[(u, v)] = 1.0

        self.monitor_thread = hub.spawn(self._monitor)

    # --- SEZIONE MONITORAGGIO E PESI ---

    def _monitor(self):
        """ Invia richieste di statistiche periodicamente """
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(5)

    def _request_stats(self, datapath):
        self.logger.debug('Inviando richiesta statistiche a %016x', datapath.id)
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def compute_update_weights(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id
        body = msg.body

        for stat in body:
            port_no = stat.port_no
            if port_no > 10: continue # Ignora porte non fisiche

            key = (dpid, port_no)
            if key in self.link_stats:
                # Calcola byte passati nell'intervallo (5 sec)
                byte_delta = stat.tx_bytes - self.link_stats[key]
                # Formula peso: 1 + (traffico_in_KB). 
                # Più traffico c'è, più il peso sale (es. 10MB -> peso ~10000)
                new_weight = 1.0 + (byte_delta / 1024.0)
                
                # Trova quale switch è collegato a questa porta e aggiorna peso
                for target_dpid, out_port in self.adj[dpid].items():
                    if out_port == port_no:
                        self.link_weights[(dpid, target_dpid)] = new_weight
            
            self.link_stats[key] = stat.tx_bytes
    # --- SEZIONE ALGORITMI DI ROUTING ---

    def get_heuristic(self, u, v):
        """ Calcola la distanza euclidea tra switch u e v per A* """
        x1, y1 = self.coords[u]
        x2, y2 = self.coords[v]
        return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

    def dijkstra(self, src, dst):
        """ Ritorna il percorso ottimo come lista di DPID """
        distances = {node: float('inf') for node in self.adj}
        distances[src] = 0
        previous = {node: None for node in self.adj}
        nodes = list(self.adj.keys())

        while nodes:
            # Trova il nodo con distanza minima
            u = min(nodes, key=lambda node: distances[node])
            nodes.remove(u)
            if u == dst or distances[u] == float('inf'): break

            for v in self.adj[u]:
                cost = self.link_weights.get((u, v), 1)
                alt = distances[u] + cost
                if alt < distances[v]:
                    distances[v] = alt
                    previous[v] = u

        return self._reconstruct_path(previous, src, dst)

    # def a_star(self, src, dst):
    #     """ A* : Dijkstra + Euristica (distanza euclidea) """
    #     open_set = [src]
    #     came_from = {}
    #     g_score = {node: float('inf') for node in self.adj}
    #     g_score[src] = 0
    #     f_score = {node: float('inf') for node in self.adj}
    #     f_score[src] = self.get_heuristic(src, dst)

    #     while open_set:
    #         current = min(open_set, key=lambda node: f_score[node])
    #         if current == dst:
    #             return self._reconstruct_path(came_from, src, dst)

    #         open_set.remove(current)
    #         for neighbor in self.adj[current]:
    #             weight = self.link_weights.get((current, neighbor), 1)
    #             tentative_g = g_score[current] + weight
                
    #             if tentative_g < g_score[neighbor]:
    #                 came_from[neighbor] = current
    #                 g_score[neighbor] = tentative_g
    #                 f_score[neighbor] = g_score[neighbor] + self.get_heuristic(neighbor, dst)
    #                 if neighbor not in open_set:
    #                     open_set.append(neighbor)
    #     return []

    def _reconstruct_path(self, previous, src, dst):
        path = []
        curr = dst
        while curr is not None:
            path.append(curr)
            curr = previous.get(curr)
        return path[::-1] if path[-1] == src else []

    # --- SEZIONE GESTIONE TRAFFICO ---

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_handler(self, ev):
        """ Installazione regola di default Table-Miss """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath
        
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """ Helper per installare flow mod negli switch """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

   @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignora pacchetti LLDP o IPv6 per pulizia log
        if eth.ethertype in [0x88cc, 0x86dd]:
            return

        if eth.ethertype == 0x0806: 
            self._handle_arp(dp, in_port, pkt)
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            src_ip, dst_ip = ip_pkt.src, ip_pkt.dst
            if dst_ip not in self.host_map: return

            dst_sw, final_port = self.host_map[dst_ip]
            
            # Recuperiamo il MAC reale dell'host di destinazione (00:00:00:00:00:0X)
            dst_mac = f"00:00:00:00:00:0{dst_ip.split('.')[-1][-1]}" # Prende l'ultima cifra dell'IP
            
            # Calcoliamo il percorso A* dallo switch attuale alla destinazione
            path = dijkstra(dpid, dst_sw)
            if not path: return

            self.logger.info(f"ROUTE L3: {src_ip} -> {dst_ip} | Path: {path} | Set DstMAC: {dst_mac}")

            # Installiamo i flussi su tutti gli switch del percorso
            for i in range(len(path)):
                sw_id = path[i]
                if sw_id not in self.datapaths: continue
                sw_dp = self.datapaths[sw_id]
                
                # Uscita verso lo switch successivo o verso l'host finale
                p_out = final_port if sw_id == dst_sw else self.adj[sw_id][path[i+1]]
                
                # AZIONI: Se siamo sull'ultimo switch, cambiamo il MAC di destinazione con quello dell'host
                actions = []
                if sw_id == dst_sw:
                    actions.append(sw_dp.ofproto_parser.OFPActionSetField(eth_dst=dst_mac))
                
                actions.append(sw_dp.ofproto_parser.OFPActionOutput(p_out))
                
                # Installazione regola per questo IP di destinazione
                match = sw_dp.ofproto_parser.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
                self.add_flow(sw_dp, 10, match, actions)

            # Inoltro immediato del pacchetto corrente
            # Applichiamo il cambio MAC anche qui se siamo già sullo switch finale
            out_actions = []
            if dpid == dst_sw:
                out_actions.append(parser.OFPActionSetField(eth_dst=dst_mac))
            
            out_port = final_port if dpid == dst_sw else self.adj[dpid][path[1]]
            out_actions.append(parser.OFPActionOutput(out_port))
            
            out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=out_actions, data=msg.data)
            dp.send_msg(out)

    def _handle_arp(self, datapath, in_port, pkt):
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt.opcode != arp.ARP_REQUEST:
            return

        target_ip = arp_pkt.dst_ip
        # Rispondi se è un host noto O se è un gateway (.254)
        if target_ip in self.host_map or target_ip.endswith('.254'):
            # Se è un gateway, diamo un MAC fittizio fisso
            if target_ip.endswith('.254'):
                target_mac = "00:00:00:00:00:FE"
            else:
                last_digit = target_ip.split('.')[-1]
                target_mac = f"00:00:00:00:00:0{last_digit}"

            self.logger.info(f"ARP Request per {target_ip} (SW{datapath.id}): Rispondo con {target_mac}")
            
            pkt_reply = packet.Packet()
            pkt_reply.add_protocol(ethernet.ethernet(ethertype=0x0806, dst=arp_pkt.src_mac, src=target_mac))
            pkt_reply.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=target_mac, src_ip=target_ip,
                                          dst_mac=arp_pkt.src_mac, dst_ip=arp_pkt.src_ip))
            pkt_reply.serialize()
            
            actions = [datapath.ofproto_parser.OFPActionOutput(in_port)]
            out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=0xffffffff,
                                  in_port=datapath.ofproto.OFPP_CONTROLLER, actions=actions, data=pkt_reply.data)
            datapath.send_msg(out)