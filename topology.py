# ------------------------
# Librerie necessarie
# ------------------------
from mininet.net import Mininet
from mininet.node import RemoteController as ControllerType, OVSSwitch as SwitchType
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
import time
import json
import os

# ------------------------

ALGORITHM = 'astar'

def build_network() -> Mininet:
  net = Mininet(link = TCLink, autoSetMacs = True)

  addresses = [
    '10.0.0.1/24',
    '10.0.0.2/24',
    '11.0.0.1/24',
    '192.168.1.1/24',
    '10.8.1.1/24'
  ]

  controller = ControllerType('c0', ip='127.0.0.1', port=6653)

  net.addController(controller)

  hosts = []
  for i in range(5):
    gateway = addresses[i].split('/')[0].rsplit('.', 1)[0] + '.254'
    host = net.addHost(f'h{i+1}', mac = f'00:00:00:00:00:0{i+1}', ip = addresses[i], defaultRoute = f'via {gateway}')
    hosts.append(host)

  switches = []
  for i in range(1, 10):
    switch = net.addSwitch(f's{i}', cls = SwitchType, protocols = 'OpenFlow13', failmode = 'secure')
    switches.append(switch)

  link_config = {'bw': 1000, 'delay' : '5ms'}

  net.addLink(switches[0], switches[1], **link_config)
  net.addLink(switches[1], switches[2], **link_config)
  net.addLink(switches[3], switches[4], **link_config)
  net.addLink(switches[4], switches[5], **link_config)
  net.addLink(switches[6], switches[7], **link_config)
  net.addLink(switches[7], switches[8], **link_config)

  net.addLink(switches[0], switches[3], **link_config)
  net.addLink(switches[1], switches[4], **link_config)
  net.addLink(switches[2], switches[5], **link_config)
  net.addLink(switches[3], switches[6], **link_config)
  net.addLink(switches[4], switches[7], **link_config)
  net.addLink(switches[5], switches[8], **link_config)

  net.addLink(hosts[0], switches[0], bw = 100, delay = '0.05ms')
  net.addLink(hosts[1], switches[0], bw = 100, delay = '0.05ms')
  net.addLink(hosts[3], switches[2], bw = 100, delay = '1ms')
  net.addLink(hosts[2], switches[6], bw = 5, delay = '0.5ms')
  net.addLink(hosts[4], switches[8], bw = 200, delay = '1ms')

  return net


def setup_ssh(net: Mininet):
  print("\nConfigurazione SSH")
  h1 = net.get('h1')

  h1.cmd('rm -rf /root/.ssh')
  h1.cmd('mkdir -p /root/.ssh && chmod 700 /root/.ssh')
  h1.cmd('ssh-keygen -t rsa -f /root/.ssh/id_rsa -N "" -q')
  h1.cmd('cat /root/.ssh/id_rsa.pub > /root/.ssh/authorized_keys')
  h1.cmd('chmod 600 /root/.ssh/authorized_keys')

  client_conf = "Host *\n  StrictHostKeyChecking no\n  UserKnownHostsFile=/dev/null\n  BatchMode yes\n"
  h1.cmd(f'echo "{client_conf}" > /root/.ssh/config')

  sshd_conf = """
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
PermitRootLogin yes
PubkeyAuthentication yes
AuthorizedKeysFile /root/.ssh/authorized_keys
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
StrictModes no
PrintMotd no
Subsystem sftp /usr/lib/openssh/sftp-server
"""
  with open("/tmp/sshd_config_mininet", "w") as f:
    f.write(sshd_conf)

  print('3')

  for host in net.hosts:
    print(f'{host.name}')
    host.cmd('mkdir -p /var/run/sshd')
    host.cmd('ssh-keygen -A')
    host.cmd('/usr/sbin/sshd -f /tmp/sshd_config_mininet -D &')
    print(f"  SSH pronto su {host.name}")

  time.sleep(3)


