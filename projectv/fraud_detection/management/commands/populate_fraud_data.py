from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Company, Account, Transaction, TransactionCategory
from fraud_detection.models import FraudDetectionRule, FraudAlert, FraudMetrics
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Populate sample fraud detection data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample fraud detection data...')
        
        # Get or create a user first (required for company)
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@samplecorp.com',
                'first_name': 'Admin',
                'last_name': 'User'
            }
        )
        
        # Get or create a company
        company, created = Company.objects.get_or_create(
            name='Sample Corp',
            defaults={
                'owner': user,
                'registration_number': 'REG123456',
                'tax_id': 'TAX789012',
                'industry': 'Technology',
                'currency': 'USD'
            }
        )
        
        # Create sample fraud detection rules
        rules_data = [
            {
                'name': 'High Amount Threshold',
                'rule_type': 'AMOUNT_THRESHOLD',
                'severity': 'HIGH',
                'parameters': {'description': 'Alert on transactions over threshold'},
                'thresholds': {'max_amount': 5000}
            },
            {
                'name': 'Transaction Velocity Check',
                'rule_type': 'VELOCITY',
                'severity': 'MEDIUM',
                'parameters': {'time_window_minutes': 30, 'description': 'Multiple transactions in short time'},
                'thresholds': {'max_transactions': 3}
            },
            {
                'name': 'Off-Hours Transaction',
                'rule_type': 'TIME_ANOMALY',
                'severity': 'LOW',
                'parameters': {'normal_hours': [6, 22], 'description': 'Transactions outside normal hours'},
                'thresholds': {}
            },
            {
                'name': 'Amount Anomaly Detection',
                'rule_type': 'AMOUNT_ANOMALY',
                'severity': 'HIGH',
                'parameters': {'user_avg_amount': 200, 'description': 'Amount significantly higher than normal'},
                'thresholds': {'amount_multiplier': 10}
            }
        ]
        
        for rule_data in rules_data:
            rule, created = FraudDetectionRule.objects.get_or_create(
                company=company,
                name=rule_data['name'],
                defaults=rule_data
            )
            if created:
                self.stdout.write(f'Created rule: {rule.name}')
        
        # Create sample accounts if they don't exist
        account, created = Account.objects.get_or_create(
            company=company,
            account_number='ACC001',
            defaults={
                'name': 'Main Account',
                'account_type': 'checking',
                'currency': 'USD',
                'current_balance': Decimal('10000.00'),
                'initial_balance': Decimal('10000.00'),
                'bank_name': 'Sample Bank'
            }
        )
        
        # Create sample categories
        category, created = TransactionCategory.objects.get_or_create(
            company=company,
            name='General Expense',
            defaults={
                'is_income': False,
                'color': '#e74c3c',
                'icon': 'expense'
            }
        )
        
        # Create sample transactions
        base_time = timezone.now() - timedelta(days=7)
        sample_transactions = [
            {'amount': 150.00, 'description': 'Coffee Shop', 'hours_offset': 2},
            {'amount': 2500.00, 'description': 'Electronics Store', 'hours_offset': 5},
            {'amount': 8000.00, 'description': 'Large Purchase', 'hours_offset': 10},  # Should trigger amount threshold
            {'amount': 100.00, 'description': 'Late Night ATM', 'hours_offset': 25},  # Should trigger time anomaly
            {'amount': 200.00, 'description': 'Restaurant', 'hours_offset': 30},
            {'amount': 300.00, 'description': 'Gas Station', 'hours_offset': 32},
            {'amount': 150.00, 'description': 'Grocery Store', 'hours_offset': 33},  # Should trigger velocity
        ]
        
        # Create sample transactions
        Transaction.objects.filter(company=company, reference_number__startswith='TXN').delete()  # Clear existing sample data
        
        for i, trans_data in enumerate(sample_transactions):
            transaction_time = base_time + timedelta(hours=trans_data['hours_offset'])
            transaction = Transaction.objects.create(
                company=company,
                account=account,
                amount=Decimal(str(trans_data['amount'])),
                description=trans_data['description'],
                transaction_type='debit',
                category=category,
                transaction_date=transaction_time,
                status='completed',
                reference_number=f'TXN{1000 + i}',
                metadata={'city': 'Sample City', 'country': 'US'}
            )
            self.stdout.write(f'Created transaction: {transaction.description} - ${transaction.amount}')
        
        # Create sample fraud metrics
        for i in range(7):
            date = (timezone.now() - timedelta(days=i)).date()
            metrics, created = FraudMetrics.objects.get_or_create(
                company=company,
                date=date,
                defaults={
                    'total_transactions': random.randint(50, 200),
                    'flagged_transactions': random.randint(1, 10),
                    'confirmed_fraud': random.randint(0, 3),
                    'false_positives': random.randint(0, 5),
                    'avg_risk_score': Decimal(str(random.uniform(10, 40))),
                    'high_risk_count': random.randint(0, 5),
                    'blocked_transactions': random.randint(0, 3),
                    'fraud_amount_detected': Decimal(str(random.uniform(1000, 5000))),
                    'fraud_amount_prevented': Decimal(str(random.uniform(500, 3000))),
                    'false_positive_amount': Decimal(str(random.uniform(100, 1000))),
                    'detection_rate': Decimal(str(random.uniform(85, 95))),
                    'false_positive_rate': Decimal(str(random.uniform(2, 8)))
                }
            )
            if created:
                self.stdout.write(f'Created fraud metrics for {date}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated fraud detection sample data!'))
        self.stdout.write('You can now test the fraud detection APIs with sample data.')
