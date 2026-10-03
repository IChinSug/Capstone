import sys
import io
import os
import time
import json
import sqlite3
import datetime
import csv
import math
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash

def check_user_password(stored_password, input_password):
    """
    Verifies input password against stored salted hash or plaintext password.
    Supports PBKDF2/scrypt/bcrypt hashes with fallback to plaintext.
    """
    if not stored_password or not input_password:
        return False
    try:
        if str(stored_password).startswith(("pbkdf2:", "scrypt:", "bcrypt:", "argon2:")):
            return check_password_hash(stored_password, input_password)
    except Exception as e:
        print(f"[!] Password hash check error: {e}")
    return stored_password == input_password

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import collections
import smtplib
from email.mime.text import MIMEText
from email.header import Header

class RateLimiter:
    """
    Sliding Window Rate Limiter for endpoint brute-force protection.
    Tracks request timestamps per (key, endpoint) pair.
    """
    def __init__(self):
        self.requests = collections.defaultdict(list)

    def is_rate_limited(self, key, limit_count=15, window_seconds=60):
        now = time.time()
        timestamps = self.requests[key]
        while timestamps and timestamps[0] < now - window_seconds:
            timestamps.pop(0)
        if len(timestamps) >= limit_count:
            return True
        timestamps.append(now)
        return False

rate_limiter = RateLimiter()

def send_real_email_otp(to_email, otp_code, student_id):
    """
    Sends 2FA OTP verification email using SMTP if configured in environment variables.
    Falls back to console/mock log if SMTP credentials are not set.
    """
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    sender_email = os.environ.get("SMTP_SENDER_EMAIL") or smtp_user or "no-reply@secureauth.com"
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    if smtp_server and smtp_user and smtp_password:
        try:
            msg = MIMEText(
                f"안녕하세요,\n\nSecureAuth 인증 시스템 2FA 복구 코드입니다.\n\n"
                f"학번/아이디: {student_id}\n"
                f"2FA OTP 인증 코드: [{otp_code}]\n\n"
                f"이 코드는 5분간 유효합니다. 본인이 요청하지 않은 경우 즉시 관리자에게 문의하세요.",
                'plain', 'utf-8'
            )
            msg['Subject'] = Header(f"[SecureAuth] 2FA 인증 코드: {otp_code}", 'utf-8')
            msg['From'] = sender_email
            msg['To'] = to_email

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                if use_tls:
                    server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()
            print(f"[✔] Real SMTP Email sent successfully to {to_email} (OTP: {otp_code})")
            return True, "이메일 전송 성공"
        except Exception as e:
            print(f"[!] Real SMTP Email sending failed: {e}")
            return False, str(e)
    else:
        print(f"[ℹ] SMTP credentials not set in environment. Falling back to Console OTP log.")
        return True, "Console fallback mode"

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Production Security & Session Cookie Configurations
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24).hex()
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# =========================================================
# 1. 200명 사용자 DB 및 설정 (users.db & users.json)
# =========================================================
USERS_DB_FILE = "users.db"
USERS_JSON_FILE = "users.json"
USERS_CSV_FILE = "users.csv"

def get_user_from_db(student_id):
    """
    Connects to users.db (or users.json) to retrieve dynamic user record for authentication.
    """
    if not os.path.exists(USERS_DB_FILE) or not os.path.exists(USERS_JSON_FILE):
        try:
            import generate_users
            generate_users.main()
        except Exception as e:
            print(f"[!] Could not generate users db: {e}")

    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, password, full_name, email, role, status FROM users WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"student_id": row[0], "password": row[1], "full_name": row[2], "email": row[3], "role": row[4], "status": row[5]}
    except Exception as e:
        print(f"[!] SQLite query failed, falling back to JSON: {e}")

    # Fallback to JSON readable file
    if os.path.exists(USERS_JSON_FILE):
        try:
            with open(USERS_JSON_FILE, "r", encoding="utf-8") as f:
                users_list = json.load(f)
                for u in users_list:
                    if u.get("student_id") == student_id:
                        return u
        except Exception as e:
            print(f"[!] JSON read error: {e}")
            
    return None

def get_user_by_email_from_db(email):
    """
    Retrieves user record by registered email address from users.db or users.json.
    """
    if not email:
        return None
    email_clean = email.strip().lower()
    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, password, full_name, email, role, status FROM users WHERE LOWER(email) = ?", (email_clean,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"student_id": row[0], "password": row[1], "full_name": row[2], "email": row[3], "role": row[4], "status": row[5]}
    except Exception as e:
        print(f"[!] get_user_by_email_from_db SQLite query failed: {e}")

    if os.path.exists(USERS_JSON_FILE):
        try:
            with open(USERS_JSON_FILE, "r", encoding="utf-8") as f:
                users_list = json.load(f)
                for u in users_list:
                    if u.get("email", "").strip().lower() == email_clean:
                        return u
        except Exception as e:
            print(f"[!] JSON email read error: {e}")
            
    return None

def update_user_status_in_db(student_id, new_status):
    """
    Updates a user's status (e.g. SUSPENDED) in users.db and syncs to files.
    Primary 'admin' account status is protected and cannot be changed.
    """
    if student_id == "admin":
        return
    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE student_id = ?", (new_status, student_id))
        conn.commit()
        conn.close()
        sync_users_to_json_csv()
    except Exception as e:
        print(f"[!] Could not update user status: {e}")

def update_user_password_and_status_in_db(student_id, new_password, new_status="ACTIVE"):
    """
    Updates a user's password (salted hash format) and status in users.db and syncs to users.json and users.csv.
    """
    try:
        hashed_pwd = generate_password_hash(new_password)
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ?, status = ? WHERE student_id = ?", (hashed_pwd, new_status, student_id))
        conn.commit()
        conn.close()
        sync_users_to_json_csv()
        print(f"[✔] User '{student_id}' password updated to salted hash and status set to '{new_status}'. Synced to DB, JSON, CSV.")
    except Exception as e:
        print(f"[!] Could not update user password/status: {e}")

