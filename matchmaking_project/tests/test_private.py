import pytest
import requests

BASE_URL = "http://localhost/api"


class TestPrivatePerson:

    def test_create_private_person(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/private-persons/", json={
            "name": "Unique Person ABC",
            "date_of_birth": "1995-03-10",
            "time_of_birth": "10:00:00",
            "place_of_birth": "Bangalore",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "timezone": "Asia/Kolkata",
        }, headers=auth_headers_one)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Unique Person ABC"
        assert "id" in data

    def test_list_private_persons(self, private_person, auth_headers_one):
        resp = requests.get(f"{BASE_URL}/private-persons/", headers=auth_headers_one)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_get_private_person(self, private_person, auth_headers_one):
        pid = private_person["id"]
        resp = requests.get(f"{BASE_URL}/private-persons/{pid}/", headers=auth_headers_one)
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_update_private_person(self, private_person, auth_headers_one):
        pid = private_person["id"]
        resp = requests.patch(f"{BASE_URL}/private-persons/{pid}/", json={
            "nickname": "Updated Nick",
            "notes": "Updated notes",
        }, headers=auth_headers_one)
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "Updated Nick"

    def test_private_person_not_visible_to_other_user(self, private_person, auth_headers_two):
        """User two must NOT be able to access user one's private persons."""
        pid = private_person["id"]
        resp = requests.get(f"{BASE_URL}/private-persons/{pid}/", headers=auth_headers_two)
        assert resp.status_code == 404  # not found — scoped to owner

    def test_list_returns_only_own_persons(self, private_person, auth_headers_two):
        """User two's list must not contain user one's private persons."""
        resp = requests.get(f"{BASE_URL}/private-persons/", headers=auth_headers_two)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert private_person["id"] not in ids

    def test_create_private_person_missing_name(self, auth_headers_one):
        resp = requests.post(f"{BASE_URL}/private-persons/", json={
            "date_of_birth": "1995-03-10",
        }, headers=auth_headers_one)
        assert resp.status_code == 400

    def test_create_private_person_unauthenticated(self):
        resp = requests.post(f"{BASE_URL}/private-persons/", json={
            "name": "Ghost",
            "date_of_birth": "1990-01-01",
        })
        assert resp.status_code == 401

    def test_delete_private_person(self, auth_headers_one):
        # Create one specifically to delete
        create = requests.post(f"{BASE_URL}/private-persons/", json={
            "name": "To Be Deleted XYZ",
            "date_of_birth": "1988-06-15",
        }, headers=auth_headers_one)
        assert create.status_code == 201
        pid = create.json()["id"]

        delete = requests.delete(f"{BASE_URL}/private-persons/{pid}/", headers=auth_headers_one)
        assert delete.status_code == 204

        # Confirm it's gone
        get = requests.get(f"{BASE_URL}/private-persons/{pid}/", headers=auth_headers_one)
        assert get.status_code == 404

    def test_other_user_cannot_delete_private_person(self, private_person, auth_headers_two):
        pid = private_person["id"]
        resp = requests.delete(f"{BASE_URL}/private-persons/{pid}/", headers=auth_headers_two)
        assert resp.status_code == 404
