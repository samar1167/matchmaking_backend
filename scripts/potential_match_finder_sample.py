"""
Standalone Django sample for finding weighted potential matches.

This script intentionally does not use PrivatePerson records. It ranks only
registered UserProfile rows by combining:

1. Compatibility index, with the highest weight.
2. Lower-weight demographic and preference fit.

Run from the repository root:

    python3 scripts/potential_match_finder_sample.py --username alice --limit 10

Or import from Django shell:

    from scripts.potential_match_finder_sample import find_potential_matches
    matches = find_potential_matches(user, limit=10)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DJANGO_PROJECT_DIR = PROJECT_ROOT / "matchmaking_project"
_DJANGO_READY = False


def setup_django() -> None:
    global _DJANGO_READY

    if _DJANGO_READY:
        return

    if str(DJANGO_PROJECT_DIR) not in sys.path:
        sys.path.insert(0, str(DJANGO_PROJECT_DIR))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()
    _DJANGO_READY = True


def django_objects() -> Dict[str, Any]:
    setup_django()

    from django.contrib.auth.models import User
    from django.db.models import Q
    from matchmaking.astrology_service import AstrologyService
    from matchmaking.models import CompatibilityScore, UserMatchPreference, UserProfile

    return {
        "AstrologyService": AstrologyService,
        "CompatibilityScore": CompatibilityScore,
        "Q": Q,
        "User": User,
        "UserMatchPreference": UserMatchPreference,
        "UserProfile": UserProfile,
    }


@dataclass(frozen=True)
class PotentialMatchResult:
    user_profile_id: int
    user_id: int
    username: str
    final_score: float
    compatibility_score: Optional[float]
    demographic_score: float
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PotentialMatchFinder:
    """
    Finds ranked matches from registered/public user profiles only.

    Weighting strategy:
    - compatibility index: 70%
    - demographics/preference fit: 30%
    """

    COMPATIBILITY_WEIGHT = 0.70
    DEMOGRAPHIC_WEIGHT = 0.30

    DEMOGRAPHIC_COMPONENT_WEIGHTS = {
        "age": 25,
        "city": 15,
        "distance": 15,
        "gender": 10,
        "relationship_intent": 10,
        "religion_community": 7,
        "mother_tongue": 6,
        "education": 6,
        "profession": 4,
        "marital_status": 2,
        "reciprocal": 15,
    }

    def __init__(
        self,
        user: Any,
        *,
        calculate_missing_compatibility: bool = False,
        minimum_score: float = 0,
    ) -> None:
        self.user = user
        self.calculate_missing_compatibility = calculate_missing_compatibility
        self.minimum_score = minimum_score
        models = django_objects()
        self.UserMatchPreference = models["UserMatchPreference"]
        self.UserProfile = models["UserProfile"]
        self.CompatibilityScore = models["CompatibilityScore"]
        self.AstrologyService = models["AstrologyService"]
        self.Q = models["Q"]
        self.user_profile = self.UserProfile.objects.get(user=user)
        self.preferences = self.UserMatchPreference.objects.get(user=user)

    def find(self, *, limit: int = 20, queryset: Optional[Any] = None) -> List[PotentialMatchResult]:
        candidates = self._candidate_queryset(queryset)
        results = [self._score_candidate(candidate) for candidate in candidates]
        results = [result for result in results if result.final_score >= self.minimum_score]
        results.sort(key=lambda result: result.final_score, reverse=True)
        return results[:limit]

    def _candidate_queryset(self, queryset: Optional[Any]) -> Any:
        queryset = queryset or self.UserProfile.objects.all()

        # Registered users only. No PrivatePerson table is queried here.
        queryset = queryset.select_related("user", "user__match_preferences")
        queryset = queryset.exclude(user=self.user)
        queryset = queryset.filter(user__match_preferences__isnull=False)

        # Use broad database filters first, then compute the weighted score in
        # Python so partial matches can still rank instead of being discarded.
        if self.preferences.preferred_age_min or self.preferences.preferred_age_max:
            today = date.today()
            dob_filters = self.Q(date_of_birth__isnull=False)

            if self.preferences.preferred_age_min:
                latest_birth_date = self._same_month_day_years_ago(
                    today,
                    self.preferences.preferred_age_min,
                )
                dob_filters &= self.Q(date_of_birth__lte=latest_birth_date)

            if self.preferences.preferred_age_max:
                earliest_birth_date = self._same_month_day_years_ago(
                    today,
                    self.preferences.preferred_age_max + 1,
                )
                dob_filters &= self.Q(date_of_birth__gt=earliest_birth_date)

            queryset = queryset.filter(dob_filters)

        if self.preferences.preferred_city:
            queryset = queryset.filter(place_of_birth__iexact=self.preferences.preferred_city)

        return queryset

    def _score_candidate(self, candidate: Any) -> PotentialMatchResult:
        compatibility_score = self._compatibility_score(candidate)
        demographic_score, reasons = self._demographic_score(candidate)

        normalized_compatibility = self._normalize_score(compatibility_score)
        final_score = (
            normalized_compatibility * self.COMPATIBILITY_WEIGHT
            + demographic_score * self.DEMOGRAPHIC_WEIGHT
        )

        if compatibility_score is None:
            reasons.append("compatibility score unavailable")
        else:
            reasons.append(f"compatibility score {round(normalized_compatibility, 2)}/100")

        return PotentialMatchResult(
            user_profile_id=candidate.id,
            user_id=candidate.user_id,
            username=candidate.user.username,
            final_score=round(final_score, 2),
            compatibility_score=compatibility_score,
            demographic_score=round(demographic_score, 2),
            reasons=reasons,
        )

    def _compatibility_score(self, candidate: Any) -> Optional[float]:
        existing_score = (
            self.CompatibilityScore.objects.filter(user=self.user_profile, matched_user=candidate)
            .order_by("-created_at")
            .first()
        )
        if existing_score:
            return existing_score.overall_score

        reverse_score = (
            self.CompatibilityScore.objects.filter(user=candidate, matched_user=self.user_profile)
            .order_by("-created_at")
            .first()
        )
        if reverse_score:
            return reverse_score.overall_score

        if not self.calculate_missing_compatibility:
            return None

        compatibility_data = self.AstrologyService.get_compatibility(self.user_profile, candidate)
        return compatibility_data.get("compatibility_score")

    def _demographic_score(self, candidate: Any) -> Tuple[float, List[str]]:
        components: List[Tuple[str, float]] = []
        reasons: List[str] = []

        candidate_age = self._age(candidate.date_of_birth)
        age_score = self._range_score(
            candidate_age,
            self.preferences.preferred_age_min,
            self.preferences.preferred_age_max,
        )
        components.append(("age", age_score))
        if age_score == 100 and candidate_age is not None:
            reasons.append(f"age {candidate_age} fits preference")

        city_score = self._exact_text_score(
            self.preferences.preferred_city,
            candidate.place_of_birth,
            empty_preference_score=100,
        )
        components.append(("city", city_score))
        if city_score == 100 and self.preferences.preferred_city:
            reasons.append("city matches preference")

        distance_score = self._distance_score(candidate)
        components.append(("distance", distance_score))
        if distance_score == 100 and self.preferences.preferred_distance_km:
            reasons.append("within preferred distance")

        # These fields are not currently present on UserProfile in this project.
        # If you later add them, the dynamic lookup below starts scoring them.
        field_pairs = [
            ("gender", "preferred_gender", "gender"),
            ("relationship_intent", "preferred_relationship_intent", "relationship_intent"),
            ("religion_community", "preferred_religion_community", "religion_community"),
            ("mother_tongue", "preferred_mother_tongue", "mother_tongue"),
            ("education", "preferred_education", "education"),
            ("profession", "preferred_profession", "profession"),
            ("marital_status", "preferred_marital_status", "marital_status"),
        ]

        for component_name, preference_field, profile_field in field_pairs:
            preferred_value = getattr(self.preferences, preference_field, "")
            candidate_value = getattr(candidate, profile_field, "")
            score = self._exact_text_score(preferred_value, candidate_value, empty_preference_score=100)
            components.append((component_name, score))
            if preferred_value and score == 100:
                reasons.append(f"{component_name} matches preference")

        reciprocal_score = self._reciprocal_preference_score(candidate)
        if reciprocal_score is not None:
            components.append(("reciprocal", reciprocal_score))
            if reciprocal_score >= 80:
                reasons.append("candidate preferences also fit this user")

        return self._weighted_average(components, self.DEMOGRAPHIC_COMPONENT_WEIGHTS), reasons

    def _reciprocal_preference_score(self, candidate: Any) -> Optional[float]:
        try:
            candidate_preferences = candidate.user.match_preferences
        except self.UserMatchPreference.DoesNotExist:
            return None

        user_age = self._age(self.user_profile.date_of_birth)
        age_score = self._range_score(
            user_age,
            candidate_preferences.preferred_age_min,
            candidate_preferences.preferred_age_max,
        )
        city_score = self._exact_text_score(
            candidate_preferences.preferred_city,
            self.user_profile.place_of_birth,
            empty_preference_score=100,
        )
        return self._weighted_average(
            [("age", age_score), ("city", city_score)],
            {"age": 70, "city": 30},
        )

    def _distance_score(self, candidate: Any) -> float:
        if not self.preferences.preferred_distance_km:
            return 100

        if not self._has_coordinates(self.user_profile) or not self._has_coordinates(candidate):
            return 0

        distance_km = self._haversine_km(
            self.user_profile.latitude,
            self.user_profile.longitude,
            candidate.latitude,
            candidate.longitude,
        )
        return 100 if distance_km <= self.preferences.preferred_distance_km else 0

    @staticmethod
    def _weighted_average(items: Iterable[Tuple[str, float]], weights: Dict[str, int]) -> float:
        weighted_total = 0.0
        total_weight = 0

        for key, score in items:
            weight = weights.get(key, 0)
            if weight <= 0:
                continue
            weighted_total += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0

        return weighted_total / total_weight

    @staticmethod
    def _normalize_score(score: Optional[float]) -> float:
        if score is None:
            return 0

        # Existing code has used both 0-10 and 0-100 compatibility scales.
        if score <= 10:
            return max(0, min(score * 10, 100))

        return max(0, min(score, 100))

    @staticmethod
    def _range_score(value: Optional[int], minimum: Optional[int], maximum: Optional[int]) -> float:
        if minimum is None and maximum is None:
            return 100
        if value is None:
            return 0
        if minimum is not None and value < minimum:
            return 0
        if maximum is not None and value > maximum:
            return 0
        return 100

    @staticmethod
    def _exact_text_score(preferred_value: str, actual_value: Optional[str], *, empty_preference_score: float) -> float:
        preferred_value = (preferred_value or "").strip().lower()
        actual_value = (actual_value or "").strip().lower()

        if not preferred_value or preferred_value == "any":
            return empty_preference_score
        if not actual_value:
            return 0
        return 100 if preferred_value == actual_value else 0

    @staticmethod
    def _age(date_of_birth: Optional[date]) -> Optional[int]:
        if date_of_birth is None:
            return None

        today = date.today()
        return (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )

    @staticmethod
    def _same_month_day_years_ago(value: date, years: int) -> date:
        try:
            return value.replace(year=value.year - years)
        except ValueError:
            # February 29 becomes February 28 in non-leap target years.
            return value.replace(year=value.year - years, day=28)

    @staticmethod
    def _has_coordinates(profile: Any) -> bool:
        return profile.latitude is not None and profile.longitude is not None

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import asin, cos, radians, sin, sqrt

        earth_radius_km = 6371
        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)
        a = (
            sin(d_lat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
        )
        return 2 * earth_radius_km * asin(sqrt(a))


def find_potential_matches(
    user: Any,
    *,
    limit: int = 20,
    calculate_missing_compatibility: bool = False,
    minimum_score: float = 0,
) -> List[Dict[str, Any]]:
    """
    Returns JSON-serializable match results.

    Set calculate_missing_compatibility=True only if you are comfortable calling
    AstrologyService for every candidate without an existing CompatibilityScore.
    """
    finder = PotentialMatchFinder(
        user,
        calculate_missing_compatibility=calculate_missing_compatibility,
        minimum_score=minimum_score,
    )
    return [result.to_dict() for result in finder.find(limit=limit)]


def _load_user(*, username: Optional[str], user_id: Optional[int]) -> Any:
    User = django_objects()["User"]

    if username:
        return User.objects.get(username=username)
    if user_id:
        return User.objects.get(id=user_id)
    raise ValueError("Provide either --username or --user-id.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find weighted potential matches for a registered user.")
    parser.add_argument("--username", help="Username to find matches for.")
    parser.add_argument("--user-id", type=int, help="User id to find matches for.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of matches to return.")
    parser.add_argument("--minimum-score", type=float, default=0, help="Minimum final score to include.")
    parser.add_argument(
        "--calculate-missing-compatibility",
        action="store_true",
        help="Call AstrologyService for candidates that do not already have a stored CompatibilityScore.",
    )
    args = parser.parse_args()

    user = _load_user(username=args.username, user_id=args.user_id)
    matches = find_potential_matches(
        user,
        limit=args.limit,
        minimum_score=args.minimum_score,
        calculate_missing_compatibility=args.calculate_missing_compatibility,
    )
    print(json.dumps(matches, indent=2, default=str))


if __name__ == "__main__":
    main()
