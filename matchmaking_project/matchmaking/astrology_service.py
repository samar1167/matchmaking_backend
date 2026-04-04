import requests, logging
from django.conf import settings
from django.core.cache import cache
logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 86400 * 30

class AstrologyService:
    BASE_URL = getattr(settings, 'ASTROLOGY_API_URL', '')
    API_KEY  = getattr(settings, 'ASTROLOGY_API_KEY', '')

    @classmethod
    def get_compatibility(cls, user_profile, target, force_refresh=False):
        cache_key = cls._cache_key(user_profile, target)
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                return cached
        result = cls._parse(cls._call_api(cls._birth_data(user_profile), cls._birth_data(target)))
        cache.set(cache_key, result, CACHE_TIMEOUT)
        return result

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

    @classmethod
    def _call_api(cls, birth1, birth2):
        try:
            resp = requests.post(
                f'{cls.BASE_URL}/compatibility',
                json={'person1': birth1, 'person2': birth2},
                headers={'Authorization': f'Bearer {cls.API_KEY}', 'Content-Type': 'application/json'},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Astrology API call failed: {e}")

    @classmethod
    def _parse(cls, r):
        return {
            'overall_score':       r.get('compatibility_score', 0),
            'sun_compatibility':   r.get('sun_compatibility'),
            'moon_compatibility':  r.get('moon_compatibility'),
            'venus_compatibility': r.get('venus_compatibility'),
            'mars_compatibility':  r.get('mars_compatibility'),
            'description':         r.get('description', ''),
            'api_response':        r,
        }

    @classmethod
    def _cache_key(cls, user_profile, target):
        from matchmaking.models import PrivatePerson
        if isinstance(target, PrivatePerson):
            return f'compat:user_{user_profile.id}:private_{target.id}'
        return f'compat:user_{min(user_profile.id, target.id)}:user_{max(user_profile.id, target.id)}'
