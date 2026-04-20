#!/usr/bin/env python3
"""Create sample users with profiles and match preferences.

Run from the project directory:

    python scripts/create_sample_users.py --count 25

All created users use the password: pass1234
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import uuid
from datetime import date, time, timedelta
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
from django.apps import apps

if not apps.ready:
    django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from matchmaking.models import UserMatch, UserMatchPreference, UserProfile


PASSWORD = "pass1234"

FIRST_NAMES = [
    "Aarav",
    "Aisha",
    "Ananya",
    "Dev",
    "Diya",
    "Ishaan",
    "Kavya",
    "Mira",
    "Neha",
    "Rahul",
    "Riya",
    "Vivaan",
]

LAST_NAMES = [
    "Kapoor",
    "Mehta",
    "Nair",
    "Patel",
    "Rao",
    "Shah",
    "Sharma",
    "Singh",
    "Verma",
    "Iyer",
]

PLACES = [
    ("Mumbai, India", 19.0760, 72.8777, "Asia/Kolkata"),
    ("Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    ("Bengaluru, India", 12.9716, 77.5946, "Asia/Kolkata"),
    ("Chennai, India", 13.0827, 80.2707, "Asia/Kolkata"),
    ("Hyderabad, India", 17.3850, 78.4867, "Asia/Kolkata"),
    ("Pune, India", 18.5204, 73.8567, "Asia/Kolkata"),
    ("Kolkata, India", 22.5726, 88.3639, "Asia/Kolkata"),
    ("Ahmedabad, India", 23.0225, 72.5714, "Asia/Kolkata"),
]


User = get_user_model()


def choice_value(choices):
    return random.choice([value for value, _label in choices])


def random_birth_date(min_age=18, max_age=55):
    today = date.today()
    min_days = min_age * 365
    max_days = max_age * 365
    return today - timedelta(days=random.randint(min_days, max_days))


def random_birth_time():
    return time(
        hour=random.randint(0, 23),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
    )


def random_age_range():
    min_age = random.randint(18, 45)
    max_age = random.randint(min_age, min(120, min_age + random.randint(5, 25)))
    return min_age, max_age


def build_user(prefix, email_domain):
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    unique_id = uuid.uuid4().hex[:10]
    email = f"{prefix}_{unique_id}@{email_domain}".lower()

    return User(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )


def create_one_user(prefix, email_domain):
    user = build_user(prefix=prefix, email_domain=email_domain)
    user.set_password(PASSWORD)
    user.save()

    place, latitude, longitude, timezone = random.choice(PLACES)
    profile = UserProfile.objects.create(
        user=user,
        gender=choice_value(UserProfile.GENDER_CHOICES),
        date_of_birth=random_birth_date(),
        time_of_birth=random_birth_time(),
        place_of_birth=place,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        public_match=True,
    )

    preferred_age_min, preferred_age_max = random_age_range()
    preferences = UserMatchPreference.objects.create(
        user=user,
        preferred_gender=choice_value(UserMatchPreference.GENDER_CHOICES),
        preferred_age_min=preferred_age_min,
        preferred_age_max=preferred_age_max,
        preferred_relationship_intent=choice_value(
            UserMatchPreference.RELATIONSHIP_INTENT_CHOICES
        ),
        preferred_marital_status=choice_value(UserMatchPreference.MARITAL_STATUS_CHOICES),
        modern_methods=random.choice([True, False]),
        karmic_glue=random.choice([True, False]),
        ancient_methods=random.choice([True, False]),
        deal_maker=random.choice([True, False]),
        sizzle=random.choice([True, False]),
    )

    return user, profile, preferences


def create_users(count, prefix, email_domain):
    created = []
    with transaction.atomic():
        for _ in range(count):
            created.append(create_one_user(prefix=prefix, email_domain=email_domain))
    return created


def update_sample_users_last_login(prefix="sample_user", email_domain="example.com"):
    now = timezone.now()
    return User.objects.filter(
        username__startswith=f"{prefix}_",
        email__endswith=f"@{email_domain}",
    ).update(last_login=now)


def delete_all_user_matches():
    deleted_count, _deleted_by_model = UserMatch.objects.all().delete()
    return deleted_count


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc

    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")

    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="Create sample users, profiles, and match preferences."
    )
    parser.add_argument(
        "-c",
        "--count",
        type=positive_int,
        default=100,
        help="Number of users to create. Defaults to 100.",
    )
    parser.add_argument(
        "--prefix",
        default="sample_user",
        help="Email/username prefix for created users. Defaults to sample_user.",
    )
    parser.add_argument(
        "--email-domain",
        default="example.com",
        help="Email domain for created users. Defaults to example.com.",
    )
    parser.add_argument(
        "--update-last-login",
        action="store_true",
        help="Update matching sample users' last_login field to now.",
    )
    parser.add_argument(
        "--delete-user-matches",
        action="store_true",
        help="Delete all UserMatch records.",
    )
    args = parser.parse_args()

    if args.delete_user_matches:
        deleted = delete_all_user_matches()
        print(f"Deleted {deleted} UserMatch records.")
        return

    if args.update_last_login:
        updated = update_sample_users_last_login(
            prefix=args.prefix,
            email_domain=args.email_domain,
        )
        print(f"Updated last_login for {updated} sample users.")
        return

    created = create_users(
        count=args.count,
        prefix=args.prefix,
        email_domain=args.email_domain,
    )

    print(f"Created {len(created)} users with password '{PASSWORD}'.")
    for user, _profile, _preferences in created:
        print(user.email)


if __name__ == "__main__":
    main()
