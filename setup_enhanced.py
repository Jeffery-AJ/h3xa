#!/usr/bin/env python
"""
ProjectV AI CFO Setup Script
Automates the setup process for the enhanced fintech platform
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        return None

def setup_database():
    """Setup database migrations"""
    print("Setting up database...")
    
    # Make migrations for core apps
    apps = ['core', 'authentication', 'ai_insights', 'open_banking', 'fraud_detection']
    
    for app in apps:
        print(f"Creating migrations for {app}...")
        result = run_command(f"python manage.py makemigrations {app}")
        if result is None:
            print(f"Warning: Could not create migrations for {app}")
    
    # Run migrations
    print("Running migrations...")
    result = run_command("python manage.py migrate")
    if result:
        print("Database setup complete!")
    else:
        print("Error setting up database")

def create_superuser():
    """Create superuser if it doesn't exist"""
    print("Creating superuser...")
    result = run_command(
        "python manage.py shell -c \"from django.contrib.auth.models import User; "
        "User.objects.filter(username='admin').exists() or "
        "User.objects.create_superuser('admin', 'admin@example.com', 'admin123')\""
    )
    if result is not None:
        print("Superuser created: admin/admin123")

def setup_sample_data():
    """Setup sample data for testing"""
    print("Setting up sample data...")
    
    # Create sample bank providers
    setup_script = """
from open_banking.models import BankProvider
from fraud_detection.models import FraudDetectionRule
from core.models import Company, TransactionCategory
from django.contrib.auth.models import User

# Create sample bank providers
providers = [
    {
        'name': 'Sample UK Bank',
        'provider_type': 'UK_OPEN_BANKING',
        'country_code': 'GB',
        'base_url': 'https://api.sandbox-bank.co.uk',
        'is_sandbox': True,
        'supports_payments': True,
        'supports_account_info': True
    },
    {
        'name': 'Plaid Sandbox',
        'provider_type': 'PLAID',
        'country_code': 'US',
        'base_url': 'https://sandbox.plaid.com',
        'is_sandbox': True,
        'supports_payments': False,
        'supports_account_info': True
    }
]

for provider_data in providers:
    provider, created = BankProvider.objects.get_or_create(
        name=provider_data['name'],
        defaults=provider_data
    )
    if created:
        print(f"Created provider: {provider.name}")

# Create sample fraud detection rules
admin_user = User.objects.filter(is_superuser=True).first()
if admin_user:
    sample_company, _ = Company.objects.get_or_create(
        name="Sample Company",
        owner=admin_user,
        defaults={
            'registration_number': 'SC123456',
            'industry': 'Technology',
            'currency': 'USD'
        }
    )
    
    fraud_rules = [
        {
            'name': 'High Velocity Detection',
            'rule_type': 'VELOCITY',
            'severity': 'HIGH',
            'parameters': {'time_window_hours': 24},
            'thresholds': {'max_amount_per_window': 10000, 'max_transactions_per_window': 20}
        },
        {
            'name': 'Large Amount Anomaly',
            'rule_type': 'AMOUNT_ANOMALY',
            'severity': 'MEDIUM',
            'parameters': {},
            'thresholds': {'anomaly_multiplier': 3.0, 'min_amount': 1000}
        }
    ]
    
    for rule_data in fraud_rules:
        rule, created = FraudDetectionRule.objects.get_or_create(
            company=sample_company,
            name=rule_data['name'],
            defaults=rule_data
        )
        if created:
            print(f"Created fraud rule: {rule.name}")
    
    # Create sample categories
    categories = [
        {'name': 'Office Supplies', 'is_income': False, 'color': '#FF6B6B'},
        {'name': 'Software Subscriptions', 'is_income': False, 'color': '#4ECDC4'},
        {'name': 'Consulting Revenue', 'is_income': True, 'color': '#45B7D1'},
        {'name': 'Product Sales', 'is_income': True, 'color': '#96CEB4'},
        {'name': 'Marketing Expenses', 'is_income': False, 'color': '#FFEAA7'},
    ]
    
    for cat_data in categories:
        category, created = TransactionCategory.objects.get_or_create(
            company=sample_company,
            name=cat_data['name'],
            defaults=cat_data
        )
        if created:
            print(f"Created category: {category.name}")

print("Sample data setup complete!")
"""
    
    result = run_command(f"python manage.py shell -c \"{setup_script}\"")
    if result is not None:
        print("Sample data created successfully!")

def main():
    """Main setup function"""
    print("🚀 ProjectV AI CFO Enhanced Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: Please run this script from the Django project directory")
        sys.exit(1)
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'h3xa.settings')
    django.setup()
    
    try:
        # Setup database
        setup_database()
        
        # Create superuser
        create_superuser()
        
        # Setup sample data
        setup_sample_data()
        
        print("\n✅ Setup complete!")
        print("\n📋 Next steps:")
        print("1. Update your .env file with API keys")
        print("2. Configure bank provider credentials")
        print("3. Run: python manage.py runserver")
        print("4. Access admin at: http://localhost:8000/admin/")
        print("5. API documentation at: http://localhost:8000/api/")
        
        print("\n🔐 Default admin credentials:")
        print("Username: admin")
        print("Password: admin123")
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
