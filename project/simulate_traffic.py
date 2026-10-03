import sys
import io
import requests
import time
import random

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import json

# SSO web server URL
TARGET_URL = "http://127.0.0.1:5000/login"

def load_user_database():
    if os.path.exists("users.json"):
        with open("users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            student_ids = [u["student_id"] for u in data]
            passwords = {u["student_id"]: u["password"] for u in data}
            return student_ids, passwords
    return ["20260001", "20260002", "20260003"], {"20260001": "Student123!", "20260002": "Password2026", "20260003": "SecurePass#1"}

STUDENT_IDS, VALID_PASSWORDS = load_user_database()

def generate_random_ip():
    """분산 공격용 랜던 IP 생성"""
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def send_login_request(student_id, password, ip_address, user_agent="Mozilla/5.0"):
    """서버에 JSON 요청을 전송하고 ML 모델 및 보안 응답 출력"""
    headers = {
        "X-Forwarded-For": ip_address,
        "User-Agent": user_agent,
        "Content-Type": "application/json"
    }
    payload = {"student_id": student_id, "password": password}

    try:
        res = requests.post(TARGET_URL, json=payload, headers=headers, timeout=5)
        response_data = res.json()
        
        status_code = res.status_code
        risk_score = response_data.get("risk_score", "N/A")
        
        if status_code == 200:
            status_str = response_data.get("status")
            print(f"  [SUCCESS/ALLOWED] ID: {student_id} | Risk: {risk_score} | Msg: {response_data.get('message')}")
        elif status_code == 429:
            print(f"  [🚨 BLOCKED - ML DETECTED] ID: {student_id} | Risk: {risk_score} | Action: {response_data.get('action_taken')}")
        else:
            print(f"  [RESPONSE {status_code}] ID: {student_id} | Risk: {risk_score}")

    except Exception as e:
        print(f"  [!] 요청 전송 실패: {e}")

# 1. 정상 사용자 트래픽
def simulate_legitimate_users(count=5):
    print(f"\n[+] 1. 정상 사용자 트래픽 시뮬레이션 시작 ({count}회 요청)...")
    for i in range(count):
        student_id = random.choice(STUDENT_IDS)
        user_ip = "192.168.1.100"
        
        # 20% 확률로 실수에 의한 비밀번호 입력 오류
        if random.random() < 0.2:
            send_login_request(student_id, "WrongPassword!", user_ip)
            time.sleep(random.uniform(1.0, 2.0))

        send_login_request(student_id, VALID_PASSWORDS[student_id], user_ip)
        time.sleep(random.uniform(1.5, 3.0))

# 2. 고빈도 Account DoS 공격 (Targeted Lockout Attack)
def simulate_account_dos_attack(target_id="20260001", attempts=12):
    print(f"\n[!] 2. Account DoS 공격 시뮬레이션 시작 (타겟 계정: {target_id}, {attempts}회 고속 실패 요청)...")
    attacker_ip = "45.33.32.156"
    
    for i in range(attempts):
        fake_pass = f"AttackPass_{random.randint(1000, 9999)}"
        send_login_request(target_id, fake_pass, attacker_ip, user_agent="Hydra/9.2 (Automated Bot)")
        time.sleep(0.05)  # 빠른 연속 시도

# 3. IP Rotation Password Spraying 공격
def simulate_password_spraying(attempts=10):
    print(f"\n[!] 3. IP Rotation Password Spraying 공격 시뮬레이션 시작 ({attempts}회 요청)...")
    for i in range(attempts):
        target_id = random.choice(STUDENT_IDS)
        bot_ip = generate_random_ip()
        send_login_request(target_id, "Password2026!", bot_ip, user_agent="Python-requests/2.31.0")
        time.sleep(0.1)

if __name__ == "__main__":
    print("=======================================================================")
    print(" ML ANOMALY DETECTOR - INTEGRATED REAL-TIME TRAFFIC SIMULATOR ")
    print("=======================================================================")
    
    # 1단계: 정상 트래픽 (Risk Score 낮음)
    simulate_legitimate_users(count=3)
    
    # 2단계: Account DoS 공격 (Risk Score 50%+ 상승 및 IP 차단)
    simulate_account_dos_attack(target_id="20260001", attempts=10)
    
    # 3단계: 공격 후 정상 로그인 검증
    print("\n[✔] 검증: 공격 후 올바른 IP에서 정상 사용자 접근 가능 여부 테스트...")
    send_login_request("20260001", "Student123!", "192.168.1.100")
    
    # 4단계: Password Spraying 공격
    simulate_password_spraying(attempts=8)
    
    print("\n=======================================================================")
    print("[✔] 트래픽 시뮬레이션이 완료되었습니다!")
    print("=======================================================================")