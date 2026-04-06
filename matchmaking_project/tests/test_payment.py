import pytest
import requests

BASE_URL = "http://localhost/api"


class TestPayment:

    def test_purchase_credits_success(self, auth_headers_one):
        before = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_one).json()

        resp = requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": "stripe_test_abc123"
        }, headers=auth_headers_one)

        assert resp.status_code == 201
        data = resp.json()
        assert "credits_purchased"  in data
        assert "paid_credits"       in data
        assert "total_credits"      in data
        assert "payment_id"         in data
        assert data["credits_purchased"] > 0

        # Verify credits increased
        after = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_one).json()
        assert after["paid_credits"] == before["paid_credits"] + data["credits_purchased"]

    def test_purchase_requires_payment_reference(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/plan/purchase/", json={},
                             headers=auth_headers_one)
        assert resp.status_code == 400

    def test_purchase_unauthenticated(self):
        resp = requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": "ref_xyz"
        })
        assert resp.status_code == 401

    def test_payment_history_returns_list(self, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/plan/payment_history/", headers=auth_headers_one)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_payment_history_has_correct_fields(self, auth_headers_one):
        # Make a purchase first
        requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": "ref_history_test"
        }, headers=auth_headers_one)

        resp = requests.get(f"{BASE_URL}/plan/payment_history/", headers=auth_headers_one)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        for record in resp.json():
            assert "id"                in record
            assert "amount_usd"        in record
            assert "credits_purchased" in record
            assert "status"            in record
            assert "payment_reference" in record
            assert "created_at"        in record

    def test_payment_history_only_shows_own_records(
        self, auth_headers_one, auth_headers_two
    ):
        """User two must not see user one's payment records."""
        # Make a purchase as user one with a unique reference
        unique_ref = "unique_ref_user_one_only_999"
        requests.post(f"{BASE_URL}/plan/purchase/", json={
            "payment_reference": unique_ref
        }, headers=auth_headers_one)

        # Check user two's history
        resp = requests.get(f"{BASE_URL}/plan/payment_history/", headers=auth_headers_two)
        refs = [r["payment_reference"] for r in resp.json()]
        assert unique_ref not in refs

    def test_payment_history_unauthenticated(self):
        resp = requests.get(f"{BASE_URL}/plan/payment_history/")
        assert resp.status_code == 401

    def test_multiple_purchases_stack_credits(self, auth_headers_paid):
        before = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_paid).json()

        requests.post(f"{BASE_URL}/plan/purchase/", json={"payment_reference": "ref_stack_1"}, headers=auth_headers_paid)
        requests.post(f"{BASE_URL}/plan/purchase/", json={"payment_reference": "ref_stack_2"}, headers=auth_headers_paid)

        after = requests.get(f"{BASE_URL}/plan/me/", headers=auth_headers_paid).json()

        credits_added = after["paid_credits"] - before["paid_credits"]
        assert credits_added == before.get("credits_per_purchase", 10) * 2