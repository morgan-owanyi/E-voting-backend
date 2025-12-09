import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from accounts.models import User
import json

client = APIClient()

# Test login request
print("=== Testing Login API ===")
response = client.post('/api/auth/login/', {
    'email': 'admin@kuravote.com',
    'password': 'Admin@123456'
}, format='json')

print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.data, indent=2)}")

if response.status_code == 200:
    print("\n✓ Login successful!")
    if 'token' in response.data:
        print(f"Token: {response.data['token']}")
    if 'user' in response.data:
        print(f"User: {response.data['user']}")
else:
    print("\n✗ Login failed!")
    print(f"Error: {response.data}")
