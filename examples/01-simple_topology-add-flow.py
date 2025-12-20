from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI

# Creazione dell'oggetto rete
net = Mininet()
# Creazione dei nodi Host
#h1 = net.addHost( 'h1' )
#h2 = net.addHost( 'h2' )

h1 = net.addHost('h1', mac='00:00:00:00:00:01')
h2 = net.addHost('h2', mac='00:00:00:00:00:02')
h3 = net.addHost('h3', mac='00:00:00:00:00:03')

# Creazione dello switch
s1 = net.addSwitch( 's1' )
# Creazione dell'hndler del controller remoto che si connettera' a Ryu
#c0 = net.addController( 'c0', controller=RemoteController, ip='127.0.0.1', port=6653 )
c0 = net.addController( 'c0', controller=Controller)
# Creazione dei link
net.addLink( h1, s1 )
net.addLink( h2, s1 )
net.addLink( h3, s1 )
# Attivazione della rete emulata
net.start()

#ARP flooding
s1.dpctl('add-flow', 'priority=65535,arp,actions=output:flood') 
s1.dpctl('add-flow', 'ip,nw_dst=10.0.0.1,actions=output:1')
s1.dpctl('add-flow', 'ip,nw_dst=10.0.0.2,actions=output:2')
s1.dpctl('add-flow', 'ip,nw_dst=10.0.0.3,actions=output:3')

CLI( net )
# Distruzione della rete emulata
net.stop()
