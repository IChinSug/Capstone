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

DB_FILE = "users.db"
JSON_FILE = "users.json"
CSV_FILE = "users.csv"

FIRST_NAMES = [
    "민준", "서준", "도윤", "예준", "시우", "하준", "지호", "주원", "지후", "준서",
    "서연", "서윤", "지우", "서현", "하은", "하윤", "민서", "지유", "윤서", "채원"
]

LAST_NAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권"
]

ROLES = ["Student", "Admin", "Instructor", "Analyst"]

from werkzeug.security import generate_password_hash

def generate_200_users():
    users = []
    
    # 1. Preserved Demo & System Accounts
    demo_accounts = [
        {"student_id": "20260001", "password": "Student123!", "full_name": "김철수", "email": "student1@school.edu.kr", "role": "Student"},
        {"student_id": "20260002", "password": "Password2026", "full_name": "이영희", "email": "student2@school.edu.kr", "role": "Student"},
        {"student_id": "20260003", "password": "SecurePass#1", "full_name": "박민수", "email": "student3@school.edu.kr", "role": "Student"},
        {"student_id": "admin", "password": "admin123", "full_name": "시스템 관리자", "email": "admin@school.edu.kr", "role": "Admin"},
        {"student_id": "user", "password": "user123", "full_name": "일반 사용자", "email": "user@school.edu.kr", "role": "Student"},
        {"student_id": "analyst", "password": "analyst123", "full_name": "보안 분석가", "email": "analyst@school.edu.kr", "role": "Analyst"},
        {"student_id": "teacher1", "password": "TeacherPass2026!", "full_name": "최성민 교수", "email": "teacher1@school.edu.kr", "role": "Instructor"},
        {"student_id": "teacher2", "password": "TeacherPass2026#", "full_name": "정수진 교수", "email": "teacher2@school.edu.kr", "role": "Instructor"},
    ]
    
    existing_ids = set(u["student_id"] for u in demo_accounts)
    
    for account in demo_accounts:
        users.append({
            "student_id": account["student_id"],
            "password": generate_password_hash(account["password"]),
            "full_name": account["full_name"],
            "email": account["email"],
            "role": account["role"],
            "status": "ACTIVE",
            "created_at": "2026-01-15T08:00:00Z"
        })
        
    # 2. Generate remaining users up to 200 records
    random.seed(42)
    current_num = 4
    
    while len(users) < 200:
        student_id = f"2026{current_num:04d}"
        current_num += 1
        
        if student_id in existing_ids:
            continue
            
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{last}{first}"
        email = f"student{current_num}@school.edu.kr"
        password = generate_password_hash(f"Pass2026#{random.randint(100, 999)}")
        role = "Student"
        
        users.append({
            "student_id": student_id,
            "password": password,
            "full_name": full_name,
            "email": email,
            "role": role,
            "status": "ACTIVE",
            "created_at": (datetime.datetime(2026, 1, 15) + datetime.timedelta(hours=len(users))).strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        
    return users

def save_to_sqlite(users):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            role TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    
    for u in users:
        cursor.execute('''
            INSERT INTO users (student_id, password, full_name, email, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (u["student_id"], u["password"], u["full_name"], u["email"], u["role"], u["status"], u["created_at"]))
        
    conn.commit()
    conn.close()

def save_to_json(users):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_to_csv(users):
    fieldnames = ["student_id", "password", "full_name", "email", "role", "status", "created_at"]
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)

def main():
    print("=======================================================================")
    print(" 200명 사용자 DB 및 데이터 파일 생성기 (User Database Generator) ")
    print("=======================================================================")
    
    users = generate_200_users()
    
    save_to_sqlite(users)
    print(f"[✔] SQLite DB 생성 완료: '{DB_FILE}' (Table: users, {len(users)}명)")
    
    save_to_json(users)
    print(f"[✔] JSON 데이터 파일 생성 완료: '{JSON_FILE}' ({len(users)}명)")
    
    save_to_csv(users)
    print(f"[✔] CSV 데이터 파일 생성 완료: '{CSV_FILE}' ({len(users)}명)")
    print("=======================================================================")

if __name__ == "__main__":
    main()
