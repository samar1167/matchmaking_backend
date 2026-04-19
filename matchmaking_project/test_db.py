import requests
import jwt
from datetime import datetime, timezone, timedelta
import json


# VARIABLES
EMAIL = "samar1167@gmail.com"
API_URL = 'https://dilaanupro.com'
PUBLIC_KEY = '1qqLcmNVTjjXKskeJJx8cx9O'
SECRET_KEY = 'card group whatever rate same call court particular person purpose'

user_tz_name = 'America/New_York'
user_year = 1990
user_month = 1
user_day = 1
user_tz_value = -5.0 # Time difference to UTC
user_timeUnknown = True

match_tz_name = 'America/Los_Angeles'
match_year = 1992
match_month = 2
match_day = 2
match_tz_value = -8.0 # Time difference to UTC
match_timeUnknown = False


def generate_token(secret_key, email=EMAIL):
    """Generate JWT token"""
    payload = {
        'iss': 'prodilanu.com',
        'sub': email,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=5),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')

def make_api_request(base_url, endpoint, data, public_key, secret_key):
    """Make authenticated request to API"""
    jwt_token = generate_token(secret_key)
    print(f"JWT Token: {jwt_token}")
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Public-Key': public_key,
        'Content-Type': 'application/json'
    }
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    return requests.post(url, json=data, headers=headers)

# API ENDPOINT FUNCTIONS
def get_dharma_type(base_url, public_key, secret_key, user_data, endpoint='api/dharma-types/'):
    """Get dharma type using specified endpoint"""
    return make_api_request(base_url, endpoint, user_data, public_key, secret_key)

def calculate_basic_compatibility(base_url, public_key, secret_key, user_data, matches_data, endpoint='api/basic-compatibility/'):
    """Calculate basic compatibility using specified endpoint"""
    data = {
        'user': user_data,
        'matches': matches_data
    }
    return make_api_request(base_url, endpoint, data, public_key, secret_key)

def calculate_roadvi_compatibility(base_url, public_key, secret_key, user_data, matches_data, endpoint='api/roadvi-compatibility/'):
    """Calculate Roadvi compatibility using specified endpoint"""
    data = {
        'user': user_data,
        'matches': matches_data
    }
    return make_api_request(base_url, endpoint, data, public_key, secret_key)

def calculate_detailed_compatibility(base_url, public_key, secret_key, user_data, matches_data, endpoint='api/detailed-compatibility/'):
    """Calculate detailed compatibility using specified endpoint"""
    data = {
        'user': user_data,
        'matches': matches_data
    }
    return make_api_request(base_url, endpoint, data, public_key, secret_key)

def calculate_relationship_timing(base_url, public_key, secret_key, user_data, matches_data, endpoint='api/relationship-timing/'):
    """Calculate relationship timing using specified endpoint"""
    data = {
        'user': user_data,
        'matches': matches_data
    }
    return make_api_request(base_url, endpoint, data, public_key, secret_key)

def calculate_dateore_bot_compatibility(base_url, public_key, secret_key, user_data, matches_data, compatibility_type='DATE', endpoint='api/dateore-bot-compatibility/'):
    """Calculate DateOre Bot compatibility using specified endpoint"""
    data = {
        'user': user_data,
        'matches': matches_data,
        'compatibility_type': compatibility_type
    }
    return make_api_request(base_url, endpoint, data, public_key, secret_key)

