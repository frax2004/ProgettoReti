from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.topo import Topo

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
        self.addLink(h1, s1)
        self.addLink(h2, s1)

def topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, autoSetMacs=True, topo=MyTopology())

    # Add controller
    #c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    c0 = RemoteController('c0', ip='127.0.0.1', port=6653, protocols="OpenFlow13")

    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()

