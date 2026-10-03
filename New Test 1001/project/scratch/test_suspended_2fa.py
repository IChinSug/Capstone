import unittest
import json
import app as flask_app

class TestSuspendedUser2FARedirection(unittest.TestCase):
    def setUp(self):
        flask_app.app.config['TESTING'] = True
        self.client = flask_app.app.test_client()

    def test_suspended_user_login_triggers_2fa(self):
        # 1. Set user '20260002' to SUSPENDED status
        flask_app.update_user_status_in_db("20260002", "SUSPENDED")

        # 2. Attempt login as '20260002'
        res = self.client.post('/login', json={
            "student_id": "20260002",
            "password": "Password2026"
        })

        data = res.get_json()
        self.assertEqual(res.status_code, 403)
        self.assertEqual(data["status"], "ACCOUNT_SUSPENDED")
        self.assertTrue(data["can_2fa_recover"])
        self.assertEqual(data["student_id"], "20260002")
        self.assertIn("student2@school.edu.kr", data["email"])
        print("[✔] Suspended user login correctly triggers 2FA modal redirection! Email:", data["email"])

    def test_inactive_user_login_triggers_2fa(self):
        # 1. Set user '20260003' to INACTIVE status
        flask_app.update_user_status_in_db("20260003", "INACTIVE")

        # 2. Attempt login as '20260003'
        res = self.client.post('/login', json={
            "student_id": "20260003",
            "password": "SecurePass#1"
        })

        data = res.get_json()
        self.assertEqual(res.status_code, 403)
        self.assertEqual(data["status"], "ACCOUNT_SUSPENDED")
        self.assertTrue(data["can_2fa_recover"])
        self.assertEqual(data["student_id"], "20260003")
        print("[✔] Inactive user login correctly triggers 2FA modal redirection!")

if __name__ == "__main__":
    unittest.main()
