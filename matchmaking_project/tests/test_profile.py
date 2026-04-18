import pytest
import requests

BASE_URL = "http://localhost/api"


class TestUserProfile:

    def test_create_profile(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/profiles/me/", json={
            "date_of_birth": "1990-05-15",
            "time_of_birth": "14:30:00",
            "place_of_birth": "Mumbai",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "timezone": "Asia/Kolkata",
        }, headers=auth_headers_one)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["date_of_birth"] == "1990-05-15"
        assert data["place_of_birth"] == "Mumbai"
        assert "user" in data

    def test_get_profile(self, profile_user_one, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/profiles/me/", headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert "date_of_birth" in data
        assert "place_of_birth" in data

    def test_update_profile_partial(self, profile_user_one, auth_headers_one):
        resp = requests.patch(f"{BASE_URL}/profiles/me/", json={
            "place_of_birth": "Delhi",
            "latitude": 28.6139,
            "longitude": 77.2090,
        }, headers=auth_headers_one)
        assert resp.status_code == 200
        assert resp.json()["place_of_birth"] == "Delhi"

    def test_get_profile_unauthenticated(self):
        resp = requests.get(f"{BASE_URL}/profiles/me/")
        assert resp.status_code == 401

    def test_create_profile_with_partial_fields(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/profiles/me/", json={
            "place_of_birth": "Mumbai",
        }, headers=auth_headers_one)
        assert resp.status_code in (200, 201)
        assert resp.json()["place_of_birth"] == "Mumbai"

    def test_profiles_isolated_between_users(self, profile_user_one, auth_headers_two, profile_user_two):
        """User two cannot see user one's profile via /me/"""
        resp = requests.get(f"{BASE_URL}/profiles/me/", headers=auth_headers_two)
        assert resp.status_code == 200
        # Should return user two's own profile, not user one's
        assert resp.json()["user"]["email"] == "two@test.com"
