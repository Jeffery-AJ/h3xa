#!/usr/bin/env python
"""
ProjectV AI CFO API Testing Script
Tests the enhanced fintech platform APIs
"""

import requests
import json
import time
from datetime import datetime, timedelta

class ProjectVAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
    
    def authenticate(self, username="admin", password="admin123"):
        """Authenticate and get JWT token"""
        print("🔐 Authenticating...")
        
        # Get JWT token
        response = self.session.post(f"{self.base_url}/api/auth/login/", {
            "username": username,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get('access_token')
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.text}")
            return False
    
    def test_core_apis(self):
        """Test core financial APIs"""
        print("\n📊 Testing Core APIs...")
        
        # Test companies
        response = self.session.get(f"{self.base_url}/api/v1/companies/")
        if response.status_code == 200:
            print("✅ Companies API working")
            companies = response.json()
            if companies.get('results'):
                self.company_id = companies['results'][0]['id']
            else:
                print("⚠️  No companies found")
        else:
            print(f"❌ Companies API failed: {response.status_code}")
        
        # Test accounts
        response = self.session.get(f"{self.base_url}/api/v1/accounts/")
        if response.status_code == 200:
            print("✅ Accounts API working")
        else:
            print(f"❌ Accounts API failed: {response.status_code}")
        
        # Test transactions
        response = self.session.get(f"{self.base_url}/api/v1/transactions/")
        if response.status_code == 200:
            print("✅ Transactions API working")
        else:
            print(f"❌ Transactions API failed: {response.status_code}")
    
    def test_open_banking_apis(self):
        """Test Open Banking APIs"""
        print("\n🏦 Testing Open Banking APIs...")
        
        # Test bank providers
        response = self.session.get(f"{self.base_url}/api/open-banking/providers/")
        if response.status_code == 200:
            print("✅ Bank Providers API working")
            providers = response.json()
            print(f"📋 Found {len(providers.get('results', []))} bank providers")
        else:
            print(f"❌ Bank Providers API failed: {response.status_code}")
        
        # Test bank connections
        response = self.session.get(f"{self.base_url}/api/open-banking/connections/")
        if response.status_code == 200:
            print("✅ Bank Connections API working")
        else:
            print(f"❌ Bank Connections API failed: {response.status_code}")
        
        # Test linked accounts
        response = self.session.get(f"{self.base_url}/api/open-banking/accounts/")
        if response.status_code == 200:
            print("✅ Linked Accounts API working")
        else:
            print(f"❌ Linked Accounts API failed: {response.status_code}")
    
    def test_fraud_detection_apis(self):
        """Test Fraud Detection APIs"""
        print("\n🛡️  Testing Fraud Detection APIs...")
        
        # Test fraud rules
        response = self.session.get(f"{self.base_url}/api/fraud/rules/")
        if response.status_code == 200:
            print("✅ Fraud Rules API working")
            rules = response.json()
            print(f"📋 Found {len(rules.get('results', []))} fraud rules")
        else:
            print(f"❌ Fraud Rules API failed: {response.status_code}")
        
        # Test fraud alerts
        response = self.session.get(f"{self.base_url}/api/fraud/alerts/")
        if response.status_code == 200:
            print("✅ Fraud Alerts API working")
        else:
            print(f"❌ Fraud Alerts API failed: {response.status_code}")
        
        # Test fraud metrics
        response = self.session.get(f"{self.base_url}/api/fraud/metrics/")
        if response.status_code == 200:
            print("✅ Fraud Metrics API working")
        else:
            print(f"❌ Fraud Metrics API failed: {response.status_code}")
    
    def test_ai_insights_apis(self):
        """Test AI Insights APIs"""
        print("\n🤖 Testing AI Insights APIs...")
        
        # Test health score
        response = self.session.get(f"{self.base_url}/api/ai/health-score/")
        if response.status_code == 200:
            print("✅ Health Score API working")
            health_data = response.json()
            if health_data.get('results'):
                latest_score = health_data['results'][0]
                print(f"📊 Latest health score: {latest_score.get('score', 'N/A')}")
        else:
            print(f"❌ Health Score API failed: {response.status_code}")
        
        # Test anomaly detection
        response = self.session.get(f"{self.base_url}/api/ai/anomaly-detection/")
        if response.status_code == 200:
            print("✅ Anomaly Detection API working")
        else:
            print(f"❌ Anomaly Detection API failed: {response.status_code}")
        
        # Test predictions
        response = self.session.get(f"{self.base_url}/api/ai/prediction-models/")
        if response.status_code == 200:
            print("✅ Prediction Models API working")
        else:
            print(f"❌ Prediction Models API failed: {response.status_code}")
    
    def create_sample_transaction(self):
        """Create a sample transaction for testing"""
        print("\n💰 Creating sample transaction...")
        
        if not hasattr(self, 'company_id'):
            print("⚠️  No company ID available, skipping transaction creation")
            return
        
        # First, create an account if none exists
        accounts_response = self.session.get(f"{self.base_url}/api/v1/accounts/")
        accounts = accounts_response.json().get('results', [])
        
        if not accounts:
            # Create a sample account
            account_data = {
                "name": "Test Checking Account",
                "account_type": "checking",
                "bank_name": "Test Bank",
                "current_balance": 5000.00,
                "initial_balance": 5000.00
            }
            account_response = self.session.post(
                f"{self.base_url}/api/v1/accounts/", 
                json=account_data
            )
            if account_response.status_code == 201:
                account_id = account_response.json()['id']
                print("✅ Sample account created")
            else:
                print(f"❌ Failed to create account: {account_response.text}")
                return
        else:
            account_id = accounts[0]['id']
        
        # Create a sample transaction
        transaction_data = {
            "account": account_id,
            "transaction_type": "expense",
            "amount": 150.00,
            "description": "Test grocery purchase",
            "transaction_date": datetime.now().isoformat()
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/transactions/", 
            json=transaction_data
        )
        
        if response.status_code == 201:
            print("✅ Sample transaction created")
            transaction = response.json()
            print(f"💳 Transaction ID: {transaction['id']}")
            return transaction['id']
        else:
            print(f"❌ Failed to create transaction: {response.text}")
            return None
    
    def test_fraud_detection_on_transaction(self, transaction_id):
        """Test fraud detection on a specific transaction"""
        if not transaction_id:
            return
        
        print(f"\n🔍 Testing fraud detection on transaction {transaction_id}...")
        
        # Wait a moment for fraud detection to process
        time.sleep(2)
        
        # Check for fraud alerts
        response = self.session.get(
            f"{self.base_url}/api/fraud/alerts/?transaction={transaction_id}"
        )
        
        if response.status_code == 200:
            alerts = response.json().get('results', [])
            if alerts:
                print(f"⚠️  Fraud alert generated! Risk score: {alerts[0].get('risk_score', 'N/A')}")
            else:
                print("✅ No fraud alerts (transaction appears legitimate)")
        else:
            print(f"❌ Failed to check fraud alerts: {response.status_code}")
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive test report"""
        print("\n📈 Generating comprehensive test report...")
        
        try:
            # Test AI comprehensive insights
            response = self.session.get(f"{self.base_url}/api/ai/insights/comprehensive/")
            if response.status_code == 200:
                insights = response.json()
                print("✅ Comprehensive AI insights generated")
                
                # Display key metrics
                health_score = insights.get('health_score', {}).get('score', 'N/A')
                print(f"📊 Financial Health Score: {health_score}")
                
                predictions = insights.get('predictions', {})
                if predictions.get('cash_flow'):
                    cash_flow_summary = predictions['cash_flow'].get('summary', {})
                    print(f"💰 30-day Cash Flow Prediction: ${cash_flow_summary.get('total_30d_cash_flow', 'N/A')}")
                
                recommendations = insights.get('recommendations', [])
                print(f"💡 AI Recommendations: {len(recommendations)} generated")
                
            else:
                print(f"❌ Failed to generate comprehensive insights: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error generating report: {str(e)}")
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 ProjectV AI CFO API Test Suite")
        print("=" * 50)
        
        if not self.authenticate():
            return
        
        # Test all API endpoints
        self.test_core_apis()
        self.test_open_banking_apis()
        self.test_fraud_detection_apis()
        self.test_ai_insights_apis()
        
        # Create sample data and test AI features
        transaction_id = self.create_sample_transaction()
        self.test_fraud_detection_on_transaction(transaction_id)
        self.generate_comprehensive_report()
        
        print("\n✅ API testing complete!")
        print("\n📝 Test Summary:")
        print("- Core financial APIs: Tested")
        print("- Open Banking APIs: Tested")
        print("- Fraud Detection APIs: Tested")
        print("- AI Insights APIs: Tested")
        print("- Sample transaction: Created and analyzed")

def main():
    """Main testing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test ProjectV AI CFO APIs')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL for the API')
    parser.add_argument('--username', default='admin', 
                       help='Username for authentication')
    parser.add_argument('--password', default='admin123', 
                       help='Password for authentication')
    
    args = parser.parse_args()
    
    tester = ProjectVAPITester(args.base_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
