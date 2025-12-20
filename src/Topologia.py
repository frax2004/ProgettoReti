from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.Topo import Topo


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
        #Coordinate fittizie per per la griglia 3x3
        Topo.__init__(self)
    
        self.coordsSwitch = {
            'SW1' : (2.0,2.0), 'SW2' : (3.0,2.0),'SW3' : (4.0,2.0),
            'SW4' : (2.0,1.0), 'SW5' : (3.0,1.0),'SW6' : (4.0,1.0),
            'SW7' : (2.0,0.0), 'SW8' : (3.0,0.0),'SW9' : (4.0,0.0),
        }

        self.coordsHost = {
            'H1' : (1.0,3.0), 'H2' : (0.0,3.0), 'H3' : (0.5,0.0),
            'H4' : (6.0,2.0), 'H5' : (6.0,0.0),
        }

        #aggiunta degli Host
        addresses = (
            '10.0.0.0/24'
            '10.0.0.0/24'
            '11.0.0.0/24'
            '192.168.1.0/24'
            '10.8.1.0/24'
        )

        hosts = []
        for i in range (1,6):
            hosts.append(self.addHost(f'H{i}', mac=f'00:00:00:00:00:0{i}',ip = addresses[i]))

        # Add switches
        switches = []
        for i in range (1,10):
            switches.append(self.addSwitch(f'SW{i}'))

        # Add links  
        # #BW in Mbps, delay in ms

        link_coreBW=1024
        link_coredelay='5ms' 
        #link orizzonatali
        self.addLink(switches[0], switches[1],cls=TCLink,bw=link_coreBW,delay=link_coredelay) 
        self.addLink(switches[1], switches[2],cls=TCLink,bw=link_coreBW,delay=link_coredelay) 
        self.addLink(switches[3], switches[4],cls=TCLink,bw=link_coreBW,delay=link_coredelay)
        self.addLink(switches[4], switches[5],cls=TCLink,bw=link_coreBW,delay=link_coredelay)
        self.addLink(switches[6], switches[7],cls=TCLink,bw=link_coreBW,delay=link_coredelay)
        self.addLink(switches[7], switches[8],cls=TCLink,bw=link_coreBW,delay=link_coredelay)

        #link verticali
        self.addLink(switches[0], switches[3],cls=TCLink,bw=link_coreBW,delay=link_coredelay) 
        self.addLink(switches[1], switches[4],cls=TCLink,bw=link_coreBW,delay=link_coredelay) 
        self.addLink(switches[2], switches[5],cls=TCLink,bw=link_coreBW,delay=link_coredelay)
        self.addLink(switches[3], switches[6],cls=TCLink,bw=link_coreBW,delay=link_coredelay)
        self.addLink(switches[4], switches[7],cls=TCLink,bw=link_coreBW,delay=link_coredelay)
        self.addLink(switches[5], switches[8],cls=TCLink,bw=link_coreBW,delay=link_coredelay)

        #link tra hosts e switches
        self.addLink(hosts[0], switches[0],cls = TCLink, bw = 100, delay = '0.05ms')
        self.addLink(hosts[1], switches[0],cls = TCLink, bw = 100, delay = '0.05ms')
        self.addLink(hosts[3], switches[2],cls = TCLink, bw = 100, delay = '1ms')
        self.addLink(hosts[2], switches[6],cls = TCLink, bw = 5, delay = '0.5ms')
        self.addLink(hosts[4], switches[8],cls = TCLink, bw = 200, delay = '1ms')

def topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, autoSetMacs=True, topo=MyTopology(),link = TCLink)

    c0 = RemoteController('c0')

    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()
if __name__ == '__main__':
    setLogLevel('info')
    topology()






