#!/usr/bin/env python
"""
Test Login After Permission Fix
"""

import os
import sys
import django
import json

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

def test_login_after_fix():
    """Test login after fixing permission classes"""
    
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
    
    print("\n🧪 TESTING LOGIN WITH PERMISSION FIX")
    print("-" * 38)
    
    client = Client()
    
    # Test POST request with credentials
    response = client.post(
        '/api/auth/login/',
        data=json.dumps({
            'username': 'testuser',
            'password': 'testpass123'
        }),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.content.decode()}")
    
    if response.status_code == 200:
        print("\n🎉 SUCCESS! Login endpoint is now working!")
        try:
            data = json.loads(response.content.decode())
            print(f"✅ Message: {data.get('message')}")
            print(f"✅ User ID: {data.get('user', {}).get('id')}")
            print(f"✅ Username: {data.get('user', {}).get('username')}")
            if 'access_token' in data:
                print(f"✅ Access Token: {data['access_token'][:50]}...")
            if 'refresh_token' in data:
                print(f"✅ Refresh Token: {data['refresh_token'][:50]}...")
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
    else:
        print(f"❌ Login still failing: {response.status_code}")
        print(f"Response: {response.content.decode()}")
    
    print(f"\n📋 TESTING WITH DIFFERENT CREDENTIALS")
    print("-" * 40)
    
    # Test with wrong password
    response = client.post(
        '/api/auth/login/',
        data=json.dumps({
            'username': 'testuser',
            'password': 'wrongpassword'
        }),
        content_type='application/json'
    )
    
    print(f"Wrong password test - Status: {response.status_code}")
    if response.status_code == 401:
        print("✅ Correctly rejects wrong password")
    else:
        print("❌ Should reject wrong password with 401")
    
    # Test with email instead of username
    response = client.post(
        '/api/auth/login/',
        data=json.dumps({
            'email': 'test@example.com',
            'password': 'testpass123'
        }),
        content_type='application/json'
    )
    
    print(f"Email login test - Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Email login works")
    else:
        print(f"❌ Email login failed: {response.content.decode()}")

if __name__ == "__main__":
    test_login_after_fix()