# Dictionary mapping API options to functions
API_OPTIONS = {
    1: {
        'name': 'Dharma Types',
        'function': get_dharma_type,
        'description': 'Calculates the user\'s Dharma Type based on birth data',
        'requires_match': False,
        'sample_request': {
            'id': '123',
            'bdatetime': '1990-01-01 00:00:00',
            'blat': '40.7128',
            'blon': '-74.0060',
            'tz': -5.0,
            'timeUnknown': True
        },
        'sample_response': {
            'success': True,
            'result': {
                'id': '123',
                'dharma_type': 'Devotional'
            }
        }
    },
    2: {
        'name': 'Basic Compatibility',
        'function': calculate_basic_compatibility,
        'description': 'Basic compatibility score between two people',
        'requires_match': True,
        'sample_request': {
            'user': {
                'id': '123',
                'bdatetime': '1990-01-01 00:00:00',
                'blat': '40.7128',
                'blon': '-74.0060',
                'tz': -5.0,
                'timeUnknown': True
            },
            'matches': [{
                'id': '456',
                'bdatetime': '1992-02-02 00:00:00',
                'blat': '34.0522',
                'blon': '-118.2437',
                'tz': -8.0,
                'timeUnknown': False
            }]
        },
        'sample_response': {
            'success': True,
            'result': {
                'id': '456',
                'total_relationship': 78.5,
                'dlm_ratio': 1.2
            }
        }
    },
    3: {
        'name': 'Roadvi Compatibility',
        'function': calculate_roadvi_compatibility,
        'description': 'Roadvi compatibility score between two people',
        'requires_match': True,
        'sample_request': {
            'user': {
                'id': '123',
                'bdatetime': '1990-01-01 00:00:00',
                'blat': '40.7128',
                'blon': '-74.0060',
                'tz': -5.0,
                'timeUnknown': True
            },
            'matches': [{
                'id': '456',
                'bdatetime': '1992-02-02 00:00:00',
                'blat': '34.0522',
                'blon': '-118.2437',
                'tz': -8.0,
                'timeUnknown': False
            }]
        },
        'sample_response': {
            'success': True,
            'result': {
                'id': '456',
                'total_relationship': 82.3,
                'dlm_ratio': 1.4
            }
        }
    },
    4: {
        'name': 'Detailed Compatibility',
        'function': calculate_detailed_compatibility,
        'description': 'Detailed compatibility analysis between two people',
        'requires_match': True,
        'sample_request': {
            'user': {
                'id': '123',
                'bdatetime': '1990-01-01 00:00:00',
                'blat': '40.7128',
                'blon': '-74.0060',
                'tz': -5.0,
                'timeUnknown': True
            },
            'matches': [{
                'id': '456',
                'bdatetime': '1992-02-02 00:00:00',
                'blat': '34.0522',
                'blon': '-118.2437',
                'tz': -8.0,
                'timeUnknown': False
            }]
        },
        'sample_response': {
            'success': True,
            'result': {
                'id': '456',
                'petals': {
                    'total_relationship': 75.8,
                    'physical': 82.1,
                    'emotional': 68.4,
                    'mental': 72.5,
                    'spiritual': 80.2
                },
                'dlm': {
                    'result': {
                        'Total': {
                            'Total': {
                                'DLM': 120,
                                'DLB': 100
                            }
                        }
                    }
                }
            }
        }
    },
    5: {
        'name': 'Relationship Timing',
        'function': calculate_relationship_timing,
        'description': 'Relationship timing analysis between two people',
        'requires_match': True,
        'sample_request': {
            'user': {
                'id': '123',
                'bdatetime': '1990-01-01 00:00:00',
                'blat': '40.7128',
                'blon': '-74.0060',
                'tz': -5.0,
                'timeUnknown': True
            },
            'matches': [{
                'id': '456',
                'bdatetime': '1992-02-02 00:00:00',
                'blat': '34.0522',
                'blon': '-118.2437',
                'tz': -8.0,
                'timeUnknown': False
            }]
        },
        'sample_response': {
            'success': True,
            'result': {
                'id': '456',
                'timing_score': 85,
                'current_phase': 'Growth',
                'next_phase': 'Challenge'
            }
        }
    },
    6: {
        'name': 'DateOre Bot Compatibility',
        'function': calculate_dateore_bot_compatibility,
        'description': 'DateOre Bot compatibility with relationship type',
        'requires_match': True,
        'sample_request': {
            'user': {
                'id': '123',
                'bdatetime': '1990-01-01 00:00:00',
                'blat': '40.7128',
                'blon': '-74.0060',
                'tz': -5.0,
                'timeUnknown': True
            },
            'matches': [{
                'id': '456',
                'bdatetime': '1992-02-02 00:00:00',
                'blat': '34.0522',
                'blon': '-118.2437',
                'tz': -8.0,
                'timeUnknown': False
            }],
            'compatibility_type': 'DATE'
        },
        'sample_response': {
            'success': True,
            'result': {
                'id': '456',
                'score': 78.5
            }
        }
    }
}

