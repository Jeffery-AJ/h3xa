#!/usr/bin/env python
"""
Comprehensive Fraud Detection Test Script
Tests anomaly detection, rule-based detection, and ML models
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'h3xa.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Company, Account, Transaction, TransactionType
from fraud_detection.models import FraudDetectionRule, BehavioralProfile
from fraud_detection.ai_engine import FraudDetectionEngine

User = get_user_model()


class FraudDetectionTest:
    def __init__(self):
        self.engine = FraudDetectionEngine()
        self.user = None
        self.company = None
        self.account = None
        self.transaction_type = None
        
    def setup_test_data(self):
        """Create test user, company, and account"""
        print("🔧 Setting up test data...")
        
        # Create test user
        self.user, created = User.objects.get_or_create(
            email='fraud_test@example.com',
            defaults={
                'username': 'fraud_test_user',
                'first_name': 'Fraud',
                'last_name': 'Tester'
            }
        )
        if created:
            self.user.set_password('testpass123')
            self.user.save()
        
        # Create test company
        self.company, created = Company.objects.get_or_create(
            name='Fraud Test Company',
            owner=self.user,
            defaults={
                'registration_number': 'FRAUD123',
                'address': '123 Test Street'
            }
        )
        
        # Create test account
        self.account, created = Account.objects.get_or_create(
            company=self.company,
            name='Test Fraud Account',
            defaults={
                'account_number': 'FRAUD-ACC-001',
                'account_type': 'checking',
                'current_balance': Decimal('50000.00')
            }
        )
        
        # Create transaction type
        self.transaction_type, created = TransactionType.objects.get_or_create(
            name='Transfer',
            defaults={'description': 'Bank transfer'}
        )
        
        print(f"✅ Test data setup complete")
        print(f"   User: {self.user.email}")
        print(f"   Company: {self.company.name}")
        print(f"   Account: {self.account.name}")
    
    def create_normal_transaction_pattern(self):
        """Create normal transaction patterns to establish baseline"""
        print("\n📊 Creating normal transaction patterns...")
        
        base_date = timezone.now() - timedelta(days=30)
        normal_transactions = []
        
        # Create 50 normal transactions over 30 days
        for i in range(50):
            transaction_date = base_date + timedelta(
                days=i % 25,  # Spread over 25 days
                hours=9 + (i % 8),  # Business hours 9-17
                minutes=i % 60
            )
            
            # Normal amounts between $100-$5000
            amount = Decimal(str(200 + (i * 50) % 4800))
            
            transaction = Transaction.objects.create(
                company=self.company,
                account=self.account,
                transaction_type=self.transaction_type,
                amount=amount,
                description=f"Normal business transaction {i+1}",
                reference_number=f"NOR-{i+1:03d}",
                transaction_date=transaction_date,
                status='completed'
            )
            normal_transactions.append(transaction)
        
        print(f"✅ Created {len(normal_transactions)} normal transactions")
        return normal_transactions
    
    def create_fraud_detection_rules(self):
        """Create fraud detection rules"""
        print("\n🛡️ Creating fraud detection rules...")
        
        rules = []
        
        # High amount threshold rule
        rule1 = FraudDetectionRule.objects.create(
            company=self.company,
            name="High Amount Threshold",
            rule_type="AMOUNT_THRESHOLD",
            severity="HIGH",
            is_active=True,
            parameters={
                "amount_threshold": 10000.00,
                "currency": "USD"
            },
            thresholds={
                "risk_score_threshold": 80
            }
        )
        rules.append(rule1)
        
        # Velocity check rule
        rule2 = FraudDetectionRule.objects.create(
            company=self.company,
            name="Transaction Velocity Check",
            rule_type="VELOCITY_CHECK",
            severity="MEDIUM",
            is_active=True,
            parameters={
                "max_transactions": 10,
                "time_window_hours": 1
            },
            thresholds={
                "risk_score_threshold": 70
            }
        )
        rules.append(rule2)
        
        # Amount anomaly rule
        rule3 = FraudDetectionRule.objects.create(
            company=self.company,
            name="Amount Anomaly Detection",
            rule_type="AMOUNT_ANOMALY",
            severity="HIGH",
            is_active=True,
            parameters={
                "lookback_days": 30
            },
            thresholds={
                "anomaly_multiplier": 3.0,
                "risk_score_threshold": 75
            }
        )
        rules.append(rule3)
        
        # Time anomaly rule
        rule4 = FraudDetectionRule.objects.create(
            company=self.company,
            name="Time Anomaly Detection",
            rule_type="TIME_ANOMALY",
            severity="MEDIUM",
            is_active=True,
            parameters={
                "unusual_hour_threshold": 22
            },
            thresholds={
                "risk_score_threshold": 60
            }
        )
        rules.append(rule4)
        
        print(f"✅ Created {len(rules)} fraud detection rules")
        return rules
    
    def test_anomaly_detection(self):
        """Test various anomaly detection scenarios"""
        print("\n🚨 Testing Anomaly Detection...")
        
        test_cases = []
        
        # Test Case 1: High Amount Anomaly
        print("\n   Test 1: High Amount Transaction")
        high_amount_transaction = Transaction.objects.create(
            company=self.company,
            account=self.account,
            transaction_type=self.transaction_type,
            amount=Decimal('25000.00'),  # Much higher than normal
            description="Suspicious high amount transfer",
            reference_number="ANOM-001",
            transaction_date=timezone.now(),
            status='pending'
        )
        
        result1 = self.engine.analyze_transaction(high_amount_transaction)
        test_cases.append({
            'case': 'High Amount Anomaly',
            'transaction': high_amount_transaction,
            'result': result1
        })
        
        print(f"      💰 Amount: ${high_amount_transaction.amount}")
        print(f"      🎯 Risk Score: {result1.get('risk_score', 0):.1f}")
        print(f"      🔍 Anomaly Factors: {result1.get('anomaly_factors', [])}")
        
        # Test Case 2: Time Anomaly (3 AM transaction)
        print("\n   Test 2: Unusual Time Transaction")
        night_transaction = Transaction.objects.create(
            company=self.company,
            account=self.account,
            transaction_type=self.transaction_type,
            amount=Decimal('1500.00'),
            description="Late night transaction",
            reference_number="ANOM-002",
            transaction_date=timezone.now().replace(hour=3, minute=0),
            status='pending'
        )
        
        result2 = self.engine.analyze_transaction(night_transaction)
        test_cases.append({
            'case': 'Time Anomaly',
            'transaction': night_transaction,
            'result': result2
        })
        
        print(f"      🕒 Time: {night_transaction.transaction_date.strftime('%H:%M')}")
        print(f"      🎯 Risk Score: {result2.get('risk_score', 0):.1f}")
        print(f"      🔍 Anomaly Factors: {result2.get('anomaly_factors', [])}")
        
        # Test Case 3: Velocity Anomaly (Multiple rapid transactions)
        print("\n   Test 3: High Velocity Transactions")
        velocity_transactions = []
        for i in range(5):
            transaction = Transaction.objects.create(
                company=self.company,
                account=self.account,
                transaction_type=self.transaction_type,
                amount=Decimal('2000.00'),
                description=f"Rapid transaction {i+1}",
                reference_number=f"VEL-{i+1:03d}",
                transaction_date=timezone.now() + timedelta(minutes=i*5),
                status='pending'
            )
            velocity_transactions.append(transaction)
        
        # Analyze the last transaction (should detect velocity)
        result3 = self.engine.analyze_transaction(velocity_transactions[-1])
        test_cases.append({
            'case': 'Velocity Anomaly',
            'transaction': velocity_transactions[-1],
            'result': result3
        })
        
        print(f"      🚀 Transactions: {len(velocity_transactions)} in 25 minutes")
        print(f"      🎯 Risk Score: {result3.get('risk_score', 0):.1f}")
        print(f"      🔍 Anomaly Factors: {result3.get('anomaly_factors', [])}")
        
        # Test Case 4: Normal Transaction (should pass)
        print("\n   Test 4: Normal Transaction (Control)")
        normal_transaction = Transaction.objects.create(
            company=self.company,
            account=self.account,
            transaction_type=self.transaction_type,
            amount=Decimal('800.00'),
            description="Normal business expense",
            reference_number="NORM-001",
            transaction_date=timezone.now().replace(hour=14, minute=30),
            status='pending'
        )
        
        result4 = self.engine.analyze_transaction(normal_transaction)
        test_cases.append({
            'case': 'Normal Transaction',
            'transaction': normal_transaction,
            'result': result4
        })
        
        print(f"      💰 Amount: ${normal_transaction.amount}")
        print(f"      🎯 Risk Score: {result4.get('risk_score', 0):.1f}")
        print(f"      ✅ Should be low risk")
        
        return test_cases
    
    def test_behavioral_profiling(self):
        """Test behavioral profiling functionality"""
        print("\n🧠 Testing Behavioral Profiling...")
        
        # Get or create behavioral profile
        profile, created = BehavioralProfile.objects.get_or_create(
            company=self.company,
            account=self.account,
            defaults={
                'avg_transaction_amount': Decimal('0.00'),
                'std_transaction_amount': Decimal('0.00'),
                'max_daily_amount': Decimal('0.00'),
                'max_daily_count': 0
            }
        )
        
        if created:
            print("   📊 Created new behavioral profile")
        else:
            print("   📊 Using existing behavioral profile")
        
        # Update profile with normal transactions
        self.engine._update_behavioral_profile(self.account, None)
        profile.refresh_from_db()
        
        print(f"   📈 Average Transaction: ${profile.avg_transaction_amount}")
        print(f"   📊 Std Deviation: ${profile.std_transaction_amount}")
        print(f"   📅 Max Daily Amount: ${profile.max_daily_amount}")
        print(f"   🔢 Max Daily Count: {profile.max_daily_count}")
        print(f"   🕐 Typical Hours: {profile.typical_hours}")
        print(f"   📅 Typical Days: {profile.typical_days}")
        
        return profile
    
    def generate_test_report(self, test_cases):
        """Generate a comprehensive test report"""
        print("\n📋 FRAUD DETECTION TEST REPORT")
        print("=" * 50)
        
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{i}. {case['case']}")
            print("-" * 30)
            
            result = case['result']
            risk_score = result.get('risk_score', 0)
            
            print(f"   Risk Score: {risk_score:.1f}/100")
            print(f"   Confidence: {result.get('confidence', 0):.1f}%")
            
            if risk_score >= 80:
                risk_level = "🔴 HIGH RISK"
                high_risk_count += 1
            elif risk_score >= 50:
                risk_level = "🟡 MEDIUM RISK"
                medium_risk_count += 1
            else:
                risk_level = "🟢 LOW RISK"
                low_risk_count += 1
            
            print(f"   Risk Level: {risk_level}")
            
            if result.get('anomaly_factors'):
                print(f"   Anomaly Factors: {', '.join(result['anomaly_factors'])}")
            
            if result.get('rule_results', {}).get('rule_matches'):
                print(f"   Triggered Rules: {len(result['rule_results']['rule_matches'])}")
        
        print(f"\n📊 SUMMARY")
        print("-" * 20)
        print(f"Total Tests: {len(test_cases)}")
        print(f"🔴 High Risk: {high_risk_count}")
        print(f"🟡 Medium Risk: {medium_risk_count}")
        print(f"🟢 Low Risk: {low_risk_count}")
        
        # Test effectiveness
        if high_risk_count >= 2:  # Expecting high amounts and velocity to be high risk
            print("\n✅ ANOMALY DETECTION IS WORKING!")
            print("   System successfully identified suspicious patterns")
        else:
            print("\n⚠️  ANOMALY DETECTION NEEDS TUNING")
            print("   Consider adjusting thresholds or rules")
    
    def run_comprehensive_test(self):
        """Run the complete fraud detection test suite"""
        print("🚀 Starting Comprehensive Fraud Detection Test")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            
            # Create baseline data
            self.create_normal_transaction_pattern()
            
            # Setup rules
            self.create_fraud_detection_rules()
            
            # Test behavioral profiling
            self.test_behavioral_profiling()
            
            # Test anomaly detection
            test_cases = self.test_anomaly_detection()
            
            # Generate report
            self.generate_test_report(test_cases)
            
            print("\n🎉 Test completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    """Main test runner"""
    test_runner = FraudDetectionTest()
    test_runner.run_comprehensive_test()


if __name__ == "__main__":
    main()
