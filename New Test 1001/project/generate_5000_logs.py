import sys
import io
import os
import json
import csv
import sqlite3
import random
import datetime

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

DB_FILE = "auth_logs.db"
LOG_FILE = "auth.log"
USERS_CSV_FILE = "users.csv"

# Real browser User-Agents
LEGIT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

BOT_USER_AGENTS = [
    "Python-requests/2.31.0",
    "Hydra/9.2 (Automated BruteForce Engine)",
    "Nmap Scripting Engine (http-form-brute)",
    "curl/7.68.0",
    "Go-http-client/1.1",
    "Wget/1.21.2"
]

def load_student_ids():
    student_ids = []
    if os.path.exists(USERS_CSV_FILE):
        with open(USERS_CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("student_id"):
                    student_ids.append(row["student_id"])
    if not student_ids:
        student_ids = [f"2026{i:04d}" for i in range(1, 201)]
    return student_ids

def random_ip():
    return f"{random.randint(1,223)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"

def generate_5000_logs():
    print("=========================================================")
    print(" 5,000 TRAFFIC LOG GENERATOR (USING 200 USERS FROM users.csv)")
    print("=========================================================")
    
    student_ids = load_student_ids()
    print(f"[+] Loaded {len(student_ids)} student IDs from '{USERS_CSV_FILE}'")

    logs = []
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Generate random timestamps spread over the last 5 days
    timestamps = [
        now - datetime.timedelta(seconds=random.randint(1, 5 * 86400))
        for _ in range(5000)
    ]
    timestamps.sort()

    # Target composition:
    # 1. 3,250 Legitimate logins (65%)
    # 2. 600 Password Spraying logs (12%)
    # 3. 600 IP Rotation Spraying logs (12%)
    # 4. 300 Brute Force / DoS logs (6%)
    # 5. 250 Automated Bot Traffic logs (5%)

    # Category 1: Legitimate logins (3,250)
    for i in range(3250):
        ts = timestamps[i].isoformat()
        sid = random.choice(student_ids)
        ip = f"192.168.1.{random.randint(2, 250)}" if random.random() < 0.7 else f"10.0.0.{random.randint(2, 250)}"
        ua = random.choice(LEGIT_USER_AGENTS)
        
        # 95% SUCCESS, 5% FAILED (typo)
        if random.random() < 0.95:
            status = "SUCCESS"
            risk = round(random.uniform(0.0, 15.0), 1)
        else:
            status = "FAILED"
            risk = round(random.uniform(15.0, 35.0), 1)
            
        logs.append((ts, sid, ip, status, ua, risk, 0, "LEGITIMATE"))

    # Category 2: Password Spraying logs (600)
    spray_ips = [random_ip() for _ in range(10)]
    for i in range(3250, 3850):
        ts = timestamps[i].isoformat()
        sid = random.choice(student_ids)
        ip = random.choice(spray_ips)
        ua = random.choice(LEGIT_USER_AGENTS)
        status = "BLOCKED"
        risk = round(random.uniform(65.0, 92.0), 1)
        logs.append((ts, sid, ip, status, ua, risk, 1, "Password Spraying"))

    # Category 3: IP Rotation Spraying logs (600)
    for i in range(3850, 4450):
        ts = timestamps[i].isoformat()
        sid = random.choice(student_ids)
        ip = random_ip()
        ua = random.choice(LEGIT_USER_AGENTS)
        status = "BLOCKED"
        risk = round(random.uniform(75.0, 98.0), 1)
        logs.append((ts, sid, ip, status, ua, risk, 1, "IP Rotation Spraying"))

    # Category 4: Brute Force / DoS logs (300)
    target_sids = ["20260001", "20260002", "20260003", "20260005"]
    bf_ips = ["45.33.32.156", "185.220.101.5", "103.253.145.8"]
    for i in range(4450, 4750):
        ts = timestamps[i].isoformat()
        sid = random.choice(target_sids)
        ip = random.choice(bf_ips)
        ua = random.choice(BOT_USER_AGENTS)
        status = "BLOCKED"
        risk = round(random.uniform(85.0, 100.0), 1)
        logs.append((ts, sid, ip, status, ua, risk, 1, "Brute Force / DoS"))

    # Category 5: Automated Bot Traffic logs (250)
    for i in range(4750, 5000):
        ts = timestamps[i].isoformat()
        sid = random.choice(student_ids)
        ip = random_ip()
        ua = random.choice(BOT_USER_AGENTS)
        status = "BLOCKED"
        risk = round(random.uniform(90.0, 100.0), 1)
        logs.append((ts, sid, ip, status, ua, risk, 1, "Automated Bot Traffic"))

    # Shuffle slightly within timestamps and populate DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS auth_logs")
    cursor.execute('''
        CREATE TABLE auth_logs (
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

    cursor.executemany('''
        INSERT INTO auth_logs (timestamp, student_id, ip_address, status, user_agent, risk_score, is_attack, attack_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', logs)

    conn.commit()
    conn.close()

    # Re-write auth.log in JSON lines format
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        for r in logs:
            entry = {
                "timestamp": r[0],
                "student_id": r[1],
                "ip_address": r[2],
                "status": r[3],
                "user_agent": r[4],
                "risk_score": r[5],
                "is_attack": r[6],
                "attack_type": r[7]
            }
            f.write(json.dumps(entry) + "\n")

    print(f"[✔] 5,000 logs successfully generated in '{DB_FILE}' & '{LOG_FILE}'!")

if __name__ == "__main__":
    generate_5000_logs()
