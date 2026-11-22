import os
import re
import sqlite3
import tempfile
import unittest

import app as app_module


class AccountAuthTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_database = app_module.DATABASE
        self.previous_autoconfirm = os.environ.get("MAK3DEALS_AUTH_AUTOCONFIRM")
        self.previous_require = os.environ.get("MAK3DEALS_AUTH_REQUIRE_EMAIL_VERIFICATION")
        app_module.DATABASE = os.path.join(self.tempdir.name, "accounts.db")
        os.environ["MAK3DEALS_AUTH_AUTOCONFIRM"] = "1"
        os.environ["MAK3DEALS_AUTH_REQUIRE_EMAIL_VERIFICATION"] = "1"
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.DATABASE = self.previous_database
        if self.previous_autoconfirm is None:
            os.environ.pop("MAK3DEALS_AUTH_AUTOCONFIRM", None)
        else:
            os.environ["MAK3DEALS_AUTH_AUTOCONFIRM"] = self.previous_autoconfirm
        if self.previous_require is None:
            os.environ.pop("MAK3DEALS_AUTH_REQUIRE_EMAIL_VERIFICATION", None)
        else:
            os.environ["MAK3DEALS_AUTH_REQUIRE_EMAIL_VERIFICATION"] = self.previous_require
        self.tempdir.cleanup()

    def _csrf(self, path="/login"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="_csrf" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_guest_can_browse_and_signup_login_logout(self):
        self.assertEqual(self.client.get("/daily").status_code, 200)
        csrf = self._csrf("/signup")
        response = self.client.post("/signup", data={
            "_csrf": csrf,
            "display_name": "Test Shopper",
            "email": "shopper@example.com",
            "password": "correct horse battery",
            "password_confirm": "correct horse battery",
            "next": "/account",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/account")
        account = self.client.get("/account")
        self.assertEqual(account.status_code, 200)
        self.assertIn("Hi, Test Shopper.", account.get_data(as_text=True))
        self.assertIn("Email status", account.get_data(as_text=True))

        csrf = self._csrf("/account")
        logout = self.client.post("/logout", data={"_csrf": csrf})
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(self.client.get("/account").status_code, 302)

        csrf = self._csrf("/login")
        login = self.client.post("/login", data={
            "_csrf": csrf,
            "email": "shopper@example.com",
            "password": "correct horse battery",
            "next": "/account",
        })
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login.headers["Location"], "/account")

    def test_password_is_hashed_and_csrf_is_required(self):
        csrf = self._csrf("/signup")
        response = self.client.post("/signup", data={
            "_csrf": csrf,
            "display_name": "Hash Check",
            "email": "hash@example.com",
            "password": "a secure password",
            "password_confirm": "a secure password",
        })
        self.assertEqual(response.status_code, 302)
        connection = sqlite3.connect(app_module.DATABASE)
        stored = connection.execute("SELECT password_hash FROM users WHERE email=?", ("hash@example.com",)).fetchone()[0]
        connection.close()
        self.assertNotEqual(stored, "a secure password")
        self.assertTrue(stored.startswith("scrypt:") or stored.startswith("pbkdf2:"))

        rejected = self.client.post("/logout", data={})
        self.assertEqual(rejected.status_code, 400)

    def test_unverified_account_cannot_login(self):
        os.environ["MAK3DEALS_AUTH_AUTOCONFIRM"] = "0"
        csrf = self._csrf("/signup")
        response = self.client.post("/signup", data={
            "_csrf": csrf,
            "display_name": "Pending Shopper",
            "email": "pending@example.com",
            "password": "a secure password",
            "password_confirm": "a secure password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Verify your email", response.get_data(as_text=True))
        csrf = self._csrf("/login")
        login = self.client.post("/login", data={
            "_csrf": csrf,
            "email": "pending@example.com",
            "password": "a secure password",
        })
        self.assertEqual(login.status_code, 403)
        self.assertIn("verify your email", login.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
