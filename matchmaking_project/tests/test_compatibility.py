import pytest
import requests

BASE_URL = "http://localhost/api"


class TestCompatibility:

    def test_check_vs_private_person(self, profile_user_one, private_person, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert 0 <= data["overall_score"] <= 100
        assert data["is_private_match"] is True

    def test_check_vs_registered_user(self, profile_user_one, profile_user_two, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_user_id": profile_user_two["id"],
        }, headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert data["is_private_match"] is False

    def test_check_requires_exactly_one_target(self, profile_user_one, auth_headers_one):
        # Neither target provided
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={},
                             headers=auth_headers_one)
        assert resp.status_code == 400

        # Both targets provided
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_user_id": 1,
            "matched_private_person_id": 1,
        }, headers=auth_headers_one)
        assert resp.status_code == 400

    def test_check_unauthenticated(self, private_person):
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        })
        assert resp.status_code == 401

    def test_check_nonexistent_private_person(self, profile_user_one, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": 999999,
        }, headers=auth_headers_one)
        assert resp.status_code == 404

    def test_check_other_users_private_person(self, profile_user_two, private_person, auth_headers_two):
        """User two cannot run a check using user one's private person."""
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_two)
        assert resp.status_code == 404

    def test_force_refresh(self, profile_user_one, private_person, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
            "force_refresh": True,
        }, headers=auth_headers_one)
        assert resp.status_code == 200
        assert "overall_score" in resp.json()

    def test_history(self, profile_user_one, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/compatibility/history/", headers=auth_headers_one)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_top_matches(self, profile_user_one, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/compatibility/top_matches/?limit=5",
                            headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        # Verify ordering — scores should be descending
        scores = [item["overall_score"] for item in data]
        assert scores == sorted(scores, reverse=True)

    def test_history_unauthenticated(self):
        resp = requests.get(f"{BASE_URL}/compatibility/history/")
        assert resp.status_code == 401