def setup_iperf(net: Mininet):
  def start_iperf_daemon(host):
    log_path = f'data/{host.name}_server_output.csv'
    host.cmd(f'iperf -s -u -i 0.2 -y C > {log_path} &')
    time.sleep(0.5)

  def assert_iperf_started(host):
    processes = host.cmd('pgrep -a iperf')
    res = processes.strip() if processes.strip() else 'NESSUN PROCESSO!'
    print(f"{host.name}: {res}")

  h1 = net.get('h1')
  h2 = net.get('h2')
  h3 = net.get('h3')
  h4 = net.get('h4')
  h5 = net.get('h5')
  hosts = [h1, h2, h3, h4, h5]

  for host in hosts:
    host.cmd(f'mkdir -p data/')

  for host in hosts:
    print(f"Avvio iperf server su {host.name}...")
    start_iperf_daemon(host)

  for host in hosts:
    print(f'Verifica server iperf su {host.name}')
    assert_iperf_started(host)

  print('\nServer iperf avviati. Attesa 3 secondi...')
  time.sleep(3)

def run_experiment(experiment, end_point_server, exp_index: int):
  senders, receiver = experiment
  
  def get_start_iperf_curl(sender, rate, receiver):
    payload = json.dumps({
      'IP_SRC': sender.IP(),
      'IP_DEST': receiver.IP(),
      'SRC_NAME': sender.name,
      'DST_NAME': receiver.name,
      'RUNTIME_OUTPUT_DIR': f'case_#{exp_index}',
      'L4_proto': 'UDP',
      'src_rate': rate
    })

    return (
      f"curl -s -X POST -H 'Content-Type: application/json' "
      f"-d '{payload}' http://{end_point_server.IP()}/start_iperf"
    )

  def get_stop_iperf_curl(sender):
    payload = json.dumps({'IP_SRC': sender.IP()})
    return (
      f"curl -s -X POST -H 'Content-Type: application/json' "
      f"-d '{payload}' http://{end_point_server.IP()}/stop_iperf"
    )

  for sender, rate in senders.items():
    print(f"Experimenting {sender.name} -> {receiver.name} on {end_point_server.name} at rate {rate}")
    request = get_start_iperf_curl(sender, rate, receiver)
    sender.cmd(request)
    time.sleep(0.5)

  # Tempo per eseguire gli esperimenti (abbondante: basterebbe 10 secondi, ma non si sa mai qualche ritardo)
  time.sleep(15)

  for sender in senders.keys():
    request = get_stop_iperf_curl(sender)
    stop_response = sender.cmd(request)
    print(stop_response)
  return

setLogLevel('info')

def run_topology(net: Mininet):
  print('Start networking\n')
  net.start()
  time.sleep(5)

  CLI(net)

  # Inizializzazione ssh
  setup_ssh(net)

  # Inizializzazione flask
  print('Avvio API Flask su h1 (IP: 10.0.0.1)')
  h1 = net.get('h1')
  h1.cmd("nohup python3 flask_server.py > log_flask.txt 2>&1 &")
  print('API Flask avviata su h1 (IP: 10.0.0.1)')
  time.sleep(2)

  # Avvio dei demoni iperf sugli host
  setup_iperf(net)

  h1 = net.get('h1')
  h2 = net.get('h2')
  h3 = net.get('h3')
  h4 = net.get('h4')
  h5 = net.get('h5')

  experiments = [
    ({h2: '100M'}, h1),
    ({h2: '100M', h3: '100M'}, h1),
    ({h2: '100M', h3: '100M', h4: '5M'}, h1),
    ({h2: '100M', h3: '100M', h4: '5M', h5: '200M'}, h1),
  ] # in pseudo codice, ogni esperimento sarebbe "host.send_traffic_to(h1, rate) for (host, rate) in hosts.items()"

  # Avvio degli esperimenti
  for i, experiment in enumerate(experiments):
    print(f"Avvio dell'esperimento #{i+1}")
    os.makedirs(f'data/case_#{i+1}', exist_ok = True)

    # h1 è il server flask (api rest) con gli end points start_iperf e stop_iperf
    # (l'abbiamo pensato nella maniera più generica possibile) 
    # i+1 serve a comunicare al server flask che questo è l'esperimento #i 
    # e quindi dovrà ridirezionare gli output nella cartella appropriata
    run_experiment(experiment, h1, i+1)
    
    print(f"Esperimento #{i+1} completato")

  CLI(net)

  print('Stopping network\n')
  net.stop()

def run_test():
  net = build_network()
  run_topology(net)

if __name__ == '__main__':
  run_test()