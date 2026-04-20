import pytest
import requests

from matchmaking.models import UserConnection, UserMatch, UserProfile


BASE_URL = "http://localhost/api"


def reset_connection_state(profile_one_id, profile_two_id):
    profile_one = UserProfile.objects.get(id=profile_one_id)
    profile_two = UserProfile.objects.get(id=profile_two_id)
    low_id, high_id = sorted((profile_one.id, profile_two.id))

    UserConnection.objects.filter(profile_low_id=low_id, profile_high_id=high_id).delete()
    UserMatch.objects.filter(user=profile_one, matched_user=profile_two).delete()
    UserMatch.objects.filter(user=profile_two, matched_user=profile_one).delete()

    return profile_one, profile_two


def create_directional_match(user_profile, matched_profile):
    return UserMatch.objects.update_or_create(
        user=user_profile,
        matched_user=matched_profile,
        defaults={'score': 91.5, 'rank': 1},
    )[0]


class TestUserConnections:

    def test_request_requires_existing_match(self, profile_user_one, profile_user_two, auth_headers_one):
        profile_one, profile_two = reset_connection_state(profile_user_one["id"], profile_user_two["id"])

        resp = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )

        assert resp.status_code == 400
        assert "matched users" in resp.json()["error"]

    def test_request_and_accept_connection(self, profile_user_one, profile_user_two, auth_headers_one, auth_headers_two):
        profile_one, profile_two = reset_connection_state(profile_user_one["id"], profile_user_two["id"])
        create_directional_match(profile_one, profile_two)

        resp = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["requester"]["id"] == profile_one.id
        assert data["receiver"]["id"] == profile_two.id
        public_connection_fields = {"id", "first_name", "last_name", "place_of_birth"}
        assert set(data["requester"].keys()) == public_connection_fields
        assert set(data["receiver"].keys()) == public_connection_fields
        assert "user" not in data["other_user"]
        assert "date_of_birth" not in data["other_user"]

        duplicate = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["id"] == data["id"]

        requester_accept = requests.post(
            f"{BASE_URL}/connections/{data['id']}/accept/",
            headers=auth_headers_one,
        )
        assert requester_accept.status_code == 403

        accepted = requests.post(
            f"{BASE_URL}/connections/{data['id']}/accept/",
            headers=auth_headers_two,
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"
        assert accepted.json()["responded_at"] is not None

        accepted_list = requests.get(f"{BASE_URL}/connections/accepted/", headers=auth_headers_one)
        assert accepted_list.status_code == 200
        assert any(item["id"] == data["id"] for item in accepted_list.json())

    def test_reverse_request_returns_existing_connection(self, profile_user_one, profile_user_two, auth_headers_one, auth_headers_two):
        profile_one, profile_two = reset_connection_state(profile_user_one["id"], profile_user_two["id"])
        create_directional_match(profile_one, profile_two)
        create_directional_match(profile_two, profile_one)

        first = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )
        assert first.status_code == 201

        reverse = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_one.id},
            headers=auth_headers_two,
        )

        assert reverse.status_code == 200
        assert reverse.json()["id"] == first.json()["id"]
        low_id, high_id = sorted((profile_one.id, profile_two.id))
        assert UserConnection.objects.filter(profile_low_id=low_id, profile_high_id=high_id).count() == 1

    def test_user_matches_excludes_requested_or_connected_users(self, profile_user_one, profile_user_two, auth_headers_one, auth_headers_two):
        profile_one, profile_two = reset_connection_state(profile_user_one["id"], profile_user_two["id"])
        create_directional_match(profile_one, profile_two)

        before_request = requests.get(f"{BASE_URL}/user-matches/", headers=auth_headers_one)
        assert before_request.status_code == 200
        assert any(item["matched_user"]["id"] == profile_two.id for item in before_request.json())

        requested = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )
        assert requested.status_code == 201

        after_request = requests.get(f"{BASE_URL}/user-matches/", headers=auth_headers_one)
        assert after_request.status_code == 200
        assert all(item["matched_user"]["id"] != profile_two.id for item in after_request.json())

        accepted = requests.post(
            f"{BASE_URL}/connections/{requested.json()['id']}/accept/",
            headers=auth_headers_two,
        )
        assert accepted.status_code == 200

        after_accept = requests.get(f"{BASE_URL}/user-matches/", headers=auth_headers_one)
        assert after_accept.status_code == 200
        assert all(item["matched_user"]["id"] != profile_two.id for item in after_accept.json())

    def test_receiver_can_decline_pending_connection(self, profile_user_one, profile_user_two, auth_headers_one, auth_headers_two):
        profile_one, profile_two = reset_connection_state(profile_user_one["id"], profile_user_two["id"])
        create_directional_match(profile_one, profile_two)

        requested = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )
        assert requested.status_code == 201

        declined = requests.post(
            f"{BASE_URL}/connections/{requested.json()['id']}/decline/",
            headers=auth_headers_two,
        )
        assert declined.status_code == 200
        assert declined.json()["status"] == "declined"

    def test_requester_can_cancel_pending_connection(self, profile_user_one, profile_user_two, auth_headers_one):
        profile_one, profile_two = reset_connection_state(profile_user_one["id"], profile_user_two["id"])
        create_directional_match(profile_one, profile_two)

        requested = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )
        assert requested.status_code == 201

        cancelled = requests.post(
            f"{BASE_URL}/connections/{requested.json()['id']}/cancel/",
            headers=auth_headers_one,
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
