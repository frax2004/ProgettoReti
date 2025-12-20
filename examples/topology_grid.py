"""      
      [h1] [h2]                                     [h3] [h4]
         \  /                                         \  /
          \/                                           \/
         (s1)-----------(s2)-----------(s3)-----------(s4)
          |              |              |              |
          |              |              |              |
         (s5)-----------(s6)-----------(s7)-----------(s8)
          |              |              |              |
          |              |              |              |
         (s9)-----------(s10)----------(s11)----------(s12)
          |              |              |              |
          |              |              |              |
         (s13)----------(s14)----------(s15)----------(s16)
          /\                                            /\
         /  \                                          /  \
      [h5] [h6]                                      [h7] [h8]
"""      


#!/usr/bin/env python
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel

class CornerGridTopo(Topo):
    def build(self, rows=4, cols=4):
        """
        Crea una griglia rows x cols.
        Attacca 2 host per ogni switch d'angolo.
        """
        if rows < 2 or cols < 2:
            raise Exception("Per una griglia servono almeno 2 righe e 2 colonne")

        # Matrice per memorizzare gli oggetti switch
        sw_matrix = [[None for c in range(cols)] for r in range(rows)]
        
        print(f"--- 1. Creazione Griglia di Switch ({rows}x{cols}) ---")
        
        # Creazione Switch
        sw_count = 1
        for r in range(rows):
            for c in range(cols):
                sw_name = f's{sw_count}'
                # Creiamo lo switch e lo salviamo nella matrice
                sw_matrix[r][c] = self.addSwitch(sw_name)
                sw_count += 1

        # Creazione Link Orizzontali
        for r in range(rows):
            for c in range(cols - 1):
                self.addLink(sw_matrix[r][c], sw_matrix[r][c+1], 
                             bw=100, delay='1ms') # Link veloci tra switch

        # Creazione Link Verticali
        for r in range(rows - 1):
            for c in range(cols):
                self.addLink(sw_matrix[r][c], sw_matrix[r+1][c], 
                             bw=100, delay='1ms')

        print("--- 2. Aggiunta Host agli Angoli (2 per angolo) ---")
        
        # Definiamo le coordinate degli angoli [(riga, colonna)]
        corners = [
            (0, 0),               # Top-Left (Nord-Ovest)
            (0, cols - 1),        # Top-Right (Nord-Est)
            (rows - 1, 0),        # Bottom-Left (Sud-Ovest)
            (rows - 1, cols - 1)  # Bottom-Right (Sud-Est)
        ]
        
        corner_names = ["Nord-Ovest", "Nord-Est", "Sud-Ovest", "Sud-Est"]
        host_global_counter = 1

        for i, (r, c) in enumerate(corners):
            target_switch = sw_matrix[r][c]
            print(f" -> Configurando angolo {corner_names[i]} su switch {target_switch}")
            
            # Aggiungiamo 2 host per questo angolo
            for _ in range(2):
                h_name = f'h{host_global_counter}'
                # Creiamo l'host
                host = self.addHost(h_name)
                # Colleghiamo allo switch d'angolo
                self.addLink(host, target_switch, bw=10, delay='1ms')
                host_global_counter += 1
                
        

def run():
    # Puoi cambiare le dimensioni qui
    ROWS = 6
    COLS = 6
    
    topo = CornerGridTopo(rows=ROWS, cols=COLS)
    
    # Usa RemoteController se hai Ryu che gira, altrimenti OVSController
    net = Mininet(topo=topo, 
                  switch=OVSKernelSwitch, 
                  link=TCLink,
                  controller=RemoteController)

    
    for node in net.values():
        for intf in node.intfList():
            if intf.name == 'lo': continue # skip loopback            
            node.cmd(f"tc qdisc change dev {intf.name} root handle 5: htb default 1 r2q 1000")
    
    net.start()
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()