import csv
import matplotlib.pyplot as plt
from datetime import datetime

def print_throughput(algo):
  with open(f'data/{algo}/h1_server_output.csv', 'r') as file:
    reader = csv.reader(file)

    lines = [line for line in reader]

  stats = {
    "Timestamp": tuple(datetime.strptime(line[0], "%Y%m%d%H%M%S") for line in lines),
    "SourceIP": tuple(line[1] for line in lines),
    "SourcePort": tuple(line[2] for line in lines),
    "DestIP": tuple(line[3] for line in lines),
    "DestPort": tuple(line[4] for line in lines),
    "ID": tuple(line[5] for line in lines),
    "Interval": tuple(line[6] for line in lines),
    "TransferredBytes": tuple(line[7] for line in lines),
    "Throughput": tuple(float(line[8]) / 1e6 for line in lines),
    "Jitter": tuple(line[9] for line in lines),
    "LostPackets": tuple(line[10] for line in lines),
    "TotalPackets": tuple(line[11] for line in lines),
    "PacketLoss": tuple(line[12] for line in lines),
    "OutOfOrder": tuple(line[13] for line in lines),
  }

  timestamp = stats['Timestamp']
  timestamp = [(seconds - timestamp[0]).total_seconds() for seconds in timestamp]
  throughput = stats['Throughput']

  plt.figure()
  plt.title(f'{algo} throughput over time')
  plt.xlabel('time')
  plt.ylabel('throughput')
  plt.scatter(timestamp, throughput)
  plt.savefig(f'{algo}_throughput.png')

print_throughput('dijkstra')
print_throughput('astar')