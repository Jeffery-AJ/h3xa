#!/usr/bin/env python
"""
Test Django Authentication Endpoints
"""

import os
import sys
import django
import requests
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

def test_authentication_issue():
    """Test the authentication endpoint issue"""
    
    print("\n🔍 DIAGNOSING AUTHENTICATION ISSUE")
    print("=" * 50)
    
    # Check if the custom_login function has any permission requirements
    from authentication.views import custom_login
    print(f"✅ custom_login function imported successfully")
    
    # Check the function attributes
    if hasattr(custom_login, 'authentication_classes'):
        print(f"🔍 Authentication classes: {custom_login.authentication_classes}")
    else:
        print("✅ No authentication_classes attribute (good for login)")
    
    if hasattr(custom_login, 'permission_classes'):
        print(f"🔍 Permission classes: {custom_login.permission_classes}")
    else:
        print("✅ No permission_classes attribute (good for login)")
    
    # Check decorators
    print(f"🔍 Function decorators: {getattr(custom_login, '__wrapped__', 'None')}")
    
    # Check if @api_view decorator is properly applied
    print(f"🔍 Has csrf_exempt: {hasattr(custom_login, 'csrf_exempt')}")
    
    # Test the URL pattern
    from django.urls import reverse
    try:
        url = reverse('rest_login')
        print(f"✅ URL pattern resolved: {url}")
    except Exception as e:
        print(f"❌ URL pattern error: {e}")
    
    # Check Django settings for authentication
    from django.conf import settings
    
    print(f"\n🔧 DJANGO SETTINGS CHECK")
    print("-" * 30)
    print(f"DEBUG mode: {settings.DEBUG}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    if hasattr(settings, 'REST_FRAMEWORK'):
        print(f"REST_FRAMEWORK: {settings.REST_FRAMEWORK}")
    
    if hasattr(settings, 'SIMPLE_JWT'):
        print(f"SIMPLE_JWT configured: ✅")
    
    # Check if there are any middleware issues
    print(f"\nMiddleware: {settings.MIDDLEWARE}")
    
    print(f"\n🎯 COMMON ISSUES & SOLUTIONS")
    print("-" * 35)
    print("1. Make sure Django server is running on http://localhost:8000")
    print("2. Check if you're sending POST request (not GET)")
    print("3. Include Content-Type: application/json header")
    print("4. Send username/email and password in request body")
    print("5. Remove any Authorization header from login request")
    
    print(f"\n📝 CORRECT LOGIN REQUEST")
    print("-" * 28)
    print("POST http://localhost:8000/api/auth/login/")
    print("Content-Type: application/json")
    print("(No Authorization header)")
    print()
    print(json.dumps({
        "username": "your_username",
        "password": "your_password"
    }, indent=2))
    
    print(f"\n🚨 POSSIBLE CAUSES OF YOUR ERROR")
    print("-" * 38)
    print("1. Django server not running")
    print("2. Wrong HTTP method (using GET instead of POST)")
    print("3. Missing Content-Type header")
    print("4. Including Authorization header on login endpoint")
    print("5. Middleware blocking the request")
    print("6. CORS issues if calling from browser")
    
    # Test the view directly
    print(f"\n🧪 TESTING VIEW DIRECTLY")
    print("-" * 27)
    
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    
    # Create a test user
    User = get_user_model()
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com'
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print("✅ Test user created")
    else:
        print("✅ Test user exists")
    
    # Test the view
    factory = RequestFactory()
    request = factory.post('/api/auth/login/', {
        'username': 'testuser',
        'password': 'testpass123'
    }, content_type='application/json')
    
    try:
        response = custom_login(request)
        print(f"✅ Direct view test: Status {response.status_code}")
        if response.status_code == 200:
            print("✅ Login function works correctly!")
        else:
            print(f"❌ Login failed: {response.content}")
    except Exception as e:
        print(f"❌ Direct view test failed: {e}")

if __name__ == "__main__":
    test_authentication_issue()
