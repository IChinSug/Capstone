import unittest
import json
import app as flask_app

class Test2FAAndPasswordStrength(unittest.TestCase):
    def setUp(self):
        flask_app.app.config['TESTING'] = True
        self.client = flask_app.app.test_client()

    def test_student_id_email_mismatch(self):
        res = self.client.post('/api/user/2fa/request-otp', json={
            "student_id": "20260001",
            "email": "wrongemail@test.com"
        })
        data = res.get_json()
        self.assertEqual(res.status_code, 400)
        self.assertIn("일치하지 않습니다", data["message"])
        print("[✔] Mismatch test passed:", data["message"])

    def test_student_id_email_match_and_password_strength(self):
        # 1. Get correct user email from DB
        user = flask_app.get_user_from_db("20260001")
        self.assertIsNotNone(user)
        email = user["email"]

        # 2. Request OTP with matching student_id and email
        res = self.client.post('/api/user/2fa/request-otp', json={
            "student_id": "20260001",
            "email": email
        })
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        otp = data["mock_otp"]
        print("[✔] Matching request OTP test passed. Mock OTP:", otp)

        # 3. Verify OTP with WEAK password (fails validation)
        res_weak = self.client.post('/api/user/2fa/verify-unsuspend', json={
            "student_id": "20260001",
            "email": email,
            "otp_code": otp,
            "new_password": "weak"
        })
        data_weak = res_weak.get_json()
        self.assertEqual(res_weak.status_code, 400)
        self.assertIn("비밀번호 규칙 오류", data_weak["message"])
        print("[✔] Weak password rejection test passed:", data_weak["message"])

        # 4. Verify OTP with STRONG password (succeeds)
        res_strong = self.client.post('/api/user/2fa/verify-unsuspend', json={
            "student_id": "20260001",
            "email": email,
            "otp_code": otp,
            "new_password": "StrongPassword123!"
        })
        data_strong = res_strong.get_json()
        self.assertEqual(res_strong.status_code, 200)
        self.assertEqual(data_strong["status"], "SUCCESS")
        print("[✔] Strong password reset test passed:", data_strong["message"])

if __name__ == "__main__":
    unittest.main()
