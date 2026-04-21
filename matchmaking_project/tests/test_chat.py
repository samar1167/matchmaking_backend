import pytest
import requests

from matchmaking.models import ChatConversation, UserConnection, UserMatch, UserProfile


BASE_URL = "http://localhost/api"


def reset_chat_state(profile_one_id, profile_two_id):
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


def create_accepted_connection(profile_one, profile_two, auth_headers_one, auth_headers_two):
    create_directional_match(profile_one, profile_two)
    requested = requests.post(
        f"{BASE_URL}/connections/request/",
        json={"matched_user_profile_id": profile_two.id},
        headers=auth_headers_one,
    )
    assert requested.status_code == 201, requested.text

    accepted = requests.post(
        f"{BASE_URL}/connections/{requested.json()['id']}/accept/",
        headers=auth_headers_two,
    )
    assert accepted.status_code == 200, accepted.text
    return accepted.json()


class TestChat:
    def test_conversation_created_for_accepted_connection(self, profile_user_one, profile_user_two, auth_headers_one, auth_headers_two):
        profile_one, profile_two = reset_chat_state(profile_user_one["id"], profile_user_two["id"])
        connection = create_accepted_connection(profile_one, profile_two, auth_headers_one, auth_headers_two)

        resp = requests.post(
            f"{BASE_URL}/chat/conversations/from-connection/{connection['id']}/",
            headers=auth_headers_one,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["connection"] == connection["id"]
        assert data["unread_count"] == 0
        assert ChatConversation.objects.filter(connection_id=connection["id"]).count() == 1

    def test_text_message_updates_receiver_unread_count(self, profile_user_one, profile_user_two, auth_headers_one, auth_headers_two):
        profile_one, profile_two = reset_chat_state(profile_user_one["id"], profile_user_two["id"])
        connection = create_accepted_connection(profile_one, profile_two, auth_headers_one, auth_headers_two)
        conversation = ChatConversation.objects.get(connection_id=connection["id"])

        sent = requests.post(
            f"{BASE_URL}/chat/conversations/{conversation.id}/messages/",
            json={"body": "Hello there", "client_message_id": "chat-test-1"},
            headers=auth_headers_one,
        )
        assert sent.status_code == 201, sent.text

        conversations_for_receiver = requests.get(
            f"{BASE_URL}/chat/conversations/",
            headers=auth_headers_two,
        )
        assert conversations_for_receiver.status_code == 200
        chat = next(item for item in conversations_for_receiver.json() if item["id"] == conversation.id)
        assert chat["unread_count"] == 1

        total_unread = requests.get(f"{BASE_URL}/chat/unread-count/", headers=auth_headers_two)
        assert total_unread.status_code == 200
        assert total_unread.json()["totalUnreadCount"] >= 1

        read = requests.post(
            f"{BASE_URL}/chat/conversations/{conversation.id}/read/",
            headers=auth_headers_two,
        )
        assert read.status_code == 200
        assert read.json()["unreadCount"] == 0

    def test_rejects_chat_before_connection_is_accepted(self, profile_user_one, profile_user_two, auth_headers_one):
        profile_one, profile_two = reset_chat_state(profile_user_one["id"], profile_user_two["id"])
        create_directional_match(profile_one, profile_two)
        requested = requests.post(
            f"{BASE_URL}/connections/request/",
            json={"matched_user_profile_id": profile_two.id},
            headers=auth_headers_one,
        )
        assert requested.status_code == 201

        resp = requests.post(
            f"{BASE_URL}/chat/conversations/from-connection/{requested.json()['id']}/",
            headers=auth_headers_one,
        )
        assert resp.status_code == 400
        assert "accepted" in resp.json()["error"]
