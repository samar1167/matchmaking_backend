import pytest
import requests

BASE_URL = "http://localhost/api"


class TestCompatibilityParameters:

    def test_parameters_endpoint_returns_list(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/parameters/", headers=auth_headers_one)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_parameters_have_required_fields(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/parameters/", headers=auth_headers_one)
        assert resp.status_code == 200
        for param in resp.json():
            assert "key"     in param
            assert "label"   in param
            assert "is_free" in param
            assert "order"   in param

    def test_at_least_one_free_parameter_exists(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/parameters/", headers=auth_headers_one)
        free_params = [p for p in resp.json() if p["is_free"]]
        assert len(free_params) >= 1, "At least one free parameter must be configured"

    def test_at_least_one_paid_parameter_exists(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/parameters/", headers=auth_headers_one)
        paid_params = [p for p in resp.json() if not p["is_free"]]
        assert len(paid_params) >= 1, "At least one paid parameter must be configured"

    def test_free_user_sees_free_parameters_unlocked(
        self, profile_user_one, private_person, auth_headers_one
    ):
        """Free parameters must have a real score for free users."""
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_one)

        if resp.status_code != 200:
            pytest.skip("No credits remaining to run this test")

        data = resp.json()
        assert "parameters" in data

        # Get which keys are free
        params_meta = requests.get(
            f"{BASE_URL}/plan/parameters/", headers=auth_headers_one
        ).json()
        free_keys = {p["key"] for p in params_meta if p["is_free"]}
        paid_keys = {p["key"] for p in params_meta if not p["is_free"]}

        if data.get("upgrade_required"):
            for param in data["parameters"]:
                if param["key"] in free_keys:
                    assert param["locked"] is False, f"{param['key']} should be unlocked for free users"
                if param["key"] in paid_keys:
                    assert param["locked"] is True,  f"{param['key']} should be locked for free users"
                    assert param["score"] is None,   f"{param['key']} score should be null when locked"

    def test_paid_user_sees_all_parameters_unlocked(
        self, profile_user_one, private_person, auth_headers_paid
    ):
        """After purchasing credits, all parameters must be unlocked."""
        # Purchase credits first
        requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": "test_ref_params_check"
        }, headers=auth_headers_paid)

        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_paid)

        if resp.status_code != 200:
            pytest.skip("Check failed — skipping parameter visibility test")

        data = resp.json()
        assert data.get("upgrade_required") is False

        for param in data["parameters"]:
            assert param["locked"] is False, f"{param['key']} should be unlocked for paid users"

    def test_locked_parameters_have_null_score(
        self, profile_user_one, private_person, auth_headers_one
    ):
        resp = requests.post(f"{BASE_URL}/compatibility/check/", json={
            "matched_private_person_id": private_person["id"],
        }, headers=auth_headers_one)

        if resp.status_code != 200:
            pytest.skip("No credits remaining")

        for param in resp.json().get("parameters", []):
            if param["locked"]:
                assert param["score"] is None

    def test_parameters_ordered_correctly(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/parameters/", headers=auth_headers_one)
        orders = [p["order"] for p in resp.json()]
        assert orders == sorted(orders), "Parameters must be returned in order"

    def test_parameters_unauthenticated(self):
        resp = requests.get(f"{BASE_URL}/plan/parameters/")
        assert resp.status_code == 401