def display_menu():
    """Display menu of available API options"""
    print("\nAvailable API Endpoints:")
    print("------------------------")
    for key, value in API_OPTIONS.items():
        print(f"{key}. {value['name']} - {value['description']}")
    print("0. Exit")

def get_user_data():
    """Get user birth data"""
    return {
        'id': '123',
        'bdatetime': f"{user_year}-{user_month:02d}-{user_day:02d} 00:00:00",
        'blat': '40.7128',
        'blon': '-74.0060',
        'tz': user_tz_value,
        'timeUnknown': user_timeUnknown
    }

def get_match_data():
    """Get match birth data"""
    return {
        'id': '456',
        'bdatetime': f"{match_year}-{match_month:02d}-{match_day:02d} 00:00:00",
        'blat': '34.0522',
        'blon': '-118.2437',
        'tz': match_tz_value,
        'timeUnknown': match_timeUnknown
    }

def test_dharma_types_by_hour():
    """Test dharma types at different hours"""
    user_data = get_user_data()
    
    print("Dharma Types by hour:")
    for hour in range(0, 24):
        bdatetime = f"{user_year}-{user_month:02d}-{user_day:02d} {hour:02d}:00:00"
        user_data['bdatetime'] = bdatetime

        try:
            response = get_dharma_type(
                API_URL,
                PUBLIC_KEY,
                SECRET_KEY,
                user_data
            )
            if response.ok:
                dharma = response.json().get('result', {}).get('dharma_type')
                print(f"{bdatetime} -> {dharma}")
            else:
                print(f"{bdatetime} -> Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"{bdatetime} -> Exception: {e}")

def main():
    """Main function to run the API client"""
    while True:
        display_menu()
        choice = input("\nEnter your choice (0-6): ")
        
        try:
            choice = int(choice)
            if choice == 0:
                print("Exiting...")
                break
                
            if choice not in API_OPTIONS:
                print("Invalid choice. Please try again.")
                continue
                
            selected_api = API_OPTIONS[choice]
            
            if choice == 1:  # Dharma Types
                user_data = get_user_data()
                
                # Ask if user wants to test dharma types by hour
                test_by_hour = input("Test dharma types for all hours of the day? (y/n): ").lower() == 'y'
                if test_by_hour:
                    test_dharma_types_by_hour()
                    continue
                
                # Otherwise, just get the dharma type for the default time
                response = selected_api['function'](
                    API_URL,
                    PUBLIC_KEY,
                    SECRET_KEY,
                    user_data
                )
            else:  # All compatibility endpoints
                user_data = get_user_data()
                match_data = get_match_data()
                
                if choice == 6:  # DateOre Bot Compatibility
                    compatibility_types = ['DATE', 'FRIEND', 'LIFE_PARTNER', 'FRIEND_WITH_BENEFITS']
                    print("\nCompatibility Types:")
                    for i, ctype in enumerate(compatibility_types, 1):
                        print(f"{i}. {ctype}")
                    
                    type_choice = int(input("\nSelect compatibility type (1-4): "))
                    if 1 <= type_choice <= 4:
                        selected_type = compatibility_types[type_choice-1]
                        response = selected_api['function'](
                            API_URL,
                            PUBLIC_KEY,
                            SECRET_KEY,
                            user_data,
                            [match_data],
                            selected_type
                        )
                    else:
                        print("Invalid compatibility type choice.")
                        continue
                else:
                    response = selected_api['function'](
                        API_URL,
                        PUBLIC_KEY,
                        SECRET_KEY,
                        user_data,
                        [match_data]
                    )
            
            # Process and display response
            if response.ok:
                result = response.json()
                print("\nAPI Response:")
                print(json.dumps(result, indent=2))
            else:
                print(f"\nError {response.status_code}: {response.text}")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            print(f"An error occurred: {e}")

main()