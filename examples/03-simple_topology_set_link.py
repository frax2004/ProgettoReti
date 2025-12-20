from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.topo import Topo
from mininet.link import TCLink

class MyTopology(Topo):
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Add hosts
        h1 = self.addHost('h1', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', mac='00:00:00:00:00:02')

        # Add switches
        s1 = self.addSwitch('s1')

        # Add links
        self.addLink(h1, s1,cls=TCLink,bw=1,delay="5ms") #BW in Mbps, delay in ms
        self.addLink(h2, s1,cls=TCLink,bw=1,delay="6ms") #BW in Mbps, delay in ms
        #self.addLink(h1, s1) #BW in Mbps, delay in ms
        #self.addLink(h2, s1) #BW in Mbps, delay in ms

def topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, autoSetMacs=True, topo=MyTopology(),link = TCLink)

    # Add controller
    #c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    c0 = RemoteController('c0', ip='127.0.0.1', port=6653, protocols="OpenFlow13")

    info('*** Starting network\n')
    net.start()

    info("*** ADD s1 flows")

    net.get("s1").dpctl('add-flow', 'arp,in_port=1,actions=output:2')
    net.get("s1").dpctl('add-flow', 'arp,in_port=2,actions=output:1')
    net.get("s1").dpctl('add-flow', 'ip,nw_dst=10.0.0.1,actions=output:1')
    net.get("s1").dpctl('add-flow', 'ip,nw_dst=10.0.0.2,actions=output:2')

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()

