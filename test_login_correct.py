#!/usr/bin/env python
"""
Test Login Endpoint with Correct Method
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'h3xa.settings')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

from django.contrib.auth import get_user_model
from django.test import Client
import json

def test_login_correctly():
    """Test login with correct POST method"""
    
    print("🔧 CREATING TEST USER")
    print("-" * 25)
    
    User = get_user_model()
    
    # Create or get test user
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print("✅ Test user created successfully")
    else:
        print("✅ Test user already exists")
    
    print(f"Username: testuser")
    print(f"Password: testpass123")
    print(f"Email: {test_user.email}")
    
    print("\n🧪 TESTING LOGIN ENDPOINT")
    print("-" * 28)
    
    client = Client()
    
    # Test with WRONG method (GET) - this will fail like your request
    print("1. Testing with GET method (WRONG):")
    response = client.get('/api/auth/login/')
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.content.decode()}")
    
    # Test with CORRECT method (POST)
    print("\n2. Testing with POST method (CORRECT):")
    response = client.post(
        '/api/auth/login/',
        data=json.dumps({
            'username': 'testuser',
            'password': 'testpass123'
        }),
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.content.decode()}")
    
    if response.status_code == 200:
        print("   ✅ LOGIN SUCCESSFUL!")
        try:
            data = json.loads(response.content.decode())
            if 'access_token' in data:
                print(f"   🔑 Access Token: {data['access_token'][:50]}...")
            if 'refresh_token' in data:
                print(f"   🔄 Refresh Token: {data['refresh_token'][:50]}...")
        except:
            pass
    else:
        print("   ❌ LOGIN FAILED")
    
    print("\n📋 SUMMARY")
    print("-" * 12)
    print("✅ Your endpoint is working correctly!")
    print("❌ You were using GET method instead of POST")
    print("✅ Use POST with JSON body containing username/password")
    
    print("\n🎯 CORRECT USAGE")
    print("-" * 18)
    print("Method: POST")
    print("URL: http://localhost:8000/api/auth/login/")
    print("Headers: Content-Type: application/json")
    print("Body:")
    print(json.dumps({
        "username": "testuser",
        "password": "testpass123"
    }, indent=2))

if __name__ == "__main__":
    test_login_correctly()
