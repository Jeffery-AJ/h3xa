#!/usr/bin/env python
"""
Simple HTTP test for login endpoint
"""
import requests
import json

def test_login_simple():
    """Test login endpoint with requests"""
    
    print("🧪 TESTING LOGIN ENDPOINT")
    print("-" * 30)
    
    # Test with POST request
    url = "http://localhost:8000/api/auth/login/"
    
    # Test data
    login_data = {
        "username": "testuser", 
        "password": "testpass123"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Making POST request to: {url}")
        print(f"Data: {json.dumps(login_data, indent=2)}")
        print(f"Headers: {headers}")
        
        response = requests.post(
            url, 
            data=json.dumps(login_data),
            headers=headers,
            timeout=10
        )
        
        print(f"\n📊 RESPONSE")
        print("-" * 12)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content: {response.text}")
        
        if response.status_code == 200:
            print("\n🎉 SUCCESS! Login is working!")
        elif response.status_code == 401:
            print("\n❌ Still getting 401 - check if user exists or server is running")
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure Django server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_login_simple()
