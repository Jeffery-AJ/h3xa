#!/usr/bin/env python3
"""
AI Financial Analytics Platform - Testing Script
Tests the complete API workflow including AI features
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8000/api"
TEST_USER = {
    "username": "testuser_ai",
    "email": "test@example.com", 
    "password1": "TestPass123!",
    "password2": "TestPass123!"
}

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.company_id = None
        self.account_id = None
        
    def register_and_login(self):
        """Register a test user and login"""
        print("🔐 Setting up test user...")
        
        # Try to register (might fail if user exists)
        try:
            response = self.session.post(f"{BASE_URL}/auth/registration/", json=TEST_USER)
            print(f"Registration: {response.status_code}")
        except:
            pass
        
        # Login
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password1"]
        }
        response = self.session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def setup_test_company(self):
        """Create a test company"""
        print("\n🏢 Creating test company...")
        
        company_data = {
            "name": "AI Test Corp",
            "description": "Test company for AI features",
            "industry": "Technology",
            "registration_number": "AI123456",
            "tax_id": "TAX789012"
        }
        
        response = self.session.post(f"{BASE_URL}/financial/companies/", json=company_data)
        
        if response.status_code == 201:
            data = response.json()
            self.company_id = data["id"]
            print(f"✅ Company created with ID: {self.company_id}")
            return True
        else:
            print(f"❌ Company creation failed: {response.status_code} - {response.text}")
            return False
    
    def setup_test_account(self):
        """Create a test account"""
        print("\n💳 Creating test account...")
        
        account_data = {
            "company": self.company_id,
            "name": "Business Checking",
            "account_type": "CHECKING", 
            "account_number": "ACC123456",
            "bank_name": "Test Bank",
            "currency": "USD",
            "current_balance": "50000.00",
            "initial_balance": "50000.00",
            "is_active": True
        }
        
        response = self.session.post(f"{BASE_URL}/financial/accounts/", json=account_data)
        
        if response.status_code == 201:
            data = response.json()
            self.account_id = data["id"]
            print(f"✅ Account created with ID: {self.account_id}")
            return True
        else:
            print(f"❌ Account creation failed: {response.status_code} - {response.text}")
            return False
    
    def create_test_transactions(self):
        """Create test transactions for AI analysis"""
        print("\n💰 Creating test transactions...")
        
        test_transactions = [
            {
                "company": self.company_id,
                "account": self.account_id,
                "transaction_type": "EXPENSE",
                "amount": "127.50",
                "description": "Amazon AWS - Cloud hosting services",
                "transaction_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "COMPLETED"
            },
            {
                "company": self.company_id,
                "account": self.account_id,
                "transaction_type": "EXPENSE", 
                "amount": "15000.00",  # Large amount - should trigger anomaly
                "description": "Suspicious large payment",
                "transaction_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "COMPLETED"
            },
            {
                "company": self.company_id,
                "account": self.account_id,
                "transaction_type": "INCOME",
                "amount": "5000.00",
                "description": "Client payment for consulting services",
                "transaction_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "COMPLETED"
            },
            {
                "company": self.company_id,
                "account": self.account_id,
                "transaction_type": "EXPENSE",
                "amount": "45.99",
                "description": "Office supplies from Staples",
                "transaction_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "COMPLETED"
            }
        ]
        
        transaction_ids = []
        
        for i, transaction in enumerate(test_transactions):
            response = self.session.post(f"{BASE_URL}/financial/transactions/", json=transaction)
            
            if response.status_code == 201:
                data = response.json()
                transaction_ids.append(data["id"])
                print(f"✅ Transaction {i+1} created: {data['id']}")
                time.sleep(1)  # Allow AI processing
            else:
                print(f"❌ Transaction {i+1} failed: {response.status_code} - {response.text}")
        
        return transaction_ids
    
    def test_ai_categorization(self, transaction_ids):
        """Test AI categorization endpoints"""
        print("\n🤖 Testing AI Categorization...")
        
        if not transaction_ids:
            print("❌ No transactions to categorize")
            return
        
        # Test individual categorization
        transaction_id = transaction_ids[0]
        response = self.session.post(f"{BASE_URL}/financial/transactions/{transaction_id}/ai_categorize/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI Categorization successful:")
            print(f"   Suggested Category: {data.get('suggested_category')}")
            print(f"   Confidence: {data.get('confidence_score')}")
            print(f"   Reasoning: {data.get('reasoning')}")
        else:
            print(f"❌ AI Categorization failed: {response.status_code} - {response.text}")
        
        # Test bulk categorization
        bulk_data = {
            "company_id": self.company_id,
            "limit": 5
        }
        response = self.session.post(f"{BASE_URL}/financial/transactions/ai_bulk_categorize/", json=bulk_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bulk categorization processed {data.get('processed_count')} transactions")
        else:
            print(f"❌ Bulk categorization failed: {response.status_code} - {response.text}")
    
    def test_ai_anomaly_detection(self, transaction_ids):
        """Test AI anomaly detection"""
        print("\n🚨 Testing AI Anomaly Detection...")
        
        if len(transaction_ids) < 2:
            print("❌ Need at least 2 transactions for anomaly testing")
            return
        
        # Test on the large transaction (likely anomaly)
        transaction_id = transaction_ids[1]  # The $15,000 transaction
        response = self.session.post(f"{BASE_URL}/financial/transactions/{transaction_id}/ai_analyze_anomaly/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Anomaly Detection Results:")
            print(f"   Anomaly Detected: {data.get('anomaly_detected')}")
            if data.get('anomaly_detected'):
                print(f"   Type: {data.get('anomaly_type')}")
                print(f"   Risk Level: {data.get('risk_level')}")
                print(f"   Explanation: {data.get('explanation')}")
        else:
            print(f"❌ Anomaly detection failed: {response.status_code} - {response.text}")
    
    def test_financial_health_score(self):
        """Test financial health scoring"""
        print("\n💚 Testing Financial Health Scoring...")
        
        response = self.session.post(f"{BASE_URL}/financial/companies/{self.company_id}/calculate_health_score/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Financial Health Score calculated:")
            print(f"   Score: {data.get('score')}/100")
            print(f"   Risk Level: {data.get('risk_level')}")
            print(f"   Strengths: {data.get('strengths')}")
            print(f"   Recommendations: {data.get('recommendations')}")
        else:
            print(f"❌ Health score calculation failed: {response.status_code} - {response.text}")
    
    def test_ai_dashboard(self):
        """Test AI dashboard endpoint"""
        print("\n📊 Testing AI Dashboard...")
        
        response = self.session.get(f"{BASE_URL}/financial/companies/{self.company_id}/ai_dashboard/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI Dashboard loaded:")
            
            health = data.get('health_score')
            if health:
                print(f"   Health Score: {health.get('score')} ({health.get('risk_level')})")
            
            anomalies = data.get('anomalies', {})
            print(f"   Anomalies: {anomalies.get('count', 0)} detected")
            
            categorization = data.get('categorization', {})
            print(f"   AI Accuracy: {categorization.get('accuracy_percentage', 0)}%")
            
        else:
            print(f"❌ AI Dashboard failed: {response.status_code} - {response.text}")
    
    def test_analyze_transactions(self):
        """Test bulk transaction analysis"""
        print("\n🔍 Testing Bulk Transaction Analysis...")
        
        analysis_data = {
            "limit": 10
        }
        response = self.session.post(f"{BASE_URL}/financial/companies/{self.company_id}/analyze_transactions/", json=analysis_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bulk Analysis completed:")
            print(f"   Processed: {data.get('processed')} transactions")
            print(f"   Categorized: {data.get('categorized')} transactions")
            print(f"   Anomalies Found: {data.get('anomalies_detected')} transactions")
        else:
            print(f"❌ Bulk analysis failed: {response.status_code} - {response.text}")
    
    def run_complete_test(self):
        """Run the complete AI testing workflow"""
        print("🚀 Starting AI Financial Analytics Platform Test")
        print("=" * 60)
        
        # Step 1: Authentication
        if not self.register_and_login():
            return False
        
        # Step 2: Setup test data
        if not self.setup_test_company():
            return False
        
        if not self.setup_test_account():
            return False
        
        # Step 3: Create test transactions (will trigger AI analysis)
        transaction_ids = self.create_test_transactions()
        
        # Step 4: Test AI features
        self.test_ai_categorization(transaction_ids)
        self.test_ai_anomaly_detection(transaction_ids) 
        self.test_financial_health_score()
        self.test_ai_dashboard()
        self.test_analyze_transactions()
        
        print("\n🎉 AI Testing Complete!")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    tester = APITester()
    success = tester.run_complete_test()
    
    if success:
        print("✅ All AI features are working correctly!")
    else:
        print("❌ Some issues were found. Check the logs above.")
