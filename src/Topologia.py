from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, UserSwitch
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
    
        # Coordinate (utilizzate per interfacce grafiche come MiniEdit, qui opzionali)
        self.coordsSwitch = {
            'SW1' : (2.0,2.0), 'SW2' : (3.0,2.0),'SW3' : (4.0,2.0),
            'SW4' : (2.0,1.0), 'SW5' : (3.0,1.0),'SW6' : (4.0,1.0),
            'SW7' : (2.0,0.0), 'SW8' : (3.0,0.0),'SW9' : (4.0,0.0),
        }

        # Corretto: Aggiunte le virgole per creare una lista/tupla
        # Corretto: Assegnati IP specifici per gli host (.1) invece dell'indirizzo di rete (.0)
        addresses = [
            '10.0.0.1/24',
            '10.0.0.2/24',
            '11.0.0.1/24',
            '192.168.1.1/24',
            '10.8.1.1/24'
        ]

        # Aggiunta degli Host
        hosts = []
        for i in range(5): # range(5) genera 0, 1, 2, 3, 4
            h = self.addHost(f'H{i+1}', mac=f'00:00:00:00:00:0{i+1}', ip=addresses[i])
            hosts.append(h)

        # Aggiunta Switch
        switches = []
        for i in range(1, 10):
            switches.append(self.addSwitch(f'SW{i}'))

        # Parametri link core
        link_coreBW = 1000
        link_coredelay = '5ms' 

        # Link orizzontali (switches[0] è SW1, switches[1] è SW2...)
        self.addLink(switches[0], switches[1], cls=TCLink, bw=link_coreBW, delay=link_coredelay) 
        self.addLink(switches[1], switches[2], cls=TCLink, bw=link_coreBW, delay=link_coredelay) 
        self.addLink(switches[3], switches[4], cls=TCLink, bw=link_coreBW, delay=link_coredelay)
        self.addLink(switches[4], switches[5], cls=TCLink, bw=link_coreBW, delay=link_coredelay)
        self.addLink(switches[6], switches[7], cls=TCLink, bw=link_coreBW, delay=link_coredelay)
        self.addLink(switches[7], switches[8], cls=TCLink, bw=link_coreBW, delay=link_coredelay)

        # Link verticali
        self.addLink(switches[0], switches[3], cls=TCLink, bw=link_coreBW, delay=link_coredelay) 
        self.addLink(switches[1], switches[4], cls=TCLink, bw=link_coreBW, delay=link_coredelay) 
        self.addLink(switches[2], switches[5], cls=TCLink, bw=link_coreBW, delay=link_coredelay)
        self.addLink(switches[3], switches[6], cls=TCLink, bw=link_coreBW, delay=link_coredelay)
        self.addLink(switches[4], switches[7], cls=TCLink, bw=link_coreBW, delay=link_coredelay)
        self.addLink(switches[5], switches[8], cls=TCLink, bw=link_coreBW, delay=link_coredelay)

        # Link tra hosts e switches (Nota: hosts[0] è H1, ecc.)
        self.addLink(hosts[0], switches[0], cls=TCLink, bw=100, delay='0.05ms') # H1-SW1
        self.addLink(hosts[1], switches[0], cls=TCLink, bw=100, delay='0.05ms') # H2-SW1
        self.addLink(hosts[3], switches[2], cls=TCLink, bw=100, delay='1ms')    # H4-SW3
        self.addLink(hosts[2], switches[6], cls=TCLink, bw=5, delay='0.5ms')    # H3-SW7
        self.addLink(hosts[4], switches[8], cls=TCLink, bw=200, delay='1ms')   # H5-SW9


def topology():
    net = Mininet(controller=None, switch=OVSKernelSwitch, autoSetMacs=True, topo=MyTopology(), link=TCLink)

    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