def sync_users_to_json_csv():
    """
    Synchronizes SQLite users.db data to users.json and users.csv files for readability.
    """
    try:
        if not os.path.exists(USERS_DB_FILE):
            return
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, password, full_name, email, role, status, created_at FROM users ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        users_list = []
        for r in rows:
            users_list.append({
                "student_id": r[0],
                "password": r[1],
                "full_name": r[2],
                "email": r[3],
                "role": r[4],
                "status": r[5],
                "created_at": r[6] if len(r) > 6 and r[6] else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            
        with open(USERS_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(users_list, f, ensure_ascii=False, indent=2)
            
        fieldnames = ["student_id", "password", "full_name", "email", "role", "status", "created_at"]
        with open(USERS_CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(users_list)
    except Exception as e:
        print(f"[!] User sync error: {e}")

LOG_FILE = "auth.log"
DB_FILE = "auth_logs.db"

# 실시간 6차원 특징 벡터 계산용 메모리 Sliding Window 버퍼
recent_attempts = []
BLOCKED_ENTITIES = set()  # 활성 차단 IP 주소 목록

# =========================================================
# 2. SQLITE 데이터베이스 초기화
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            student_id TEXT,
            ip_address TEXT,
            status TEXT,
            user_agent TEXT,
            risk_score REAL,
            is_attack INTEGER,
            attack_type TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(auth_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    if "attack_type" not in columns:
        cursor.execute("ALTER TABLE auth_logs ADD COLUMN attack_type TEXT")
    conn.commit()
    conn.close()

init_db()  # 서버 구동 시 DB 초기화

# =========================================================
# 3. 모든 인증 요청을 LOG FILE 및 DB에 실시간 저장
# =========================================================
def save_log_entry(student_id, ip_address, status, user_agent, risk_score, is_attack, attack_type="LEGITIMATE"):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # A. auth.log (JSON Lines 형식 기록)
    log_data = {
        "timestamp": now_iso,
        "student_id": student_id,
        "ip_address": ip_address,
        "status": status,
        "user_agent": user_agent,
        "risk_score": risk_score,
        "is_attack": is_attack,
        "attack_type": attack_type
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_data) + "\n")

    # B. auth_logs.db (SQLite DB 저장)
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO auth_logs (timestamp, student_id, ip_address, status, user_agent, risk_score, is_attack, attack_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (now_iso, student_id, ip_address, status, user_agent, risk_score, is_attack, attack_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] DB 기록 오류: {e}")

BOT_USER_AGENTS = ["python", "hydra", "curl", "nmap", "go-http", "requests", "bot", "script"]

def is_bot_user_agent(ua_str):
    if not ua_str:
        return 0
    ua_lower = str(ua_str).lower()
    return 1 if any(b in ua_lower for b in BOT_USER_AGENTS) else 0

FEATURE_COLS = [
    "failed_attempts_5m", "time_interval_sec", 
    "ip_changes_5m", "global_failed_5m", "global_unique_ips_5m", "ua_bot_flag"
]

def classify_attack_type(features):
    """
    Classifies attack type based on feature vector indicators:
    [ip_failed_attempts_5m, time_interval_sec, ip_changes_5m, global_failed_5m, global_unique_ips_5m, ua_bot_flag]
    """
    ip_failed, time_int, ip_changes, glob_failed, glob_ips, is_bot = features
    
    # 1. Automated Bot Traffic (Highest priority if User-Agent is bot/script)
    if is_bot == 1:
        return "Automated Bot Traffic"
        
    # 2. Brute Force / DoS (Single IP high failure rate on target account)
    if ip_failed >= 3 or (ip_failed >= 2 and time_int < 1.5):
        return "Brute Force / DoS"

    # 3. IP Rotation Spraying (Multiple unique IPs attacking multiple accounts)
    if glob_ips >= 3 and glob_failed >= 3 and ip_failed < 3:
        return "IP Rotation Spraying"
        
    # 4. Single-IP Password Spraying (Single IP attacking multiple accounts)
    if glob_failed >= 3 or ip_changes >= 3:
        return "Password Spraying"
        
    return "Anomaly Threshold Exceeded"

# =========================================================
# 4. 머신러닝 모델 (Random Forest) 로드
# =========================================================
def train_and_load_anomaly_detector():
    from sklearn.ensemble import RandomForestClassifier
    print("[+] ML Anomaly Detection Engine을 준비하는 중입니다...")
    
    if os.path.exists("extracted_features.csv"):
        df = pd.read_csv("extracted_features.csv")
        X = df[FEATURE_COLS]
        y = df["label"]
    else:
        X = pd.DataFrame([
            [0, 15.0, 1, 0, 0, 0],  # 정상
            [1, 8.0,  1, 1, 1, 0],  # 정상
            [12, 0.08, 1, 12, 1, 1], # Account DoS
            [0, 0.2, 5, 20, 15, 1],  # Password Spraying
        ], columns=FEATURE_COLS)
        y = np.array([0, 0, 1, 1])

    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X, y)
    print("[✔] Random Forest ML 모델 학습 완료 및 웹 서버 연결 성공!")
    return rf_model

ml_detector = train_and_load_anomaly_detector()

# =========================================================
# 5. REAL-TIME FEATURE EXTRACTION (6차원 특징 벡터 계산)
# =========================================================
def extract_incoming_features(student_id, current_ip, user_agent, now_ts):
    five_min_ago = now_ts - 300  # 최근 5분 (300초)

    # Prune buffer in-place to prevent memory leaks
    recent_attempts[:] = [l for l in recent_attempts if l["time"] >= five_min_ago]
    window_logs = list(recent_attempts)

    # Feature 1: IP 기반 최근 5분 실패 횟수
    ip_failed_attempts_5m = sum(
        1 for l in window_logs 
        if l["ip_address"] == current_ip and l["status"] in ("FAILED", "BLOCKED")
    )

    # Feature 2: 해당 IP의 직전 요청 간 시간 간격 (초)
    ip_logs = [l for l in window_logs if l["ip_address"] == current_ip]
    if ip_logs:
        time_interval_sec = round(now_ts - ip_logs[-1]["time"], 2)
    else:
        time_interval_sec = 15.0

    # Feature 3: 동일 계정이 최근 5분간 접촉한 고유 IP 주소 수
    user_ips = set(l["ip_address"] for l in window_logs if l["student_id"] == student_id)
    user_ips.add(current_ip)
    ip_changes_5m = len(user_ips)

    # Feature 4: 전체 시스템 기준 최근 5분 총 실패 횟수 (Password Spraying 지표)
    global_failed_5m = sum(1 for l in window_logs if l["status"] in ("FAILED", "BLOCKED"))

    # Feature 5: 전체 시스템 기준 실패를 유발한 고유 IP 수 (IP Rotation 지표)
    global_unique_ips_5m = len(set(
        l["ip_address"] for l in window_logs if l["status"] in ("FAILED", "BLOCKED")
    ))

    # Feature 6: 자동화 봇 / 스크립트 User-Agent 지표
    ua_bot_flag = is_bot_user_agent(user_agent)

    return [ip_failed_attempts_5m, time_interval_sec, ip_changes_5m, global_failed_5m, global_unique_ips_5m, ua_bot_flag]

# =========================================================
# 6. 라우트 및 인라인 이상 차단 제어 (/login)
# =========================================================
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return "", 204

def is_known_user_ip(student_id, ip_address):
    """
    Checks if student_id has previously logged in successfully from ip_address
    OR if current IP is local/legitimate network.
    """
    if not student_id:
        return False
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM auth_logs 
            WHERE student_id = ? AND ip_address = ? AND status = 'SUCCESS'
        ''', (student_id, ip_address))
        count = cursor.fetchone()[0]
        conn.close()
        if count > 0:
            return True
    except Exception as e:
        print(f"[!] is_known_user_ip query error: {e}")

    if ip_address in ("127.0.0.1", "::1", "localhost") or ip_address.startswith("192.168.") or ip_address.startswith("10.0."):
        return True

    return False

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("index.html")

    now_ts = time.time()
    
    if request.is_json:
        data = request.get_json()
        student_id = data.get("student_id", "").strip()
        password = data.get("password", "")
    else:
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
        
    user_agent = request.headers.get("User-Agent", "Unknown")

    # Rate Limiting Check (Production Protection against HTTP flooding)
    limit_login_rpm = int(os.environ.get("RATE_LIMIT_LOGIN_PER_MINUTE", 15))
    if rate_limiter.is_rate_limited(f"login_{ip_address}", limit_count=limit_login_rpm, window_seconds=60):
        return jsonify({
            "status": "RATE_LIMIT_EXCEEDED",
            "message": "⚠️ [보안 제한] 짧은 시간에 너무 많은 로그인 요청이 발생했습니다. 1분 후 다시 시도해 주세요."
        }), 429

    # 0. A. 사용자 계정 정지 (SUSPENDED / INACTIVE / DISABLED) 검증
    user_rec = get_user_from_db(student_id)
    if user_rec and user_rec.get("status") in ("SUSPENDED", "INACTIVE", "DISABLED", "LOCKED"):
        features = extract_incoming_features(student_id, ip_address, user_agent, now_ts)
        features_df = pd.DataFrame([features], columns=FEATURE_COLS)
        computed_risk = round(ml_detector.predict_proba(features_df)[0][1] * 100, 1)
        risk_score_val = max(computed_risk, 85.0)
        att_type = classify_attack_type(features)
        save_log_entry(student_id, ip_address, "ACCOUNT_SUSPENDED", user_agent, risk_score_val, 1, attack_type=att_type)

        user_email = user_rec.get("email", "").strip()
        has_registered_email = bool(user_email and "@" in user_email)

        if has_registered_email:
            return jsonify({
                "status": "ACCOUNT_SUSPENDED",
                "can_2fa_recover": True,
                "student_id": student_id,
                "email": user_email,
                "risk_score": f"{risk_score_val}%",
                "attack_type": att_type,
                "message": f"⚠️ [보안 제한] '{student_id}' 계정은 정지/비활성화(SUSPENDED) 상태입니다. 이메일 2FA 인증으로 계정을 복구하고 비밀번호를 변경하세요."
            }), 403
        else:
            return jsonify({
                "status": "ACCOUNT_SUSPENDED",
                "can_2fa_recover": False,
                "student_id": student_id,
                "risk_score": f"{risk_score_val}%",
                "attack_type": att_type,
                "message": f"⚠️ [보안 제한] '{student_id}' 계정은 정지/비활성화 상태입니다. (등록된 이메일 주소가 없습니다.)"
            }), 403

    # 0. B. 활성 차단 IP (BLOCKED_ENTITIES) 검증
    if ip_address in BLOCKED_ENTITIES:
        is_2fa_rescued = (student_id in VERIFIED_2FA_RESCUED_ACCOUNTS and now_ts < VERIFIED_2FA_RESCUED_ACCOUNTS[student_id])

        # Admin Rescue Check: 올바른 Admin 계정 정보로 로그인 시 차단된 IP 자동 해제
        if user_rec and user_rec.get("role") == "Admin" and check_user_password(user_rec.get("password"), password):
            BLOCKED_ENTITIES.discard(ip_address)
            recent_attempts[:] = [l for l in recent_attempts if l.get("ip_address") != ip_address]
            save_log_entry(student_id, ip_address, "ADMIN_RESCUE_UNBLOCK", user_agent, 0.0, 0, attack_type="LEGITIMATE")
            full_name = user_rec.get("full_name", student_id)
            save_log_entry(student_id, ip_address, "SUCCESS", user_agent, 0.0, 0, attack_type="LEGITIMATE")
            return jsonify({
                "status": "SUCCESS",
                "message": f"🔑 [Admin Rescue Mode] IP 차단이 자동 해제되어 정상 로그인되었습니다! 환영합니다 {full_name}님.",
                "risk_score": "0.0%",
                "model_flag": "LEGITIMATE",
                "user": {
                    "student_id": user_rec["student_id"],
                    "full_name": full_name,
                    "email": user_rec.get("email", ""),
                    "role": user_rec.get("role", "Admin"),
                    "status": user_rec.get("status", "ACTIVE")
                }
            }), 200

        # PER-ACCOUNT EXEMPTION RULE:
        # If account status is ACTIVE AND correct password for THIS specific account is entered AND (IP is known OR user verified 2FA):
        elif user_rec and user_rec.get("status") == "ACTIVE" and check_user_password(user_rec.get("password"), password) and (is_known_user_ip(student_id, ip_address) or is_2fa_rescued):
            BLOCKED_ENTITIES.discard(ip_address)
            recent_attempts[:] = [l for l in recent_attempts if l.get("student_id") != student_id]
            status = "SUCCESS"
            full_name = user_rec.get("full_name", student_id)
            message = f"🔑 [계정 복구 로그인 성공] '{student_id}' 계정으로 새로운 비밀번호로 성공적으로 로그인되었습니다!"
            save_log_entry(student_id, ip_address, "2FA_ACCOUNT_SCOPED_LOGIN", user_agent, 0.0, 0, attack_type="LEGITIMATE")
            save_log_entry(student_id, ip_address, "SUCCESS", user_agent, 0.0, 0, attack_type="LEGITIMATE")
            return jsonify({
                "status": "SUCCESS",
                "message": message,
                "risk_score": "0.0%",
                "model_flag": "LEGITIMATE",
                "user": {
                    "student_id": user_rec["student_id"],
                    "full_name": full_name,
                    "email": user_rec.get("email", ""),
                    "role": user_rec.get("role", "Student"),
                    "status": "ACTIVE"
                }
            }), 200

        else:
            time.sleep(0.3)
            recent_attempts.append({"student_id": student_id, "ip_address": ip_address, "status": "FAILED", "time": now_ts})
            features = extract_incoming_features(student_id, ip_address, user_agent, now_ts)
            features_df = pd.DataFrame([features], columns=FEATURE_COLS)
            computed_risk = round(ml_detector.predict_proba(features_df)[0][1] * 100, 1)
            risk_score_val = max(computed_risk, 90.0)
            att_type = classify_attack_type(features)
            save_log_entry(student_id, ip_address, "BLOCKED", user_agent, risk_score_val, 1, attack_type=att_type)
            return jsonify({
                "status": "MALICIOUS_ATTACK_BLOCKED",
                "can_2fa_recover": False,
                "risk_score": f"{risk_score_val}%",
                "attack_type": att_type,
                "action_taken": f"IP 차단 유지됨: {ip_address}",
                "message": f"⚠️ [보안 차단] IP 주소가 차단된 상태입니다! 2FA 복구가 불가능합니다."
            }), 429

    # A. 실시간 6차원 특징 벡터 계산
    features = extract_incoming_features(student_id, ip_address, user_agent, now_ts)
    features_df = pd.DataFrame([features], columns=FEATURE_COLS)

    # B. ML 모델 기반 이상 및 Risk Score 계산
    is_attack = ml_detector.predict(features_df)[0]
    risk_score = round(ml_detector.predict_proba(features_df)[0][1] * 100, 1)

    # Check if student account was recently 2FA rescued/verified
    is_2fa_rescued = (student_id in VERIFIED_2FA_RESCUED_ACCOUNTS and now_ts < VERIFIED_2FA_RESCUED_ACCOUNTS[student_id])

    # C. Anomaly Defense: IP 차단 및 계정 SUSPENDED 자동 전환
    if (is_attack == 1 or risk_score >= 50.0) and not is_2fa_rescued:
        time.sleep(0.5)
        BLOCKED_ENTITIES.add(ip_address)
        
        # 사용자 계정은 IP 차단과 별개로 SUSPENDED로 자동 전환
        if student_id and student_id != "admin":
            update_user_status_in_db(student_id, "SUSPENDED")
            
        recent_attempts.append({"student_id": student_id, "ip_address": ip_address, "status": "FAILED", "time": now_ts})
        att_type = classify_attack_type(features)
        save_log_entry(student_id, ip_address, "BLOCKED", user_agent, risk_score, 1, attack_type=att_type)

        return jsonify({
            "status": "MALICIOUS_ATTACK_BLOCKED",
            "risk_score": f"{risk_score}%",
            "attack_type": att_type,
            "action_taken": f"IP 차단 완료: {ip_address} | 계정 SUSPENDED 전환: {student_id}",
            "message": f"⚠️ [ML Alert] 이상 트래픽 탐지! ({att_type}) IP 주소가 차단되었으며, '{student_id}' 계정이 SUSPENDED 상태로 전환되었습니다."
        }), 429

    # D. 정상 사용자 로그인
    if user_rec and check_user_password(user_rec.get("password"), password):
        status = "SUCCESS"
        full_name = user_rec.get("full_name", student_id)
        message = f"성공적으로 로그인되었습니다! 환영합니다 {full_name}님."
        http_code = 200
        user_info = {
            "student_id": user_rec["student_id"],
            "full_name": full_name,
            "email": user_rec.get("email", ""),
            "role": user_rec.get("role", "Student"),
            "status": user_rec.get("status", "ACTIVE")
        }
        recent_attempts.append({"student_id": student_id, "ip_address": ip_address, "status": status, "time": now_ts})
        save_log_entry(student_id, ip_address, status, user_agent, risk_score, 0, attack_type="LEGITIMATE")
    else:
        status = "FAILED"
        message = f"사용자 아이디 또는 비밀번호가 올바르지 않습니다!"
        http_code = 400
        user_info = None
        
        # 검증: 동일 계정에 5회 연속 비밀번호 오류 발생 시 계정을 SUSPENDED로 자동 전환
        user_failed_count = sum(
            1 for l in recent_attempts 
            if l.get("student_id") == student_id and l.get("status") == "FAILED"
        ) + 1  # current attempt makes it +1
        
        if user_failed_count >= 5 and student_id and student_id != "admin":
            update_user_status_in_db(student_id, "SUSPENDED")
            message = f"⚠️ [Security Restriction] 비밀번호를 5회 연속 잘못 입력하여 '{student_id}' 계정이 SUSPENDED 상태로 전환되었습니다."

        recent_attempts.append({"student_id": student_id, "ip_address": ip_address, "status": status, "time": now_ts})
        
        att_type = classify_attack_type(features)
        is_attack_flag = 1 if (user_failed_count >= 3 or risk_score >= 35.0 or is_bot_user_agent(user_agent) == 1) else 0
        actual_attack_type = att_type if is_attack_flag == 1 else "LEGITIMATE"
        save_log_entry(student_id, ip_address, status, user_agent, risk_score, is_attack_flag, attack_type=actual_attack_type)

    return jsonify({
        "status": status,
        "message": message,
        "risk_score": f"{risk_score}%",
        "model_flag": "LEGITIMATE",
        "user": user_info
    }), http_code

# =========================================================
# 6. B. EMAIL 2FA ACCOUNT RECOVERY & PASSWORD RESET ENDPOINTS
# =========================================================
OTP_STORE = {}
VERIFIED_2FA_RESCUED_ACCOUNTS = {}

import re

def validate_password_strength(password):
    if not password or len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."
    if not re.search(r'[A-Z]', password):
        return False, "비밀번호에 최소 1개 이상의 대문자(A-Z)가 포함되어야 합니다."
    if not re.search(r'[a-z]', password):
        return False, "비밀번호에 최소 1개 이상의 소문자(a-z)가 포함되어야 합니다."
    if not re.search(r'\d', password):
        return False, "비밀번호에 최소 1개 이상의 숫자(0-9)가 포함되어야 합니다."
    if not re.search(r'[^a-zA-Z0-9]', password):
        return False, "비밀번호에 최소 1개 이상의 특수문자(!@#$%^&*)가 포함되어야 합니다."
    return True, ""

@app.route("/api/user/2fa/request-otp", methods=["POST"])
def request_2fa_otp():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    email = data.get("email", "").strip()

    if not student_id or not email:
        return jsonify({
            "status": "FAILED",
            "can_2fa_recover": False,
            "message": "❌ 학번/아이디와 이메일 주소를 모두 입력해 주세요!"
        }), 400

    # 1. Check if student_id exists in DB
    user_rec = get_user_from_db(student_id)
    if not user_rec:
        return jsonify({
            "status": "FAILED",
            "can_2fa_recover": False,
            "message": f"❌ 입력하신 학번('{student_id}')을 시스템에서 찾을 수 없습니다."
        }), 400

    # 2. Check if student_id and email MATCH each other in DB!
    user_email_in_db = user_rec.get("email", "").strip().lower()
    input_email_clean = email.strip().lower()

    if user_email_in_db != input_email_clean:
        return jsonify({
            "status": "FAILED",
            "can_2fa_recover": False,
            "message": f"❌ 학번('{student_id}')과 입력하신 이메일('{email}') 정보가 일치하지 않습니다!"
        }), 400

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()

    # Rate Limiting Check for OTP Request
    limit_otp_rpm = int(os.environ.get("RATE_LIMIT_OTP_PER_MINUTE", 5))
    if rate_limiter.is_rate_limited(f"otp_{ip_address}", limit_count=limit_otp_rpm, window_seconds=60):
        return jsonify({
            "status": "FAILED",
            "can_2fa_recover": False,
            "message": "⚠️ [보안 제한] OTP 인증 코드 요청이 너무 잦습니다. 1분 후 다시 시도해 주세요."
        }), 429

    # Rule Check: Blocked attacker IP cannot request 2FA OTP for other accounts
    if ip_address in BLOCKED_ENTITIES and not is_known_user_ip(student_id, ip_address):
        return jsonify({
            "status": "FAILED",
            "can_2fa_recover": False,
            "message": "🚨 차단된 공격자 IP 주소에서는 타인의 2FA 인증 코드를 요청할 수 없습니다!"
        }), 429

    import random
    otp = f"{random.randint(100000, 999999)}"
    OTP_STORE[input_email_clean] = {
        "student_id": student_id,
        "email": user_rec.get("email"),
        "otp": otp,
        "expires_at": time.time() + 300,
        "attempts": 0
    }

    send_real_email_otp(user_rec.get("email"), otp, student_id)

    print("\n" + "="*65)
    print(f" 📧 [SECUREAUTH 2FA RESCUE EMAIL] To: {user_rec.get('email')} (User: {student_id})")
    print(f" 🔑 OTP Verification Code: [{otp}]")
    print(f" ⏰ Valid for 5 Minutes (300s)")
    print("="*65 + "\n")

    return jsonify({
        "status": "SUCCESS",
        "student_id": student_id,
        "email": user_rec.get("email"),
        "mock_otp": otp,
        "message": f"📧 학번('{student_id}')과 이메일 정보가 확인되었습니다. 6자리 OTP 코드가 '{user_rec.get('email')}' 주소로 발송되었습니다."
    }), 200

@app.route("/api/user/2fa/verify-unsuspend", methods=["POST"])
def verify_unsuspend_2fa():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    email = data.get("email", "").strip().lower()
    otp_code = data.get("otp_code", "").strip()
    new_password = data.get("new_password", "").strip()

    if not email or email not in OTP_STORE:
        return jsonify({"status": "FAILED", "message": "⚠️ 활성화된 인증 코드가 없습니다. 코드를 다시 요청해 주세요."}), 400

    otp_info = OTP_STORE[email]
    expected_student_id = otp_info["student_id"]
    now_ts = time.time()

    if student_id and student_id != expected_student_id:
        return jsonify({"status": "FAILED", "message": "❌ 요청한 학번 정보가 초기 인증 정보와 일치하지 않습니다."}), 400

    if now_ts > otp_info["expires_at"]:
        del OTP_STORE[email]
        return jsonify({"status": "FAILED", "message": "⌛ 인증 코드 유효 시간이 만료되었습니다 (5분). 새 코드를 요청해 주세요."}), 400

    otp_info["attempts"] += 1
    if otp_info["attempts"] > 5:
        del OTP_STORE[email]
        return jsonify({"status": "FAILED", "message": "🚨 잘못된 코드를 5회 이상 입력하여 인증 코드가 무효화되었습니다."}), 400

    if otp_code != otp_info["otp"]:
        rem = 5 - otp_info["attempts"]
        return jsonify({"status": "FAILED", "message": f"❌ 잘못된 OTP 코드입니다! (남은 시도 횟수: {rem}회)"}), 400

    # Password strength check
    if new_password:
        is_valid, err_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({"status": "FAILED", "message": f"❌ 비밀번호 규칙 오류: {err_msg}"}), 400

    # Verification successful!
    del OTP_STORE[email]

    # 1. Update status (and password if provided) in users.db (syncs to JSON and CSV)
    if new_password:
        update_user_password_and_status_in_db(expected_student_id, new_password, "ACTIVE")
    else:
        update_user_status_in_db(expected_student_id, "ACTIVE")

    # 2. Register student_id in VERIFIED_2FA_RESCUED_ACCOUNTS (valid for 15 mins)
    VERIFIED_2FA_RESCUED_ACCOUNTS[expected_student_id] = now_ts + 900

    # 3. Discard IP from BLOCKED_ENTITIES for this verified user & reset buffer
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
        
    BLOCKED_ENTITIES.discard(ip_address)
    recent_attempts[:] = [l for l in recent_attempts if l.get("student_id") != expected_student_id and l.get("ip_address") != ip_address]

    # 4. Log event
    user_agent = request.headers.get("User-Agent", "Unknown")
    save_log_entry(expected_student_id, ip_address, "2FA_PASSWORD_RESET_SUCCESS", user_agent, 0.0, 0, attack_type="LEGITIMATE")

    user_rec = get_user_from_db(expected_student_id)
    return jsonify({
        "status": "SUCCESS",
        "student_id": expected_student_id,
        "message": f"🎉 학번('{expected_student_id}')과 이메일 2FA 인증 성공! 비밀번호가 규칙에 맞춰 변경되었으며 ACTIVE 상태로 정상 복구되었습니다.",
        "new_password": new_password if new_password else user_rec.get("password"),
        "user": {
            "student_id": user_rec["student_id"],
            "full_name": user_rec.get("full_name", expected_student_id),
            "email": user_rec.get("email", ""),
            "role": user_rec.get("role", "Student"),
            "status": "ACTIVE"
        }
    }), 200

# =========================================================
# 7. ROLE-BASED ACCESS CONTROL (RBAC) & PAGINATED APIs
# =========================================================
@app.route("/api/user/logs", methods=["GET"])
def get_user_logs():
    student_id = request.args.get("student_id", "")
    if not student_id:
        return jsonify({"error": "student_id가 필요합니다."}), 400
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, student_id, ip_address, status, user_agent, risk_score, is_attack, attack_type
            FROM auth_logs
            WHERE student_id = ?
            ORDER BY id DESC LIMIT 100
        ''', (student_id,))
        rows = cursor.fetchall()
        conn.close()
        
        logs = [{
            "id": r[0], "timestamp": r[1], "student_id": r[2],
            "ip_address": r[3], "status": r[4], "user_agent": r[5],
            "risk_score": r[6], "is_attack": r[7], "attack_type": r[8] if len(r) > 8 else "LEGITIMATE"
        } for r in rows]
        return jsonify({"status": "SUCCESS", "logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/logs", methods=["GET"])
def get_admin_logs():
    status_filter = request.args.get("status", "ALL")
    search_query = request.args.get("search", "")
    
    # 10페이지 페이징 파라미터 (100 Log x 10 Page = 총 1,000 Log)
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 100))
    if page < 1: page = 1
    if page > 10: page = 10
    if per_page > 100: per_page = 100

    offset = (page - 1) * per_page
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        base_where = " FROM auth_logs WHERE 1=1"
        params = []
        
        if status_filter != "ALL":
            if status_filter in ("IP Rotation Spraying", "Password Spraying", "Brute Force / DoS", "Automated Bot Traffic"):
                base_where += " AND attack_type = ?"
                params.append(status_filter)
            else:
                base_where += " AND status = ?"
                params.append(status_filter)
            
        if search_query:
            base_where += " AND (student_id LIKE ? OR ip_address LIKE ? OR attack_type LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
            
        # Total matching records (Max limit 1,000)
        cursor.execute("SELECT COUNT(*)" + base_where, params)
        raw_total = cursor.fetchone()[0]
        total_records = min(raw_total, 1000)
        total_pages = max(1, min(10, math.ceil(total_records / per_page)))

        # Fetch paginated logs
        query = "SELECT id, timestamp, student_id, ip_address, status, user_agent, risk_score, is_attack, attack_type" + base_where + " ORDER BY id DESC LIMIT ? OFFSET ?"
        query_params = params + [per_page, offset]
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        conn.close()
        
        logs = [{
            "id": r[0], "timestamp": r[1], "student_id": r[2],
            "ip_address": r[3], "status": r[4], "user_agent": r[5],
            "risk_score": r[6], "is_attack": r[7], "attack_type": r[8] if len(r) > 8 else "LEGITIMATE"
        } for r in rows]
        
        return jsonify({
            "status": "SUCCESS",
            "logs": logs,
            "page": page,
            "per_page": per_page,
            "total_records": total_records,
            "total_pages": total_pages
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/stats", methods=["GET"])
def get_admin_stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM auth_logs")
        total_traffic = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM auth_logs WHERE status = 'SUCCESS'")
        total_success = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM auth_logs WHERE status = 'FAILED'")
        total_failed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM auth_logs WHERE status = 'BLOCKED' OR is_attack = 1")
        total_blocked = cursor.fetchone()[0]
        
        conn.close()

        suspended_users = []
        try:
            u_conn = sqlite3.connect(USERS_DB_FILE)
            u_cursor = u_conn.cursor()
            u_cursor.execute("SELECT student_id, full_name, email, status FROM users WHERE status IN ('SUSPENDED', 'LOCKED', 'INACTIVE', 'DISABLED') ORDER BY student_id ASC")
            suspended_users = [
                {"student_id": row[0], "full_name": row[1] or "", "email": row[2] or "", "status": row[3]}
                for row in u_cursor.fetchall()
            ]
            u_conn.close()
        except Exception as u_err:
            print(f"[!] Querying suspended users failed: {u_err}")
        
        return jsonify({
            "status": "SUCCESS",
            "total_traffic": total_traffic,
            "total_success": total_success,
            "total_failed": total_failed,
            "total_blocked": total_blocked,
            "blocked_ips": sorted(list(BLOCKED_ENTITIES)),
            "suspended_users": suspended_users,
            "active_window_size": len(recent_attempts)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/unblock", methods=["POST"])
def admin_unblock():
    data = request.get_json() or {}
    target = data.get("target", "").strip()
    requester_role = data.get("requester_role", "Admin")

    if requester_role == "Analyst":
        return jsonify({"error": "⛔ 접근 거부! Analyst(분석가) 역할은 IP 차단을 해제할 수 없습니다. 시스템 관리자(Admin)에게 문의하세요."}), 403
    
    if not target:
        return jsonify({"error": "unblock target (IP 또는 student_id) 정보가 필요합니다."}), 400
        
    global recent_attempts
    BLOCKED_ENTITIES.discard(target)
    
    update_user_status_in_db(target, "ACTIVE")
    
    recent_attempts[:] = [
        l for l in recent_attempts 
        if l.get("ip_address") != target and l.get("student_id") != target
    ]
    
    save_log_entry(target, target, "UNBLOCKED_BY_ADMIN", "Admin Console", 0.0, 0, attack_type="UNBLOCKED")
    
    return jsonify({
        "status": "SUCCESS",
        "message": f"요청하신 '{target}' 대상의 차단/정지 상태가 성공적으로 해제되었습니다!",
        "unblocked_target": target,
        "remaining_blocked": sorted(list(BLOCKED_ENTITIES))
    })

# =========================================================
# 8. ADMIN USER MANAGEMENT APIs (Immutable Admin Account Protection)
# =========================================================
@app.route("/api/admin/users", methods=["GET"])
def get_users_list():
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "ALL")
    status_filter = request.args.get("status", "ALL")
    
    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        
        query = "SELECT student_id, password, full_name, email, role, status, created_at FROM users WHERE 1=1"
        params = []
        
        if role_filter != "ALL":
            query += " AND role = ?"
            params.append(role_filter)
            
        if status_filter != "ALL":
            query += " AND status = ?"
            params.append(status_filter)
            
        if search:
            query += " AND (student_id LIKE ? OR full_name LIKE ? OR email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            
        query += " ORDER BY id ASC LIMIT 200"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        users = [{
            "student_id": r[0],
            "password": r[1],
            "full_name": r[2],
            "email": r[3],
            "role": r[4],
            "status": r[5],
            "created_at": r[6]
        } for r in rows]
        
        return jsonify({"status": "SUCCESS", "users": users, "total": len(users)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/users/add", methods=["POST"])
def add_new_user():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    role = data.get("role", "Student").strip()
    status = data.get("status", "ACTIVE").strip()
    
    if not student_id or not password:
        return jsonify({"error": "Student ID 및 비밀번호는 필수 입력 항목입니다."}), 400
        
    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM users WHERE student_id = ?", (student_id,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"'{student_id}' ID를 가진 사용자가 이미 존재합니다."}), 400
            
        created_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor.execute('''
            INSERT INTO users (student_id, password, full_name, email, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, password, full_name, email, role, status, created_at))
        conn.commit()
        conn.close()
        
        sync_users_to_json_csv()
        return jsonify({"status": "SUCCESS", "message": f"신규 사용자 '{student_id}' 계정이 생성되었습니다!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/users/update", methods=["POST"])
def update_user_info():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    role = data.get("role")
    status = data.get("status")
    
    if not student_id:
        return jsonify({"error": "student_id가 필요합니다."}), 400
        
    # PRIMARY ADMIN PROTECTION: Cannot change role or status of primary 'admin' account
    if student_id == "admin":
        return jsonify({"error": "🔒 최고 관리자 'admin' 계정의 권한 및 상태는 변경할 수 없습니다 (Protected Admin Account)!"}), 400

    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        
        if role:
            cursor.execute("UPDATE users SET role = ? WHERE student_id = ?", (role, student_id))
        if status:
            cursor.execute("UPDATE users SET status = ? WHERE student_id = ?", (status, student_id))
            
        conn.commit()
        conn.close()
        
        sync_users_to_json_csv()
        return jsonify({"status": "SUCCESS", "message": f"'{student_id}' 사용자 정보가 업데이트되었습니다!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/users/delete", methods=["POST"])
def delete_user_account():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    
    if not student_id:
        return jsonify({"error": "student_id가 필요합니다."}), 400
    if student_id == "admin":
        return jsonify({"error": "🔒 최고 관리자 'admin' 계정은 삭제할 수 없습니다 (Protected Admin Account)!"}), 400
        
    try:
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE student_id = ?", (student_id,))
        conn.commit()
        conn.close()
        
        sync_users_to_json_csv()
        return jsonify({"status": "SUCCESS", "message": f"'{student_id}' 계정이 시스템에서 완전히 삭제되었습니다!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# 9. SECURITY ANALYST LOG ANALYTICS APIs
# =========================================================
@app.route("/api/analyst/analytics", methods=["GET"])
def get_analyst_analytics():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Attack type breakdown counts
        cursor.execute('''
            SELECT attack_type, COUNT(*) 
            FROM auth_logs 
            WHERE status = 'BLOCKED' OR is_attack = 1
            GROUP BY attack_type
        ''')
        attack_counts = dict(cursor.fetchall())
        
        # 2. Top threat IPs
        cursor.execute('''
            SELECT ip_address, COUNT(*) as attack_count 
            FROM auth_logs 
            WHERE status = 'BLOCKED' OR is_attack = 1
            GROUP BY ip_address 
            ORDER BY attack_count DESC LIMIT 5
        ''')
        top_ips = [{"ip": r[0], "count": r[1]} for r in cursor.fetchall()]
        
        # 3. Top target users
        cursor.execute('''
            SELECT student_id, COUNT(*) as attack_count 
            FROM auth_logs 
            WHERE status = 'BLOCKED' OR is_attack = 1
            GROUP BY student_id 
            ORDER BY attack_count DESC LIMIT 5
        ''')
        top_targets = [{"student_id": r[0], "count": r[1]} for r in cursor.fetchall()]

        # 4. Recent Threat Logs with details
        cursor.execute('''
            SELECT id, timestamp, student_id, ip_address, status, user_agent, risk_score, attack_type
            FROM auth_logs
            WHERE status = 'BLOCKED' OR is_attack = 1
            ORDER BY id DESC LIMIT 20
        ''')
        rows = cursor.fetchall()
        recent_threats = [{
            "id": r[0], "timestamp": r[1], "student_id": r[2],
            "ip_address": r[3], "status": r[4], "user_agent": r[5],
            "risk_score": r[6], "attack_type": r[7] or "Unknown Attack"
        } for r in rows]
        
        conn.close()
        
        return jsonify({
            "status": "SUCCESS",
            "attack_counts": {
                "ip_rotation": attack_counts.get("IP Rotation Spraying", 0),
                "password_spraying": attack_counts.get("Password Spraying", 0),
                "brute_force": attack_counts.get("Brute Force / DoS", 0),
                "bot_traffic": attack_counts.get("Automated Bot Traffic", 0),
                "other": attack_counts.get("Anomaly Threshold Exceeded", 0)
            },
            "top_threat_ips": top_ips,
            "top_target_users": top_targets,
            "recent_threats": recent_threats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# 8. ATTACKER CONTROL CENTER ENDPOINTS (Single-Port & Cloud PaaS Deployment Ready)
# =========================================================
import live_attack_simulator

@app.route("/attacker", methods=["GET"])
@app.route("/attacker/", methods=["GET"])
def attacker_dashboard_page():
    return render_template("attacker.html")

@app.route("/api/students", methods=["GET"])
def get_students_api():
    students = live_attack_simulator.fetch_student_accounts()
    return jsonify({"status": "SUCCESS", "students": students})

@app.route("/api/attack/brute_force", methods=["POST"])
def launch_brute_force_api():
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
def launch_password_spraying_api():
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
def launch_ip_rotation_api():
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
def launch_bot_traffic_api():
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
def start_continuous_api():
    started = live_attack_simulator.start_continuous_traffic()
    return jsonify({
        "status": "SUCCESS",
        "is_running": live_attack_simulator.is_continuous_running,
        "message": "실시간 무한 트래픽 전송이 시작되었습니다." if started else "이미 실행 중입니다."
    })

@app.route("/api/attack/continuous/stop", methods=["POST"])
def stop_continuous_api():
    stopped = live_attack_simulator.stop_continuous_traffic()
    return jsonify({
        "status": "SUCCESS",
        "is_running": live_attack_simulator.is_continuous_running,
        "message": "실시간 무한 트래픽 전송이 중지되었습니다." if stopped else "실행 중이 아닙니다."
    })

@app.route("/api/attack/continuous/status", methods=["GET"])
def get_continuous_status_api():
    return jsonify({
        "status": "SUCCESS",
        "is_running": live_attack_simulator.is_continuous_running
    })

@app.route("/api/attack/logs", methods=["GET"])
def get_attack_logs_api():
    return jsonify({
        "status": "SUCCESS",
        "logs": live_attack_simulator.attack_history_logs[-50:],
        "is_running": live_attack_simulator.is_continuous_running
    })

@app.route("/api/attack/logs/clear", methods=["POST"])
def clear_attack_logs_api():
    live_attack_simulator.clear_attacker_logs()
    return jsonify({
        "status": "SUCCESS",
        "message": "공격자 콘솔 로그가 성공적으로 지워졌습니다."
    })

@app.route("/api/reset", methods=["POST"])
def reset_system_api():
    live_attack_simulator.clear_attacker_logs()
    return jsonify({"status": "SUCCESS", "message": "공격자 전용 DB(attacker_logs.db) 및 로그가 초기화되었습니다."})

import subprocess
import atexit
import socket

child_processes = []

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def cleanup_subservers():
    for p in child_processes:
        try:
            p.terminate()
            p.wait(timeout=1)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

def launch_subservers():
    python_exe = sys.executable
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Launch Attacker Control Center (Port 5001)
    attacker_script = os.path.join(base_dir, "Attacker", "attacker_app.py")
    if os.path.exists(attacker_script):
        if not is_port_open(5001):
            print("[+] Attacker Control Center (Port 5001) 서버를 백그라운드에서 자동으로 실행합니다...")
            p1 = subprocess.Popen([python_exe, attacker_script], cwd=base_dir)
            child_processes.append(p1)
        else:
            print("[✔] Attacker Control Center (Port 5001) 서버가 이미 실행 중입니다.")

    if child_processes:
        atexit.register(cleanup_subservers)

if __name__ == "__main__":
    launch_subservers()
    print("=======================================================================")
    print(" 🚀 SECUREAUTH INTEGRATED SECURITY SYSTEM RUNNING ")
    print(" 🛡️ 1. Main SSO Security Server: http://127.0.0.1:5000")
    print(" ☠️ 2. Attacker Control Console: http://127.0.0.1:5001")
    print("=======================================================================")
    app.run(host="0.0.0.0", port=5000, debug=False)