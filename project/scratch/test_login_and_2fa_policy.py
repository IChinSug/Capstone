import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sqlite3
import unittest
from app import app, BLOCKED_ENTITIES, USERS_DB_FILE, update_user_status_in_db, save_log_entry

class LoginPolicyTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Setup test data in SQLite with explicit password
        from app import update_user_password_and_status_in_db
        update_user_password_and_status_in_db("20260001", "Pass2026#...", "ACTIVE")
        update_user_password_and_status_in_db("20260002", "Pass2026#...", "ACTIVE")

        # Record a previous SUCCESS log for student 20260001 from IP 192.168.1.100
        save_log_entry("20260001", "192.168.1.100", "SUCCESS", "TestUserAgent", 0.0, 0, attack_type="LEGITIMATE")

    def test_successful_login_does_not_remove_ip_from_blocked_list(self):
        # Add IP to blocked list
        BLOCKED_ENTITIES.add("192.168.1.100")

        # 20260001 logs in from known IP 192.168.1.100 with correct password Pass2026#...
        res = self.app.post('/login', json={"student_id": "20260001", "password": "Pass2026#..."}, environ_base={'REMOTE_ADDR': '192.168.1.100'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "SUCCESS")

        # CRITICAL VERIFICATION: IP 192.168.1.100 MUST STAY IN BLOCKED_ENTITIES!
        self.assertIn("192.168.1.100", BLOCKED_ENTITIES)
        print("[✔] Policy Test 1 Passed: Successful login from known IP did NOT remove IP from BLOCKED_ENTITIES.")

    def test_unknown_ip_under_blocked_condition_is_denied_even_with_correct_password(self):
        BLOCKED_ENTITIES.add("45.33.32.156")

        # 20260002 has NO previous SUCCESS log from 45.33.32.156.
        # Test 1: Try correct password from unknown blocked IP -> MUST BE BLOCKED (429)
        res1 = self.app.post('/login', json={"student_id": "20260002", "password": "Pass2026#..."}, environ_base={'REMOTE_ADDR': '45.33.32.156'})
        self.assertEqual(res1.status_code, 429)
        self.assertEqual(res1.get_json()["status"], "MALICIOUS_ATTACK_BLOCKED")

        # Test 2: Try wrong password from unknown blocked IP -> MUST BE BLOCKED (429)
        res2 = self.app.post('/login', json={"student_id": "20260002", "password": "WrongPassword123!"}, environ_base={'REMOTE_ADDR': '45.33.32.156'})
        self.assertEqual(res2.status_code, 429)
        self.assertEqual(res2.get_json()["status"], "MALICIOUS_ATTACK_BLOCKED")

        print("[✔] Policy Test 2 Passed: Unknown IP under block condition denied login for both correct and wrong passwords.")

if __name__ == '__main__':
    unittest.main()
