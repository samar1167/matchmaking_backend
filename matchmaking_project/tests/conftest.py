import pytest
import requests

BASE_URL = "http://localhost/api"

USER_ONE = {
    "username": "testuser_one",
    "email": "one@test.com",
    "password": "TestPass123!",
}

USER_TWO = {
    "username": "testuser_two",
    "email": "two@test.com",
    "password": "TestPass456!",
}

PRIVATE_PERSON = {
    "name": "Priya Sharma",
    "nickname": "Priya",
    "date_of_birth": "1992-08-20",
    "time_of_birth": "08:15:00",
    "place_of_birth": "Chennai",
    "latitude": 13.0827,
    "longitude": 80.2707,
    "timezone": "Asia/Kolkata",
    "notes": "Test private person",
}

PROFILE_ONE = {
    "date_of_birth": "1990-05-15",
    "time_of_birth": "14:30:00",
    "place_of_birth": "Mumbai",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata",
}


@pytest.fixture(scope="session")
def register_user_one():
    """Register user one — skip if already exists."""
    resp = requests.post(f"{BASE_URL}/auth/register/", json=USER_ONE)
    assert resp.status_code in (201, 400), f"Unexpected status: {resp.status_code} {resp.text}"
    return USER_ONE


@pytest.fixture(scope="session")
def register_user_two():
    """Register user two — skip if already exists."""
    resp = requests.post(f"{BASE_URL}/auth/register/", json=USER_TWO)
    assert resp.status_code in (201, 400), f"Unexpected status: {resp.status_code} {resp.text}"
    return USER_TWO


@pytest.fixture(scope="session")
def token_user_one(register_user_one):
    """Login as user one and return access + refresh tokens."""
    resp = requests.post(f"{BASE_URL}/auth/login/", json={
        "username": USER_ONE["username"],
        "password": USER_ONE["password"],
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert "access" in data
    assert "refresh" in data
    return data


@pytest.fixture(scope="session")
def token_user_two(register_user_two):
    """Login as user two and return access + refresh tokens."""
    resp = requests.post(f"{BASE_URL}/auth/login/", json={
        "username": USER_TWO["username"],
        "password": USER_TWO["password"],
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


@pytest.fixture(scope="session")
def auth_headers_one(token_user_one):
    return {"Authorization": f"Bearer {token_user_one['access']}"}


@pytest.fixture(scope="session")
def auth_headers_two(token_user_two):
    return {"Authorization": f"Bearer {token_user_two['access']}"}


@pytest.fixture(scope="session")
def profile_user_one(auth_headers_one):
    """Create profile for user one."""
    resp = requests.post(f"{BASE_URL}/profiles/me/", json=PROFILE_ONE, headers=auth_headers_one)
    assert resp.status_code in (200, 201), f"Profile create failed: {resp.text}"
    return resp.json()


@pytest.fixture(scope="session")
def profile_user_two(auth_headers_two):
    """Create profile for user two."""
    profile = {
        "date_of_birth": "1993-11-22",
        "time_of_birth": "09:00:00",
        "place_of_birth": "Delhi",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timezone": "Asia/Kolkata",
    }
    resp = requests.post(f"{BASE_URL}/profiles/me/", json=profile, headers=auth_headers_two)
    assert resp.status_code in (200, 201), f"Profile create failed: {resp.text}"
    return resp.json()


@pytest.fixture(scope="session")
def private_person(auth_headers_one):
    """Create a private person under user one."""
    resp = requests.post(f"{BASE_URL}/private-persons/", json=PRIVATE_PERSON, headers=auth_headers_one)
    assert resp.status_code == 201, f"Private person create failed: {resp.text}"
    return resp.json()
