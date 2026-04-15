import logging
import random

from django.conf import settings

logger = logging.getLogger(__name__)


class AstrologyService:
    BASE_URL = getattr(settings, 'ASTROLOGY_API_URL', '')
    API_KEY  = getattr(settings, 'ASTROLOGY_API_KEY', '')

    TIMEOUT = 15

    @classmethod
    def get_compatibility(cls, user_profile, target):
        birth1 = cls._birth_data(user_profile)
        birth2 = cls._birth_data(target)

        raw_response = cls._call_api(birth1, birth2)
        cls._validate_response(raw_response)
        return cls._parse(raw_response)
    

    @classmethod
    def _birth_data(cls, profile):
        return {
            'date':      profile.date_of_birth.isoformat(),
            'time':      profile.time_of_birth.isoformat() if profile.time_of_birth else '00:00:00',
            'latitude':  profile.latitude or 0,
            'longitude': profile.longitude or 0,
            'timezone':  profile.timezone,
            'place':     profile.place_of_birth,
        }


    # @classmethod
    # def _call_api(cls, birth1, birth2):
    #     try:
    #         resp = requests.post(
    #             f'{cls.BASE_URL}/compatibility',
    #             json={'person1': birth1, 'person2': birth2},
    #             headers={
    #                 'Authorization': f'Bearer {cls.API_KEY}',
    #                 'Content-Type': 'application/json'
    #             },
    #             timeout=cls.TIMEOUT,
    #         )

    #         resp.raise_for_status()
    #         return resp.json()

    #     except requests.exceptions.Timeout:
    #         logger.error("Astrology API timeout")
    #         raise Exception("Astrology service timeout")

    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"Astrology API error: {e}")
    #         raise Exception("Astrology service unavailable")

    @classmethod
    def _call_api(cls, birth1, birth2):
        """
        -------------------------------------------------------
        MOCK IMPLEMENTATION — replace with real API call later
        Returns random compatibility scores between 1 and 10.
        -------------------------------------------------------
        """
        logger.info("Using mock astrology API — returning random scores")

        def rand():
            return round(random.uniform(1, 10), 1)

        overall = round(
            (rand() + rand() + rand() + rand()) / 4, 1
        )

        return {
            "compatibility_score":     overall,
            "sun_compatibility":       rand(),
            "moon_compatibility":      rand(),
            "venus_compatibility":     rand(),
            "mars_compatibility":      rand(),
            "jupiter_compatibility":   rand(),
            "saturn_compatibility":    rand(),
            "mercury_compatibility":   rand(),
            "rahu_compatibility":      rand(),
            "ketu_compatibility":      rand(),
            "ascendant_compatibility": rand(),
            "description": (
                f"This is a mock compatibility result. "
                f"Overall score: {overall}/10. "
                f"Replace AstrologyService._call_api() with your real API when ready."
            ),
        }


    @classmethod
    def _validate_response(cls, data):
        if not isinstance(data, dict):
            raise Exception("Invalid API response format")

        if 'compatibility_score' not in data:
            raise Exception("Incomplete API response")


    @classmethod
    def _parse(cls, r):
        return {
            'compatibility_score':     r.get('compatibility_score', 0),
            'sun_compatibility':       r.get('sun_compatibility'),
            'moon_compatibility':      r.get('moon_compatibility'),
            'venus_compatibility':     r.get('venus_compatibility'),
            'mars_compatibility':      r.get('mars_compatibility'),
            'jupiter_compatibility':   r.get('jupiter_compatibility'),
            'saturn_compatibility':    r.get('saturn_compatibility'),
            'mercury_compatibility':   r.get('mercury_compatibility'),
            'rahu_compatibility':      r.get('rahu_compatibility'),
            'ketu_compatibility':      r.get('ketu_compatibility'),
            'ascendant_compatibility': r.get('ascendant_compatibility'),
            'description':             r.get('description', ''),
            'api_response':            r,
        }