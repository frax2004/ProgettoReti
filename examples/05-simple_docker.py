from mininet.net import Mininet, Containernet
from mininet.node import RemoteController, Controller
from mininet.cli import CLI

from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController

img_name="frr:alpine-bb9d4c1b57"

#img_name="ubuntu:trusty"
# Creazione dell'oggetto rete
net = Containernet()


d = []

# Creazione dello switch
s1 = net.addSwitch( 's1' )
# Creazione dell'handler del controller remoto che si connettera' a Ryu
c0 = net.addController( 'c0', controller=RemoteController, ip='127.0.0.1', port=6653 )



h1 = net.addHost('h1', mac='00:00:00:00:00:01',ip=f'192.168.1.11')
h2 = net.addHost('h2', mac='00:00:00:00:00:02',ip=f'192.168.1.12')

#h3 = net.addDocker('h3', ip='10.0.0.3', dimage=img_name)
#h4 = net.addDocker('h4', ip='10.0.0.4', dimage=img_name)

# Creazione dei link
net.addLink( h1, s1 )
net.addLink( h2, s1 )
#net.addLink( h3, s1 )
#net.addLink( h4, s1 )


for i in range(0,4):    
    d.append(net.addDocker(f'd{i+1}', mac=f'00:00:00:00:00:0{i+1}', ip=f'10.0.0.25{i+1}', dimage=img_name) )
    net.addLink( d[i], s1 )




# Attivazione della rete emulata
net.start()
# Escuzione del comando ping (fallisce)
#print(h1.cmd( 'ping -c1', h2.IP() ))
# Apertura della Command Line Interface (CTRL + d per usire)
CLI( net )
# Distruzione della rete emulata
net.stop()
