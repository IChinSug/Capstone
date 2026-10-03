import os
import sys
import unittest

sys.path.insert(0, ".")

import app as flask_app

class TestProductionSettings(unittest.TestCase):
    def test_env_loaded(self):
        self.assertIsNotNone(os.environ.get("SECRET_KEY"))
        self.assertEqual(flask_app.app.config['SESSION_COOKIE_HTTPONLY'], True)
        self.assertEqual(flask_app.app.config['SESSION_COOKIE_SAMESITE'], 'Lax')
        print("[✔] Test env & session cookie security configurations passed!")

    def test_rate_limiter(self):
        client = flask_app.app.test_client()
        # Fire 20 requests rapidly to trigger rate limit (limit is 15/min)
        exceeded = False
        for i in range(20):
            res = client.post("/login", json={"student_id": "test_rate", "password": "wrong"})
            if res.status_code == 429 and "RATE_LIMIT_EXCEEDED" in res.get_data(as_text=True):
                exceeded = True
                break
        self.assertTrue(exceeded)
        print("[✔] Test rate limiter endpoint protection passed!")

if __name__ == "__main__":
    unittest.main()
