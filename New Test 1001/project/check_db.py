import sqlite3
import json
import os

print("--- USERS.DB ---")
if os.path.exists('users.db'):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, password, role, status FROM users WHERE student_id IN ('admin', 'analyst', '20260001', '20260002')")
    for r in cursor.fetchall():
        print("DB:", r)
    conn.close()

print("--- USERS.JSON ---")
if os.path.exists('users.json'):
    with open('users.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        for u in data:
            if u.get('student_id') in ['admin', 'analyst', '20260001', '20260002']:
                print("JSON:", u['student_id'], u.get('role'), u.get('status'))
