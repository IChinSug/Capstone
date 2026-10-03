import sys
import io
import time
import json
import requests
import sqlite3
import os
import random
import threading

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_base_url():
    url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("BASE_URL") or "http://127.0.0.1:5000"
    if url.endswith("/"):
        url = url[:-1]
    return url

def get_target_url():
    return f"{get_base_url()}/login"

BASE_URL = get_base_url()
TARGET_URL = get_target_url()

ATTACKER_DB_FILE = "attacker_logs.db"

# Global state for continuous traffic loop
is_continuous_running = False
continuous_thread = None
attack_history_logs = []

def init_attacker_db():
    try:
        conn = sqlite3.connect(ATTACKER_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attacker_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                student_id TEXT,
                ip_address TEXT,
                status_code INTEGER,
                risk_score TEXT,
                attack_type TEXT,
                message TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [!] attacker_logs.db init warning: {e}")

init_attacker_db()

def clear_attacker_logs():
    """
    Clears ONLY the Attacker's logs in memory and in attacker_logs.db.
    Protects the main SSO server's auth_logs.db and users.db from being wiped.
    """
    global attack_history_logs
    attack_history_logs.clear()
    try:
        if os.path.exists(ATTACKER_DB_FILE):
            conn = sqlite3.connect(ATTACKER_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attacker_logs")
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"  [!] attacker_logs.db clear error: {e}")
    print("[✔] 공격자 전용 데이터베이스(attacker_logs.db) 및 로그가 초기화되었습니다.")

def reset_db_and_logs():
    clear_attacker_logs()

def fetch_student_accounts():
    """
    Dynamically fetches student accounts from users.db (or users.json),
    returning a list of student_id strings (excluding admin and analyst).
    """
    students = []
    if os.path.exists("users.db"):
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT student_id FROM users WHERE role = 'Student' ORDER BY id ASC")
            rows = cursor.fetchall()
            conn.close()
            students = [r[0] for r in rows if r[0] not in ("admin", "analyst")]
        except Exception as e:
            print(f"  [!] users.db query error: {e}")

    if not students and os.path.exists("users.json"):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                students = [u["student_id"] for u in data if u.get("role") == "Student"]
        except Exception as e:
            print(f"  [!] users.json query error: {e}")

    if not students:
        students = [f"2026{i:04d}" for i in range(1, 201)]

    return students

def get_random_victim(exclude=None):
    """
    Dynamically picks a single random student account ID.
    Optionally excludes specified student IDs.
    """
    students = fetch_student_accounts()
    if exclude:
        if isinstance(exclude, (list, tuple, set)):
            students = [s for s in students if s not in exclude]
        else:
            students = [s for s in students if s != exclude]
    return random.choice(students) if students else "20260001"

def get_random_victims(count=5, exclude=None):
    """
    Dynamically picks 'count' random unique student account IDs.
    Optionally excludes specified student IDs.
    """
    students = fetch_student_accounts()
    if exclude:
        if isinstance(exclude, (list, tuple, set)):
            students = [s for s in students if s not in exclude]
        else:
            students = [s for s in students if s != exclude]
    if not students:
        return [f"2026{i:04d}" for i in range(1, count + 1)]
    return random.sample(students, min(count, len(students)))

def generate_random_ip():
    """랜덤 공격자/사용자 IP 생성"""
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def send_real_request(student_id, password, ip_address, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"):
    headers = {
        "X-Forwarded-For": ip_address,
        "User-Agent": user_agent,
        "Content-Type": "application/json"
    }
    payload = {"student_id": student_id, "password": password}
    
    try:
        res = requests.post(get_target_url(), json=payload, headers=headers, timeout=5)
        data = res.json()
        status_code = res.status_code
        risk_score = data.get("risk_score", "0.0%")
        msg = data.get("message", "")
        att_type = data.get("attack_type", "LEGITIMATE")
        
        log_entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "student_id": student_id,
            "ip_address": ip_address,
            "status_code": status_code,
            "risk_score": risk_score,
            "attack_type": att_type,
            "message": msg
        }
        attack_history_logs.append(log_entry)
        if len(attack_history_logs) > 200:
            attack_history_logs.pop(0)

        # Save to attacker's own database (attacker_logs.db)
        try:
            conn = sqlite3.connect(ATTACKER_DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO attacker_logs (timestamp, student_id, ip_address, status_code, risk_score, attack_type, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (log_entry["timestamp"], student_id, ip_address, status_code, str(risk_score), att_type, msg))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [!] attacker_logs.db insert error: {e}")

        if status_code == 200:
            print(f"  [✅ HTTP 200 SUCCESS] User: {student_id:10s} | IP: {ip_address:15s} | Risk: {risk_score:6s} | {msg}")
        elif status_code == 403:
            print(f"  [⛔ HTTP 403 SUSPENDED] User: {student_id:8s} | IP: {ip_address:15s} | {msg}")
        elif status_code == 429:
            print(f"  [🚨 HTTP 429 BLOCKED ] User: {student_id:8s} | IP: {ip_address:15s} | Risk: {risk_score:6s} | Attack: {att_type}")
        else:
            print(f"  [❌ HTTP {status_code} FAILED  ] User: {student_id:8s} | IP: {ip_address:15s} | Risk: {risk_score:6s} | {msg}")
        return status_code, data
    except Exception as e:
        print(f"  [!] HTTP 요청 전송 실패: {e}")
        return 500, {"error": str(e)}

# =======================================================================
# 4가지 개별 공격 실행 함수 (Modular Attack Functions for Attacker Web Interface)
# =======================================================================

def execute_brute_force(target_id=None, attacker_ip="45.33.32.156", attempts=5):
    """공격 1: Brute Force / Account DoS 공격"""
    if not target_id or str(target_id).strip().upper() in ("", "RANDOM", "NONE"):
        target_id = get_random_victim()
    print(f"\n--- [공격 1] Brute Force / Account DoS 실행 (Target: {target_id}, IP: {attacker_ip}, Attempts: {attempts}) ---")
    results = []
    for i in range(1, attempts + 1):
        code, resp = send_real_request(target_id, f"WrongPass_{i}!", attacker_ip, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        results.append({"step": i, "status": code, "response": resp})
        time.sleep(0.1)
    
    # Check status with correct password
    code, resp = send_real_request(target_id, "Password2026", "192.168.1.200")
    results.append({"step": "check_status", "status": code, "response": resp})
    return results

def execute_password_spraying(attacker_ip="198.51.100.42", common_password="Password123!", num_targets=5, targets=None):
    """공격 2: Single-IP Password Spraying 공격"""
    if not targets:
        targets = get_random_victims(num_targets)
    print(f"\n--- [공격 2] Single-IP Password Spraying 실행 (IP: {attacker_ip}, Common Pass: {common_password}, Targets: {len(targets)}) ---")
    results = []
    for victim in targets:
        code, resp = send_real_request(victim, common_password, attacker_ip, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        results.append({"victim": victim, "status": code, "response": resp})
        time.sleep(0.15)
    return results

def execute_ip_rotation(proxy_ips=None, spray_password="SprayPassword2026!", num_targets=5, targets=None):
    """공격 3: IP Rotation Password Spraying 공격"""
    if not proxy_ips:
        proxy_ips = ["185.220.101.5", "103.253.145.8", "91.240.118.12", "185.220.101.9", "45.154.255.88"]
    if not targets:
        targets = get_random_victims(num_targets)
    print(f"\n--- [공격 3] IP Rotation Spraying 실행 (Proxies: {len(proxy_ips)}, Pass: {spray_password}, Targets: {len(targets)}) ---")
    results = []
    for i, victim in enumerate(targets):
        proxy_ip = proxy_ips[i % len(proxy_ips)]
        code, resp = send_real_request(victim, spray_password, proxy_ip, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        results.append({"victim": victim, "proxy_ip": proxy_ip, "status": code, "response": resp})
        time.sleep(0.15)
    return results

def execute_bot_traffic(bot_agent="Hydra/9.2 (Automated Security Bot Engine)", target_id=None, bot_ips=None):
    """공격 4: Automated Bot Traffic / Multi-IP Anomaly 공격"""
    if not target_id or str(target_id).strip().upper() in ("", "RANDOM", "NONE"):
        target_id = get_random_victim()
    if not bot_ips:
        bot_ips = ["194.26.29.11", "185.156.173.22", "45.146.164.110"]
    print(f"\n--- [공격 4] Automated Bot Traffic 실행 (Target: {target_id}, Bot: {bot_agent}) ---")
    results = []
    for b_ip in bot_ips:
        code, resp = send_real_request(target_id, "BotAttemptPass!", b_ip, user_agent=bot_agent)
        results.append({"bot_ip": b_ip, "status": code, "response": resp})
        time.sleep(0.15)
    
    # Check target account status
    code, resp = send_real_request(target_id, "Password2026", "192.168.1.201")
    results.append({"step": "check_status", "status": code, "response": resp})
    return results

# =======================================================================
# 실시간 무한 트래픽 루프 (Continuous Real-Time Background Traffic Loop)
# =======================================================================

def continuous_traffic_loop():
    """
    Runs an endless real-time background loop generating realistic login requests
    (legitimate logins mixed with attack patterns) until is_continuous_running is False.
    """
    global is_continuous_running
    print("\n[▶] 실시간 무한 트래픽 전송 루프가 시작되었습니다 (Continuous Traffic Loop Started)...")
    students = fetch_student_accounts()
    
    legit_ips = ["192.168.1.100", "192.168.1.101", "192.168.1.105", "10.0.0.15", "10.0.0.42"]
    attack_ips = ["45.33.32.156", "198.51.100.42", "185.220.101.5", "194.26.29.11"]
    
    while is_continuous_running:
        try:
            # 80% probability: Normal/Realistic user login request
            if random.random() < 0.8:
                student_id = random.choice(students) if students else f"2026{random.randint(1, 200):04d}"
                user_ip = random.choice(legit_ips)
                
                # Random chance of typo password vs correct password
                if random.random() < 0.25:
                    send_real_request(student_id, f"PassTypo{random.randint(1,99)}!", user_ip)
                else:
                    send_real_request(student_id, "Password2026", user_ip)
            else:
                # 20% probability: Random attack traffic burst
                attack_choice = random.choice(["brute", "spray", "bot"])
                if attack_choice == "brute":
                    target = random.choice(students) if students else "20260001"
                    send_real_request(target, f"AttackPass_{random.randint(100,999)}", random.choice(attack_ips))
                elif attack_choice == "spray":
                    target = random.choice(students) if students else "20260002"
                    send_real_request(target, "Password123!", "198.51.100.42")
                else:
                    target = random.choice(students) if students else "20260003"
                    send_real_request(target, "BotAttempt!", generate_random_ip(), user_agent="Hydra/9.2")

            time.sleep(random.uniform(0.3, 1.2))
        except Exception as e:
            print(f"[!] Continuous loop error: {e}")
            time.sleep(1.0)
            
    print("[⏹] 실시간 무한 트래픽 전송 루프가 중지되었습니다 (Continuous Traffic Loop Stopped).")

def start_continuous_traffic():
    global is_continuous_running, continuous_thread
    if not is_continuous_running:
        is_continuous_running = True
        continuous_thread = threading.Thread(target=continuous_traffic_loop, daemon=True)
        continuous_thread.start()
        return True
    return False

def stop_continuous_traffic():
    global is_continuous_running
    if is_continuous_running:
        is_continuous_running = False
        return True
    return False

def run_live_attacks():
    """Test sequence if explicitly requested with --test."""
    print("=======================================================================")
    print(" 실제 HTTP 요청 기반 4가지 보안 공격 시뮬레이션 (Live Attack Simulation) ")
    print("=======================================================================")

    reset_db_and_logs()

    students = fetch_student_accounts()
    bf_victim = students[1] if len(students) > 1 else "20260002"
    spray_victims = students[2:7] if len(students) >= 7 else students[:5]
    ip_rot_victims = students[7:12] if len(students) >= 12 else students[:5]
    bot_victim = students[12] if len(students) > 12 else "20260010"

    print("\n--- 시나리오 0: 정상 사용자 로그인 ---")
    send_real_request(students[0] if students else "20260001", "Password2026", "192.168.1.105")
    send_real_request("admin", "admin123", "192.168.1.100")

    execute_brute_force(bf_victim, "45.33.32.156", attempts=5)
    execute_password_spraying("198.51.100.42", "Password123!", num_targets=5)
    execute_ip_rotation(spray_password="SprayPassword2026!", num_targets=5)
    execute_bot_traffic(target_id=bot_victim)

    print("\n--- 시나리오 5: Admin Rescue Mode ---")
    send_real_request("admin", "admin123", "45.33.32.156")

    print("\n=======================================================================")
    print("[✔] 4가지 보안 공격 시뮬레이션 테스트가 완료되었습니다!")
    print("=======================================================================")

if __name__ == "__main__":
    if "--loop" in sys.argv or "--continuous" in sys.argv:
        try:
            start_continuous_traffic()
            print("[💡] Ctrl+C를 누르면 무한 트래픽 전송이 중지됩니다.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_continuous_traffic()
            print("\n[✔] 시뮬레이터가 안전하게 종료되었습니다.")
    elif "--test" in sys.argv:
        run_live_attacks()
    else:
        print("=======================================================================")
        print(" 🚨 LIVE ATTACK SIMULATOR (시뮬레이터 기본 모드: 대기 상태 IDLE) ")
        print("=======================================================================")
        print(" [!] Default Mode: 무한 트래픽 및 자동 공격을 수행하지 않습니다.")
        print("")
        print(" [💡] 웹 공격자 대시보드 실행 (Attacker Control Panel):")
        print("     python Attacker/attacker_app.py")
        print("     -> http://127.0.0.1:5001 에서 4가지 공격을 클릭하여 실행")
        print("")
        print(" [💡] 터미널 옵션:")
        print("     python live_attack_simulator.py --loop    (실시간 무한 트래픽 실행)")
        print("     python live_attack_simulator.py --test    (4가지 공격 테스트 1회 수행)")
        print("=======================================================================")
