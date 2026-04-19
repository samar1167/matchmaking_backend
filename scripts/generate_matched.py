# your_app/scripts/generate_matches.py

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from matchmaking_project.matchmaking.models import UserProfile, UserMatch

User = get_user_model()


# -----------------------------
# Candidate Fetching
# -----------------------------
def get_candidates(user_profile, limit=300):
    qs = UserProfile.objects.exclude(id=user_profile.id).select_related("user")

    # Hard filters
    if user_profile.preferred_gender:
        qs = qs.filter(gender=user_profile.preferred_gender)

    if user_profile.preferred_age_min and user_profile.preferred_age_max:
        qs = qs.filter(
            age__gte=user_profile.preferred_age_min,
            age__lte=user_profile.preferred_age_max,
        )

    if user_profile.preferred_relationship_intent:
        qs = qs.filter(
            relationship_intent=user_profile.preferred_relationship_intent
        )

    if user_profile.preferred_marital_status:
        qs = qs.filter(
            marital_status=user_profile.preferred_marital_status
        )

    # Activity filter using last_login
    cutoff = timezone.now() - timedelta(days=7)
    qs = qs.filter(user__last_login__gte=cutoff)

    # Randomize + limit
    return qs.order_by("?")[:limit]


# -----------------------------
# Scoring
# -----------------------------
def score(user, candidate):
    s = 0

    # Age closeness
    if user.preferred_age_min and user.preferred_age_max:
        mid = (user.preferred_age_min + user.preferred_age_max) / 2
        age_diff = abs(candidate.age - mid)
        s += max(0, 20 - age_diff)

    # Relationship intent
    if user.preferred_relationship_intent == candidate.relationship_intent:
        s += 30

    # Marital status
    if user.preferred_marital_status == candidate.marital_status:
        s += 20

    return s


def mutual_score(a, b):
    return score(a, b) + score(b, a)


# -----------------------------
# Match Generation (per user)
# -----------------------------
def generate_matches_for_user(user_profile, top_n=50):
    candidates = get_candidates(user_profile)

    scored = []
    for c in candidates:
        s = mutual_score(user_profile, c)
        scored.append((c, s))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_matches = scored[:top_n]

    with transaction.atomic():
        # Clear old matches
        UserMatch.objects.filter(user=user_profile).delete()

        # Bulk insert
        bulk = []
        for rank, (candidate, s) in enumerate(top_matches, start=1):
            bulk.append(
                UserMatch(
                    user=user_profile,
                    matched_user=candidate,
                    score=s,
                    rank=rank,
                )
            )

        UserMatch.objects.bulk_create(bulk)


# -----------------------------
# Batch Runner
# -----------------------------
def run(batch_size=200):
    print("Starting match generation...")

    qs = UserProfile.objects.select_related("user").only(
        "id",
        "age",
        "gender",
        "preferred_gender",
        "preferred_age_min",
        "preferred_age_max",
        "preferred_relationship_intent",
        "preferred_marital_status",
        "relationship_intent",
        "marital_status",
        "user__last_login",
    )

    total = qs.count()
    print(f"Total users: {total}")

    processed = 0

    for i in range(0, total, batch_size):
        batch = qs[i : i + batch_size]

        for user_profile in batch:
            try:
                generate_matches_for_user(user_profile)
                processed += 1
            except Exception as e:
                print(f"Error for user {user_profile.id}: {e}")

        print(f"Processed {processed}/{total}")

    print("Match generation complete.")