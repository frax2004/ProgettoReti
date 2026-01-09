from flask import Flask, jsonify, request
import subprocess
import re

app = Flask(__name__)

# Endpoint per verificare che il server sia attivo
@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({"status": "ready", "node": "H1", "message": "Esperimenti di rete pronti"})

# Endpoint per eseguire un PING verso un altro host
@app.route('/experiment/ping', methods=['POST'])
def run_ping():
    data = request.json
    target_ip = data.get('target')
    count = data.get('count', 4)

    if not target_ip:
        return jsonify({"error": "Target IP mancante"}), 400

    # Esegue il comando ping
    cmd = ["ping", "-c", str(count), target_ip]
    result = subprocess.run(cmd, capture_output=True, text=True)

    return jsonify({
        "target": target_ip,
        "stdout": result.stdout,
        "stderr": result.stderr
    })

# Endpoint per eseguire un test di banda con IPERF
@app.route('/experiment/iperf', methods=['POST'])
def run_iperf():
    data = request.json
    server_ip = data.get('target') # L'host che fa da server iperf

    if not server_ip:
        return jsonify({"error": "Target server IPERF mancante"}), 400

    # Esegue iperf come client verso il target
    # Nota: il target deve avere 'iperf -s' attivo
    cmd = ["iperf", "-c", server_ip, "-t", "5", "-y", "C"] # -y C per output CSV facile da parsare
    result = subprocess.run(cmd, capture_output=True, text=True)

    return jsonify({
        "experiment": "iperf_bandwidth",
        "raw_csv": result.stdout.strip(),
        "error": result.stderr
    })

if __name__ == '__main__':
    # h1 deve ascoltare sul proprio IP o su 0.0.0.0
    app.run(host='0.0.0.0', port=5000)