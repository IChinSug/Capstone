import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sqlite3
import unittest
from app import app, BLOCKED_ENTITIES, USERS_DB_FILE, update_user_status_in_db

class AdminUnblockTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Ensure test user exists in DB and set status to SUSPENDED for testing
        update_user_status_in_db("20260001", "SUSPENDED")
        BLOCKED_ENTITIES.add("192.168.1.99")

    def test_admin_stats_includes_suspended_users_and_blocked_ips(self):
        response = self.app.get('/api/admin/stats')
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("192.168.1.99", data["blocked_ips"])
        
        # Check suspended_users contains 20260001
        suspended_ids = [u["student_id"] for u in data.get("suspended_users", [])]
        self.assertIn("20260001", suspended_ids)
        print(f"[✔] /api/admin/stats test passed: Blocked IP = {data['blocked_ips']}, Suspended = {suspended_ids}")

    def test_admin_unblock_unsuspends_user_and_unblocks_ip(self):
        # 1. Unblock IP
        res1 = self.app.post('/api/admin/unblock', json={"target": "192.168.1.99", "requester_role": "Admin"})
        self.assertEqual(res1.status_code, 200)
        self.assertNotIn("192.168.1.99", BLOCKED_ENTITIES)

        # 2. Unblock Student ID
        res2 = self.app.post('/api/admin/unblock', json={"target": "20260001", "requester_role": "Admin"})
        self.assertEqual(res2.status_code, 200)
        
        # Verify student_id is now ACTIVE in SQLite DB
        conn = sqlite3.connect(USERS_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM users WHERE student_id = '20260001'")
        status = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(status, "ACTIVE")
        print(f"[✔] /api/admin/unblock test passed: User 20260001 status restored to {status}")

if __name__ == '__main__':
    unittest.main()
