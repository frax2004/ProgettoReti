from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.topo import Topo



''' 
      [Subnet: 10.0.0.0/24]                                    [Subnet 1: 192.168.1.0/24]

            H1      H2                                         
            |        |                         
            ----------[SW1] ----------- [SW2] ----------- [SW3]----------- H4
                        |                 |                 |
                        |                 |                 |
                      [SW4] ----------- [SW5] ----------- [SW6]
                        |                 |                 |
                        |                 |                 |
          H3----------[SW7] ----------- [SW8] ----------- [SW9]----------- H5

[Subnet 1: 11.0.0.0/24]                                         [Subnet 1: 10.8.1.0/24]                                               

''' 
class MyTopology(Topo):
    def __init__(self):
        Topo.__init__(self)
    
        # Coordinate per algoritmo A* (utilizzabili dal controller)
        self.coordsSwitch = {
            'SW1' : (2.0,2.0), 'SW2' : (3.0,2.0), 'SW3' : (4.0,2.0),
            'SW4' : (2.0,1.0), 'SW5' : (3.0,1.0), 'SW6' : (4.0,1.0),
            'SW7' : (2.0,0.0), 'SW8' : (3.0,0.0), 'SW9' : (4.0,0.0),
        }

        # IP degli host secondo le specifiche del PDF
        addresses = [
            '10.0.0.1/24',    # H1
            '10.0.0.2/24',    # H2
            '11.0.0.1/24',    # H3
            '192.168.1.1/24', # H4
            '10.8.1.1/24'     # H5
        ]

        # Creazione Host
        hosts = []
        for i in range(5):
            # Nota: aggiungiamo un defaultRoute (Gateway) per permettere il routing tra sottoreti
            # Usiamo l'indirizzo .254 come gateway fittizio che verrà gestito dal controller SDN
            gw = addresses[i].split('/')[0].rsplit('.', 1)[0] + '.254'
            h = self.addHost(f'h{i+1}', 
                             mac=f'00:00:00:00:00:0{i+1}', 
                             ip=addresses[i],
                             defaultRoute=f'via {gw}')
            hosts.append(h)

        # Creazione Switch
        switches = []
        # In MyTopology.py, cambia la riga della creazione switch:
        for i in range(1, 10):
            sw = self.addSwitch(f's{i}', cls=OVSKernelSwitch, protocols='OpenFlow13', failMode='secure')
            switches.append(sw)

        # --- LINK CORE (1Gbps, 5ms) ---
        link_config = {'bw': 1000, 'delay': '5ms'}
        
        # Link Orizzontali
        self.addLink(switches[0], switches[1], **link_config) # s1-s2
        self.addLink(switches[1], switches[2], **link_config) # s2-s3
        self.addLink(switches[3], switches[4], **link_config) # s4-s5
        self.addLink(switches[4], switches[5], **link_config) # s5-s6
        self.addLink(switches[6], switches[7], **link_config) # s7-s8
        self.addLink(switches[7], switches[8], **link_config) # s8-s9

        # Link Verticali
        self.addLink(switches[0], switches[3], **link_config) # s1-s4
        self.addLink(switches[1], switches[4], **link_config) # s2-s5
        self.addLink(switches[2], switches[5], **link_config) # s3-s6
        self.addLink(switches[3], switches[6], **link_config) # s4-s7
        self.addLink(switches[4], switches[7], **link_config) # s5-s8
        self.addLink(switches[5], switches[8], **link_config) # s6-s9

        # --- LINK HOST-SWITCH (Parametri specifici PDF) ---
        self.addLink(hosts[0], switches[0], bw=100, delay='0.05ms') # H1-SW1
        self.addLink(hosts[1], switches[0], bw=100, delay='0.05ms') # H2-SW1
        self.addLink(hosts[3], switches[2], bw=100, delay='1ms')    # H4-SW3
        self.addLink(hosts[2], switches[6], bw=5,   delay='0.5ms')  # H3-SW7
        self.addLink(hosts[4], switches[8], bw=200, delay='1ms')    # H5-SW9

def topology():
    # Definiamo il controller remoto (Ryu)
    c0 = RemoteController('c0', ip='127.0.0.1', port=6633)

    net = Mininet(
        topo=MyTopology(),
        controller=c0,
        link=TCLink,
        autoSetMacs=True
    )

    info('*** Starting network\n')
    net.start()

    print("\n=== Avvio server iperf su tutti gli host (Punto 11-12) ===")
    for host in net.hosts:
        # Formato richiesto dal punto 12 del PDF per il log CSV
        host.cmd(f'iperf -s -y C >> {host.name}_log.csv &')
        print(f"Server iperf in ascolto su {host.name} (Log: {host.name}_log.csv)")
    
    print("\n=== Avvio Flask REST API su H1 (Punto 5) ===")
    h1 = net.get('h1')
    # Assicurati che flask_api.py sia nella stessa cartella
    h1.cmd('python3 MyServerFlask.py &')
    print("API Flask avviata su H1 (IP: 10.0.0.1)")
    
    info('\n*** Network is ready. Entrando in CLI...\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()