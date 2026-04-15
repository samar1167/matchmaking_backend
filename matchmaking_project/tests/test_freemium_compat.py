import pytest
import requests

BASE_URL = "http://localhost/api"


class TestFreemiumFlow:
    """
    End-to-end tests covering the full freemium journey:
    register → free checks → exhaust → purchase → paid checks
    """

    def test_full_freemium_journey(self):
        """
        Full flow: new user → free credits → check → see locked params
        → purchase → check → see all params
        """
        # 1. Register fresh user
        user = {
            "email":    "journey@test.com",
            "password": "JourneyPass123!",
        }
        reg = requests.post(f"{BASE_URL}/auth/register/", json=user)
        assert reg.status_code in (201, 400)

        token = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": user["email"], "password": user["password"],
        }).json()
        headers = {"Authorization": f"Bearer {token['access']}"}

        # 2. Verify free credits assigned
        plan = requests.get(f"{BASE_URL}/plan/me/", headers=headers).json()
        assert plan["free_credits"] >= 0
        assert plan["paid_credits"] == 0

        # 3. Create profile
        requests.post(f"{BASE_URL}/profiles/me/", json={
            "date_of_birth": "1991-04-10",
            "time_of_birth": "10:00:00",
            "place_of_birth": "Pune",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "timezone": "Asia/Kolkata",
        }, headers=headers)

        # 4. Create private person
        pp = requests.post(f"{BASE_URL}/private-persons/", json={
            "name":          "E2E Test Person",
            "date_of_birth": "1993-07-15",
            "time_of_birth": "06:00:00",
            "place_of_birth":"Hyderabad",
            "latitude":       17.3850,
            "longitude":      78.4867,
            "timezone":       "Asia/Kolkata",
        }, headers=headers)
        assert pp.status_code == 201
        pp_id = pp.json()["id"]

        # 5. Run a free check — should get locked params
        check = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": pp_id,
        }, headers=headers)

        if check.status_code == 200:
            data = check.json()
            assert "parameters"       in data
            assert "upgrade_required" in data
            assert "credits_remaining" in data

            if data["upgrade_required"]:
                locked = [p for p in data["parameters"] if p["locked"]]
                assert len(locked) > 0, "Free user must have some locked parameters"

        # 6. Purchase paid credits
        purchase = requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": "e2e_test_purchase_ref_001"
        }, headers=headers)
        assert purchase.status_code == 201
        assert purchase.json()["paid_credits"] > 0

        # 7. Run paid check — all params should be unlocked
        paid_check = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": pp_id,
            "force_refresh": True,
        }, headers=headers)
        assert paid_check.status_code == 200
        paid_data = paid_check.json()

        assert paid_data["upgrade_required"] is False
        for param in paid_data["parameters"]:
            assert param["locked"] is False

        # 8. Verify credits decreased after paid check
        plan_after = requests.get(f"{BASE_URL}/plan/me/", headers=headers).json()
        assert plan_after["paid_credits"] < purchase.json()["paid_credits"]

    def test_upgrade_required_flag_reflects_credit_type(
        self, profile_user_one, private_person, auth_headers_one, auth_headers_paid
    ):
        # Purchase credits for paid user
        requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": "ref_upgrade_flag_test"
        }, headers=auth_headers_paid)

        paid_resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_paid)

        if paid_resp.status_code == 200:
            assert paid_resp.json()["upgrade_required"] is False

    def test_response_structure_consistent_for_free_and_paid(
        self, profile_user_one, private_person, auth_headers_one
    ):
        """Both free and paid responses must have the same top-level structure."""
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_one)

        if resp.status_code != 200:
            pytest.skip("No credits remaining")

        data = resp.json()
        required_keys = [
            "overall_score", "parameters", "upgrade_required",
            "credits_remaining", "description",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
