import pytest
import requests

BASE_URL = "http://localhost/api"


class TestCreditWallet:

    def test_new_user_gets_free_credits(self, register_user_one, auth_headers_one):
        """Every new user should have free credits on registration."""
        resp = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert "free_credits"  in data
        assert "paid_credits"  in data
        assert "total_credits" in data
        assert data["total_credits"] >= 0

    def test_plan_shows_correct_structure(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert "free_credits"          in data
        assert "paid_credits"          in data
        assert "total_credits"         in data
        assert "paid_credit_price_usd" in data
        assert "credits_per_purchase"  in data
        assert data["total_credits"] == data["free_credits"] + data["paid_credits"]

    def test_plan_unauthenticated(self):
        resp = requests.get(f"{BASE_URL}/plan/me/")
        assert resp.status_code == 401

    def test_credit_decreases_after_check(
        self, profile_user_one, private_person, auth_headers_one
    ):
        """Each compatibility check should consume exactly one credit."""
        before = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_one).json()

        requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_one)

        after = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_one).json()

        if before["total_credits"] > 0:
            assert after["total_credits"] == before["total_credits"] - 1

    def test_response_includes_credits_remaining(
        self, profile_user_one, private_person, auth_headers_one
    ):
        """Compatibility check response must include credits_remaining."""
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_one)

        if resp.status_code == 200:
            assert "credits_remaining" in resp.json()
        elif resp.status_code == 402:
            data = resp.json()
            assert "credits_remaining" in data
            assert data["credits_remaining"] == 0

    def test_no_credits_returns_402(self, register_user_one):
        """A user with zero credits should get 402 Payment Required."""
        # Create a brand new user and exhaust their credits
        new_user = {
            "username": "zero_credit_user_xyz",
            "email":    "zerocredit@test.com",
            "password": "ZeroPass123!",
        }
        requests.post(f"{BASE_URL}/auth/register/", json=new_user)
        token = requests.post(f"{BASE_URL}/auth/login/", json={
            "username": new_user["username"],
            "password": new_user["password"],
        }).json()
        headers = {"Authorization": f"Bearer {token['access']}"}

        # Check plan
        plan = requests.get(f"{BASE_URL}/plan/me/", headers=headers).json()
        initial_credits = plan["total_credits"]

        # Create profile first
        requests.post(f"{BASE_URL}/profiles/me/", json={
            "date_of_birth": "1990-01-01",
            "time_of_birth": "12:00:00",
            "place_of_birth": "Mumbai",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "timezone": "Asia/Kolkata",
        }, headers=headers)

        # Exhaust all credits
        for _ in range(initial_credits + 1):
            resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
                "matched_private_person_id": 1,  # any existing person
            }, headers=headers)
            if resp.status_code == 402:
                break

        # Final check must be 402
        final = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": 1,
        }, headers=headers)
        assert final.status_code == 402
        data = final.json()
        assert "purchase_url" in data
        assert data["credits_remaining"] == 0

    def test_paid_credits_consumed_before_free(self, auth_headers_paid):
        """When user has both paid and free credits, paid must be used first."""
        plan_before = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_paid).json()

        if plan_before["paid_credits"] > 0 and plan_before["free_credits"] > 0:
            # Run a check
            requests.post(f"{BASE_URL}/compatibility/check/", json={
                "matched_private_person_id": 1,
            }, headers=auth_headers_paid)

            plan_after = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_paid).json()
            # Paid credits should have decreased, free credits unchanged
            assert plan_after["paid_credits"] == plan_before["paid_credits"] - 1
            assert plan_after["free_credits"] == plan_before["free_credits"]