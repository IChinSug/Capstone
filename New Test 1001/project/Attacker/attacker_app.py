import os
import sys
import io
import time
from flask import Flask, render_template, request, jsonify

# Ensure parent directory is in path to import live_attack_simulator
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import live_attack_simulator

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__, template_folder='templates', static_folder='../static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route("/", methods=["GET"])
def attacker_dashboard():
    return render_template("index.html")

@app.route("/api/students", methods=["GET"])
def get_students():
    students = live_attack_simulator.fetch_student_accounts()
    return jsonify({"status": "SUCCESS", "students": students})

@app.route("/api/attack/brute_force", methods=["POST"])
def launch_brute_force():
    data = request.get_json() or {}
    target_id = data.get("target_id", "").strip()
    attacker_ip = data.get("attacker_ip", "45.33.32.156").strip()
    attempts = int(data.get("attempts", 5))

    if not target_id:
        target_id = live_attack_simulator.get_random_victim()

    results = live_attack_simulator.execute_brute_force(target_id, attacker_ip, attempts)
    return jsonify({
        "status": "SUCCESS",
        "attack_name": "Brute Force / Account DoS",
        "target_id": target_id,
        "attacker_ip": attacker_ip,
        "attempts": attempts,
        "results": results
    })

@app.route("/api/attack/password_spraying", methods=["POST"])
def launch_password_spraying():
    data = request.get_json() or {}
    attacker_ip = data.get("attacker_ip", "198.51.100.42").strip()
    common_password = data.get("common_password", "Password123!").strip()
    num_targets = int(data.get("num_targets", 5))

    results = live_attack_simulator.execute_password_spraying(attacker_ip, common_password, num_targets)
    return jsonify({
        "status": "SUCCESS",
        "attack_name": "Single-IP Password Spraying",
        "attacker_ip": attacker_ip,
        "common_password": common_password,
        "num_targets": num_targets,
        "results": results
    })

@app.route("/api/attack/ip_rotation", methods=["POST"])
def launch_ip_rotation():
    data = request.get_json() or {}
    proxy_ips_str = data.get("proxy_ips", "").strip()
    spray_password = data.get("spray_password", "SprayPassword2026!").strip()
    num_targets = int(data.get("num_targets", 5))

    if proxy_ips_str:
        proxy_ips = [ip.strip() for ip in proxy_ips_str.split(",") if ip.strip()]
    else:
        proxy_ips = ["185.220.101.5", "103.253.145.8", "91.240.118.12", "185.220.101.9", "45.154.255.88"]

    results = live_attack_simulator.execute_ip_rotation(proxy_ips, spray_password, num_targets)
    return jsonify({
        "status": "SUCCESS",
        "attack_name": "IP Rotation Password Spraying",
        "proxy_ips": proxy_ips,
        "spray_password": spray_password,
        "num_targets": num_targets,
        "results": results
    })

@app.route("/api/attack/bot_traffic", methods=["POST"])
def launch_bot_traffic():
    data = request.get_json() or {}
    bot_agent = data.get("bot_agent", "Hydra/9.2 (Automated Security Bot Engine)").strip()
    target_id = data.get("target_id", "").strip()
    bot_ips_str = data.get("bot_ips", "").strip()

    if not target_id:
        target_id = live_attack_simulator.get_random_victim()

    if bot_ips_str:
        bot_ips = [ip.strip() for ip in bot_ips_str.split(",") if ip.strip()]
    else:
        bot_ips = ["194.26.29.11", "185.156.173.22", "45.146.164.110"]

    results = live_attack_simulator.execute_bot_traffic(bot_agent, target_id, bot_ips)
    return jsonify({
        "status": "SUCCESS",
        "attack_name": "Automated Bot Traffic",
        "bot_agent": bot_agent,
        "target_id": target_id,
        "bot_ips": bot_ips,
        "results": results
    })

@app.route("/api/attack/continuous/start", methods=["POST"])
def start_continuous():
    started = live_attack_simulator.start_continuous_traffic()
    return jsonify({
        "status": "SUCCESS",
        "is_running": live_attack_simulator.is_continuous_running,
        "message": "실시간 무한 트래픽 전송이 시작되었습니다." if started else "이미 실행 중입니다."
    })

@app.route("/api/attack/continuous/stop", methods=["POST"])
def stop_continuous():
    stopped = live_attack_simulator.stop_continuous_traffic()
    return jsonify({
        "status": "SUCCESS",
        "is_running": live_attack_simulator.is_continuous_running,
        "message": "실시간 무한 트래픽 전송이 중지되었습니다." if stopped else "실행 중이 아닙니다."
    })

@app.route("/api/attack/continuous/status", methods=["GET"])
def get_continuous_status():
    return jsonify({
        "status": "SUCCESS",
        "is_running": live_attack_simulator.is_continuous_running
    })

@app.route("/api/attack/logs", methods=["GET"])
def get_attack_logs():
    return jsonify({
        "status": "SUCCESS",
        "logs": live_attack_simulator.attack_history_logs[-50:],
        "is_running": live_attack_simulator.is_continuous_running
    })

@app.route("/api/attack/logs/clear", methods=["POST"])
def clear_attack_logs():
    live_attack_simulator.clear_attacker_logs()
    return jsonify({
        "status": "SUCCESS",
        "message": "공격자 콘솔 로그가 성공적으로 지워졌습니다."
    })

@app.route("/api/reset", methods=["POST"])
def reset_system():
    live_attack_simulator.clear_attacker_logs()
    return jsonify({"status": "SUCCESS", "message": "공격자 전용 DB(attacker_logs.db) 및 로그가 초기화되었습니다."})

if __name__ == "__main__":
    print("=======================================================================")
    print(" 🚨 SECUREAUTH ATTACKER CONTROL PANEL SERVER RUNNING ")
    print(" Attacker Console URL: http://127.0.0.1:5001")
    print(" Target SSO Server:    http://127.0.0.1:5000/login")
    print("=======================================================================")
    app.run(host="0.0.0.0", port=5001, debug=False)
