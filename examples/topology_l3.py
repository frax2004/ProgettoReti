import threading
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

def run():
    # Usa OVSKernelSwitch
    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSKernelSwitch)

    # --- HOSTS (Subnet separate) ---
    h1 = net.addHost("h1", ip="10.1.0.1/24", mac="00:00:00:00:00:01", defaultRoute='via 10.1.0.254')
    h2 = net.addHost("h2", ip="10.2.0.1/24", mac="00:00:00:00:00:02", defaultRoute='via 10.2.0.254')
    h3 = net.addHost("h3", ip="10.3.0.1/24", mac="00:00:00:00:00:03", defaultRoute='via 10.3.0.254')

    # --- SERVERS ---
    # Gruppo 1
    s1 = net.addHost("s1", ip="192.168.10.1/24", mac="00:00:00:00:00:04", defaultRoute='via 192.168.10.254')
    s2 = net.addHost("s2", ip="192.168.10.2/24", mac="00:00:00:00:00:05", defaultRoute='via 192.168.10.254')
    s3 = net.addHost("s3", ip="192.168.10.3/24", mac="00:00:00:00:00:06", defaultRoute='via 192.168.10.254')
    # Gruppo 2
    s4 = net.addHost("s4", ip="192.168.20.1/24", mac="00:00:00:00:00:07", defaultRoute='via 192.168.20.254')
    s5 = net.addHost("s5", ip="192.168.20.2/24", mac="00:00:00:00:00:08", defaultRoute='via 192.168.20.254')
    s6 = net.addHost("s6", ip="192.168.20.3/24", mac="00:00:00:00:00:09", defaultRoute='via 192.168.20.254')
    # Gruppo 3
    s7 = net.addHost("s7", ip="172.16.0.1/24", mac="00:00:00:00:00:10", defaultRoute='via 172.16.0.254')
    s8 = net.addHost("s8", ip="172.16.0.2/24", mac="00:00:00:00:00:11", defaultRoute='via 172.16.0.254')
    s9 = net.addHost("s9", ip="172.16.0.3/24", mac="00:00:00:00:00:12", defaultRoute='via 172.16.0.254')
    # Gruppo 4
    s10 = net.addHost("s10", ip="172.16.1.1/24", mac="00:00:00:00:00:13", defaultRoute='via 172.16.1.254')
    s11 = net.addHost("s11", ip="172.16.1.2/24", mac="00:00:00:00:00:14", defaultRoute='via 172.16.1.254')
    s12 = net.addHost("s12", ip="172.16.1.3/24", mac="00:00:00:00:00:15", defaultRoute='via 172.16.1.254')

    # Switches
    switches = [net.addSwitch(f'sw{i}') for i in range(1, 17)]
    sw1, sw2, sw3, sw4, sw5, sw6, sw7, sw8, sw9, sw10, sw11, sw12, sw13, sw14, sw15, sw16 = switches

    net.addController("C0", controller=RemoteController, ip="127.0.0.1", port=6633)

    linkopt5 = dict(bw=5, delay='1ms', cls=TCLink)
    linkopt10 = dict(bw=10, delay='1ms', cls=TCLink)
    linkopt15 = dict(bw=15, delay='1ms', cls=TCLink)
    linkopt50 = dict(bw=50, delay='1ms', cls=TCLink)
    linkopt100 = dict(bw=100, delay='1ms', cls=TCLink)

    # Links (Invariati)
    net.addLink(sw1, s1, **linkopt100)
    net.addLink(sw1, s2, **linkopt100)
    net.addLink(sw1, sw3, **linkopt50)
    net.addLink(sw1, sw4, **linkopt100)
    net.addLink(sw2, s3, **linkopt100)
    net.addLink(sw2, s4, **linkopt100)
    net.addLink(sw2, sw4, **linkopt50)
    net.addLink(sw4, sw14, **linkopt5)
    net.addLink(sw5, s5, **linkopt100)
    net.addLink(sw5, s6, **linkopt100)
    net.addLink(sw5, sw7, **linkopt50)
    net.addLink(sw5, sw8, **linkopt100)
    net.addLink(sw6, s7, **linkopt100)
    net.addLink(sw6, s8, **linkopt100)
    net.addLink(sw6, sw8, **linkopt50)
    net.addLink(sw7, sw13, **linkopt15)
    net.addLink(sw8, sw15, **linkopt10)
    net.addLink(sw9, s9, **linkopt100)
    net.addLink(sw9, s10, **linkopt100)
    net.addLink(sw9, sw11, **linkopt50)
    net.addLink(sw9, sw12, **linkopt100)
    net.addLink(sw10, s11, **linkopt100)
    net.addLink(sw10, s12, **linkopt100)
    net.addLink(sw10, sw12, **linkopt50)
    net.addLink(sw11, sw14, **linkopt10)
    net.addLink(sw12, sw16, **linkopt10)
    net.addLink(sw13, h1, **linkopt100)
    net.addLink(sw14, h2, **linkopt100)
    net.addLink(sw15, sw12, **linkopt15)
    net.addLink(sw16, h3, **linkopt100)

    net.start()
    
    print("Attendere 5 secondi per la scoperta della topologia...")
    time.sleep(5)
    
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel('info')
    run()