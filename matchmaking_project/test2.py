import requests
import jwt
from datetime import datetime, timezone, timedelta
import json

# Configuration
EMAIL = "samar1167@gmail.com"
BASE_URL = 'https://dilaanupro.com'
PUBLIC_KEY = '1qqLcmNVTjjXKskeJJx8cx9O'
SECRET_KEY = 'card group whatever rate same call court particular person purpose'

# Sample data
# SAMPLE_USER = {
#     'id': 'user123',
#     'bdatetime': '1990-01-01 12:00:00',  # New Year's Day, noon
#     'blat': 40.7128,   # New York City latitude
#     'blon': -74.0060,  # New York City longitude  
#     'tz': -5.0,        # EST timezone (UTC-5)
#     'timeUnknown': True
# }

# SAMPLE_MATCH = {
#     'id': 'match456',
#     'bdatetime': '1992-02-02 15:30:00',  # Feb 2nd, 3:30 PM
#     'blat': 34.0522,   # Los Angeles latitude
#     'blon': -118.2437, # Los Angeles longitude
#     'tz': -8.0,        # PST timezone (UTC-8)
#     'timeUnknown': False
# }

SAMPLE_USER = {
    'id': 'user123',
    'bdatetime': '1983-12-20 09:12:00',  # New Year's Day, noon
    'blat': 28.6139,   # New Delhi latitude
    'blon': 77.2090,  # New delhi longitude  
    'tz': +5.30,        # EST timezone (UTC-5)
    'timeUnknown': False
}

SAMPLE_MATCH = {
    'id': 'match456',
    'bdatetime': '1971-07-28 13:45:01',  # Feb 2nd, 3:30 PM
    'blat': +24.7914,   # Gaya latitude
    'blon': +85.0002, # Gaya longitude
    'tz': +5.30,        # PST timezone (UTC-8)
    'timeUnknown': False
}


def generate_token():
    """Generate JWT token"""
    now = datetime.now(timezone.utc)
    payload = {
        'iss': BASE_URL,
        'sub': EMAIL,
        'exp': now + timedelta(minutes=5),
        'iat': now
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def make_request(endpoint, data):
    """Make authenticated API request"""
    token = generate_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Public-Key': PUBLIC_KEY,
        'Content-Type': 'application/json'
    }
    url = f"{BASE_URL}/api/{endpoint}"
    
    print(f"\n=== {endpoint.upper()} ===")
    
    response = requests.post(url, json=data, headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print("Response:", json.dumps(result, indent=2))
        return response
    else:
        print("Error:", response.text)
        try:
            error_json = response.json()
            print("Error JSON:", json.dumps(error_json, indent=2))
        except:
            pass
    return response

# Individual test functions for each endpoint
def test_dharma_types():
    """Test dharma types endpoint"""
    return make_request('dharma-types/', SAMPLE_USER)

def test_basic_compatibility():
    """Test basic compatibility endpoint"""
    data = {'user': SAMPLE_USER, 'matches': [SAMPLE_MATCH]}
    return make_request('basic-compatibility/', data)

def test_roadvi_compatibility():
    """Test roadvi compatibility endpoint"""
    data = {'user': SAMPLE_USER, 'matches': [SAMPLE_MATCH]}
    return make_request('roadvi-compatibility/', data)

def test_detailed_compatibility():
    """Test detailed compatibility endpoint"""
    data = {'user': SAMPLE_USER, 'matches': [SAMPLE_MATCH]}
    return make_request('detailed-compatibility/', data)

def test_timing_compatibility():
    """Test timing compatibility endpoint"""
    data = {'user': SAMPLE_USER, 'matches': [SAMPLE_MATCH]}
    return make_request('timing-compatibility/', data)

def test_dateore_bot_compatibility():
    """Test DateOre bot compatibility endpoint"""
    data = {
        'user': SAMPLE_USER, 
        'matches': [SAMPLE_MATCH],
        'compatibility_type': 'DATE'
    }
    return make_request('dateore-bot-compatibility/', data)

def test_all_endpoints():
    """Test all API endpoints"""
    print("🚀 Testing all API endpoints...\n")
    
    # Test each endpoint
    # test_dharma_types()
    # test_basic_compatibility()
    # test_roadvi_compatibility()
    test_detailed_compatibility()
    # test_timing_compatibility()
    # test_dateore_bot_compatibility()
    
    print("\n✅ All tests completed!")

def test_dateore_all_types():
    """Test DateOre bot with all compatibility types"""
    print("🚀 Testing DateOre Bot with all compatibility types...\n")
    
    compatibility_types = ['DATE', 'FRIEND', 'LIFE_PARTNER', 'FRIEND_WITH_BENEFITS']
    
    for comp_type in compatibility_types:
        data = {
            'user': SAMPLE_USER, 
            'matches': [SAMPLE_MATCH],
            'compatibility_type': comp_type
        }
        make_request('dateore-bot-compatibility/', data)
    
    print("\n✅ DateOre compatibility type tests completed!")

# if _name_ == "_main_":
print("🧪 Simple API Test Client")
print("=" * 50)
    
    # You can run individual tests by calling the functions:
    # test_dharma_types()
    # test_basic_compatibility()
    # test_roadvi_compatibility()
    # test_detailed_compatibility()
    # test_timing_compatibility()
    # test_dateore_bot_compatibility()
    # test_dateore_all_types()
    
    # Or test everything at once:
test_all_endpoints()
    
    # Test just one endpoint for debugging
    # test_dharma_types()