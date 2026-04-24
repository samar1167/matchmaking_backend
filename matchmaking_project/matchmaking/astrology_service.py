import logging
import profile
import random
import requests
import jwt
from datetime import datetime, timezone, timedelta, time
import json
import zoneinfo

from django.conf import settings

logger = logging.getLogger(__name__)


class AstrologyService:
    EMAIL = getattr(settings, 'DILAANU_EMAIL', '')
    BASE_URL  = getattr(settings, 'DILAANU_BASE_URL', '')
    PUBLIC_KEY = getattr(settings, 'DILAANU_PUBLIC_KEY', '')
    SECRET_KEY  = getattr(settings, 'DILAANU_SECRET_KEY', '')

    TIMEOUT = 15

    @classmethod
    def get_compatibility(cls, user_profile, target):
        birth1 = cls._birth_data(user_profile)
        birth2 = cls._birth_data(target)

        response_data = cls._call_api(birth1, birth2)
        return cls._get_detailed_compatibility_data(response_data, birth2['id'])

    @classmethod
    def _generate_token(cls):
        now = datetime.now(timezone.utc)
        payload = {
            'iss': cls.BASE_URL,
            'sub': cls.EMAIL,
            'exp': now + timedelta(minutes=5),
            'iat': now
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm='HS256')

    @classmethod
    def _generate_tz_offset(cls, timezone):
        tz = zoneinfo.ZoneInfo(timezone)
        offset = tz.utcoffset(datetime.now(tz))
        hours = int(offset.total_seconds() / 3600)
        return hours + (0.5 if offset.total_seconds() % 3600 else 0)
    
    @classmethod
    def _get_utc_offset(cls, timezone_name: str, dt: datetime = None):
        if dt is None:
            dt = datetime.now(timezone.utc)

        local_dt = dt.astimezone(zoneinfo.ZoneInfo(timezone_name))
        offset_timedelta = local_dt.utcoffset()
        offset_seconds = offset_timedelta.total_seconds()
        return offset_seconds / 3600

    @classmethod
    def _is_valid_time(cls, t):
        if t is None:
            return False
        return not (t.hour == 0 and t.minute == 0 and t.second == 0)
    
    @classmethod
    def _combine_date_time(cls, d, t):
        if t is None or (t.hour == 0 and t.minute == 0 and t.second == 0):
            return datetime.combine(d, time(12, 0, 0)) #default to mid day
        return datetime.combine(d, t)

    @classmethod
    def _birth_data(cls, profile):
        return {
            'id': 'match'+str(random.randint(1000,9999)),
            'bdatetime': cls._combine_date_time(profile.date_of_birth, profile.time_of_birth).strftime('%Y-%m-%d %H:%M:%S'),
            'blat': profile.latitude or 0, 
            'blon': profile.longitude or 0,
            'tz': cls._get_utc_offset(profile.place_of_birth) if profile.place_of_birth else 0,
            'timeUnknown': (not cls._is_valid_time(profile.time_of_birth)) #TODO change it to long lat based time unknown
        }

    @classmethod
    def make_request(cls, endpoint: str, data):
        """Make authenticated API request with error handling"""
        try:
            token = cls._generate_token()
            headers = {
                'Authorization': f'Bearer {token}',
                'Public-Key': cls.PUBLIC_KEY,
                'Content-Type': 'application/json'
            }
            url = f"{cls.BASE_URL}/api/{endpoint}"
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.ok:
                return response
            else:
                # Log error details
                try:
                    error_json = response.json()
                    logger.error(f"API error {response.status_code}: {error_json}")
                except:
                    logger.error(f"API error {response.status_code}: {response.text}")
                return response
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for endpoint {endpoint}")
            raise Exception("API request timeout")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for endpoint {endpoint}")
            raise Exception("API connection failed")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for endpoint {endpoint}: {e}")
            raise Exception(f"API request failed: {str(e)}")
        
    @classmethod
    def _get_detailed_compatibility_data(cls, data, target_match_id):
        # Extract user_matches from response
        if data is None:
            logger.warning("No user_matches found in response")
            return None
            
        user_matches = data.get('result', {}).get('user_matches', [])
        
        if not user_matches:
            logger.warning("No user_matches found in response")
            return None
        
        # Find the match with target ID
        for match in user_matches:
            if match.get('id') == target_match_id:
                petals = match.get('result', {}).get('petals', {})
                
                if petals:
                    return {
                        'overall_score': petals.get('total_relationship'),
                        'durability': petals.get('durability'),
                        'compatibility': petals.get('compatibility'),
                        'sizzle': petals.get('sex_total'),
                        'destiny': petals.get('karmic_glue'),
                        'waity': petals.get('waity'),
                        'chemistry': petals.get('chemistry'),
                        'description': "Some fields are Not Available because of missing Time of Birth data" if not petals.get('chemistry') else '',
                        'api_response': petals,
                    }
                else:
                    logger.warning(f"No petals data found for match {target_match_id}")
                    return None
    
    @classmethod
    def _call_api(cls, birth1, birth2):
        """Test basic compatibility endpoint"""
        try:
            data = {'user': birth1, 'matches': [birth2]}
            response = cls.make_request('detailed-compatibility/', data)

            if response and response.ok:
                return response.json()
            else:
                logger.error(f"API call failed with status: {response.status_code if response else 'No response'}")
                return None
                
        except Exception as e:
            logger.error(f"Error in Dilaanu API Call: {e}")

    # @classmethod
    # def _call_api(cls, birth1, birth2):
    #     """
    #     -------------------------------------------------------
    #     MOCK IMPLEMENTATION — replace with real API call later
    #     Returns random compatibility scores between 1 and 10.
    #     -------------------------------------------------------
    #     """
    #     logger.info("Using mock astrology API — returning random scores")

    #     def rand():
    #         return round(random.uniform(1, 10), 1)

    #     overall = round(
    #         (rand() + rand() + rand() + rand()) / 4, 1
    #     )

    #     return {
    #         "overall_score":     overall,
    #         "compatibility":       rand(),
    #         "durability":      rand(),
    #         "chemistry":     rand(),
    #         "sizzle":      rand(),
    #         "destiny":   rand(),
    #         "friendship":    rand(),
    #         "waity":   rand(),
    #         "description": (
    #             f"This is a mock compatibility result. "
    #             f"Overall score: {overall}/10. "
    #             f"Replace AstrologyService._call_api() with your real API when ready."
    #         ),
    #     }


    # @classmethod
    # def _validate_response(cls, data):
    #     if not isinstance(data, dict):
    #         raise Exception("Invalid API response format")

    #     if 'overall_score' not in data:
    #         raise Exception("Incomplete API response")


    # @classmethod
    # def _parse(cls, r):
    #     return {
    #         'overall_score':     r.get('overall_score', 0),
    #         'compatibility':       r.get('compatibility'),
    #         'durability':      r.get('durability'),
    #         'chemistry':     r.get('chemistry'),
    #         'sizzle':      r.get('sizzle'),
    #         'destiny':   r.get('destiny'),
    #         'friendship':    r.get('friendship'),
    #         'waity':   r.get('waity'),
    #         'description':             r.get('description', ''),
    #         'api_response':            r,
    #     }