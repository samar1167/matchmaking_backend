import pytest
import requests

BASE_URL = "http://localhost/api"


class TestRegistration:

    def test_register_success(self):
        resp = requests.post(f"{BASE_URL}/auth/register/", json={
            "email": "fresh@test.com",
            "password": "FreshPass123!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["email"] == "fresh@test.com"
        assert "password" not in data  # password must never be returned

    def test_register_duplicate_email(self, register_user_one):
        resp = requests.post(f"{BASE_URL}/auth/register/", json={
            "email": "one@test.com",
            "password": "AnotherPass1!",
        })
        assert resp.status_code == 400

    def test_register_missing_password(self):
        resp = requests.post(f"{BASE_URL}/auth/register/", json={
            "email": "nopw@test.com",
        })
        assert resp.status_code == 400

    def test_register_weak_password(self):
        resp = requests.post(f"{BASE_URL}/auth/register/", json={
            "email": "weak@test.com",
            "password": "123",
        })
        assert resp.status_code == 400


class TestLogin:

    def test_login_success(self, register_user_one):
        resp = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "one@test.com",
            "password": "TestPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_wrong_password(self, register_user_one):
        resp = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "one@test.com",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "nobody@test.com",
            "password": "SomePass1!",
        })
        assert resp.status_code == 401


class TestTokenRefresh:

    def test_refresh_success(self, token_user_one):
        resp = requests.post(f"{BASE_URL}/auth/refresh/", json={
            "refresh": token_user_one["refresh"]
        })
        assert resp.status_code == 200
        assert "access" in resp.json()

    def test_refresh_invalid_token(self):
        resp = requests.post(f"{BASE_URL}/auth/refresh/", json={
            "refresh": "invalid.token.here"
        })
        assert resp.status_code == 401


class TestChangePassword:

    def test_change_password_success(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/auth/change-password/", json={
            "old_password": "TestPass123!",
            "new_password": "UpdatedPass999!",
        }, headers=auth_headers_one)
        assert resp.status_code == 200
        assert "detail" in resp.json()

        # change it back so other tests still work
        token = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "one@test.com", "password": "UpdatedPass999!"
        }).json()
        requests.post(f"{BASE_URL}/auth/change-password/", json={
            "old_password": "UpdatedPass999!",
            "new_password": "TestPass123!",
        }, headers={"Authorization": f"Bearer {token['access']}"})

    def test_change_password_wrong_old(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/auth/change-password/", json={
            "old_password": "WrongOldPass!",
            "new_password": "NewPass999!",
        }, headers=auth_headers_one)
        assert resp.status_code == 400

    def test_change_password_unauthenticated(self):
        resp = requests.post(f"{BASE_URL}/auth/change-password/", json={
            "old_password": "TestPass123!",
            "new_password": "NewPass999!",
        })
        assert resp.status_code == 401


class TestLogout:

    def test_logout_success(self, register_user_one):
        # Login fresh to get a token we can safely blacklist
        token = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "one@test.com", "password": "TestPass123!"
        }).json()
        resp = requests.post(f"{BASE_URL}/auth/logout/", json={
            "refresh": token["refresh"]
        }, headers={"Authorization": f"Bearer {token['access']}"})
        assert resp.status_code == 200

        # Blacklisted token should now be rejected
        retry = requests.post(f"{BASE_URL}/auth/refresh/", json={
            "refresh": token["refresh"]
        })
        assert retry.status_code == 401

    def test_logout_unauthenticated(self):
        resp = requests.post(f"{BASE_URL}/auth/logout/", json={"refresh": "sometoken"})
        assert resp.status_code == 401
