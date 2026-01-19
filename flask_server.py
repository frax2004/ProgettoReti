from flask import Flask, jsonify, request
import subprocess
import os

app = Flask(__name__)

# Ottieni il percorso assoluto della cartella dove gira il server
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(BASE_DIR, 'data')
os.makedirs(data_dir, exist_ok=True)


@app.route('/start_iperf', methods=['POST'])
def start_iperf():
  data = request.json
  src_ip = data.get('IP_SRC')
  dst_ip = data.get('IP_DEST')
  src_name = data.get('SRC_NAME')
  dst_name = data.get('DST_NAME')
  out_dir = data.get('RUNTIME_OUTPUT_DIR')
  l4_proto = data.get('L4_proto', 'UDP').upper()
  src_rate = data.get('src_rate')

  if l4_proto not in ['TCP', 'UDP']:
    return jsonify({'error': 'Protocollo non valido. Usa TCP o UDP'}), 400

  try:
    if not src_rate: raise ValueError
  except ValueError:
    return jsonify({'error': 'src_rate non valido'}), 400

  os.makedirs('data', exist_ok=True)

  if l4_proto == 'UDP':
    iperf_cmd = f'iperf -c {dst_ip} -u -b {src_rate} -t 10 -i 0.2 -y C'
  else:
    iperf_cmd = f'stdbuf -oL iperf -c {dst_ip} -t 10 -i 0.2 -y C'

  log_path = os.path.join(data_dir, out_dir, f'client_{src_name}_to_{dst_name}.csv')

  ssh_cmd = (
    f"ssh -o StrictHostKeyChecking=no root@{src_ip} "
    f"\"stdbuf -oL {iperf_cmd} >> {log_path} 2>&1 &\""
  )

  try:
    result = subprocess.run(
      ssh_cmd,
      shell=True,
      capture_output=True,
      text=True,
      timeout=5
    )
  
    if result.returncode != 0:
      print(f"[ERROR] SSH command failed: {result.stderr}")
      return jsonify({
        'error': 'Failed to start iperf',
        'details': result.stderr
      }), 500
    
  except subprocess.TimeoutExpired:
    print("[WARNING] SSH command timed out (this might be normal)")
  except Exception as e:
    print(f"[ERROR] Exception: {str(e)}")
    return jsonify({'error': str(e)}), 500

  return jsonify({
    'status': 'Traffic started',
    'source': src_ip,
    'destination': dst_ip,
    'protocol': l4_proto,
    'rate': src_rate,
    'log_file': log_path
  })


@app.route('/stop_iperf', methods=['POST'])
def stop_iperf():
  data = request.json
  src_ip = data.get('IP_SRC')
  
  if not src_ip:
    return jsonify({'error': 'IP_SRC required'}), 400


  ssh_cmd = (
    f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    f"-o LogLevel=ERROR root@{src_ip} "
    f"'pkill -f \"iperf -c\"'"
  )

  try:
    result = subprocess.run(
      ssh_cmd,
      shell=True,
      capture_output=True,
      text=True,
      timeout=5
    )
    
    return jsonify({
      'status': 'Stopped iperf clients',
      'host': src_ip
    })
    
  except Exception as e:
    print(f"[ERROR] Failed to stop iperf: {str(e)}")
    return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=80, debug=True)

