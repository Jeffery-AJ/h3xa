import csv
import io
import pandas as pd
import numpy as np
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import (
    Company, Account, TransactionCategory, Transaction, 
    Budget, FinancialGoal
)
from .models import BulkUpload, BulkUploadError

class CSVProcessor:
    """Base class for CSV processing"""
    
    def __init__(self, user, company, upload_type):
        self.user = user
        self.company = company
        self.upload_type = upload_type
        self.bulk_upload = None
        self.errors = []
        self.processed_data = []
        
    def create_bulk_upload_record(self, file_name, total_records):
        """Create a bulk upload tracking record"""
        self.bulk_upload = BulkUpload.objects.create(
            user=self.user,
            company=self.company,
            upload_type=self.upload_type,
            file_name=file_name,
            total_records=total_records,
            status='PROCESSING'
        )
        return self.bulk_upload
    
    def add_error(self, row_number, field_name, error_message, row_data):
        """Add an error to the bulk upload"""
        if self.bulk_upload:
            BulkUploadError.objects.create(
                bulk_upload=self.bulk_upload,
                row_number=row_number,
                field_name=field_name,
                error_message=error_message,
                row_data=row_data
            )
        self.errors.append({
            'row': row_number,
            'field': field_name,
            'error': error_message,
            'data': row_data
        })
    
    def finalize_upload(self, successful_count, failed_count):
        """Finalize the bulk upload record"""
        if self.bulk_upload:
            self.bulk_upload.successful_records = successful_count
            self.bulk_upload.failed_records = failed_count
            self.bulk_upload.status = 'COMPLETED' if failed_count == 0 else 'PARTIAL_SUCCESS'
            self.bulk_upload.completed_at = timezone.now()
            self.bulk_upload.save()

    def to_dataframe(self, csv_file):
        """Convert CSV to pandas DataFrame for analysis"""
        try:
            content = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
            return df
        except Exception as e:
            raise Exception(f"Failed to read CSV file: {str(e)}")

class AccountCSVProcessor(CSVProcessor):
    """Process account CSV uploads"""
    
    REQUIRED_FIELDS = ['name', 'account_type', 'initial_balance']
    ACCOUNT_TYPES = dict(Account.ACCOUNT_TYPES)
    
    def process_csv(self, csv_file):
        """Process accounts CSV file"""
        try:
            # Read CSV content
            content = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Create bulk upload record
            rows = list(csv_reader)
            self.create_bulk_upload_record(csv_file.name, len(rows))
            
            successful_count = 0
            failed_count = 0
            
            with transaction.atomic():
                for row_num, row in enumerate(rows, start=2):  # Start from 2 (accounting for header)
                    try:
                        account_data = self.validate_account_row(row, row_num)
                        if account_data:
                            Account.objects.create(**account_data)
                            self.processed_data.append(account_data)
                            successful_count += 1
                    except Exception as e:
                        failed_count += 1
                        self.add_error(row_num, '', str(e), row)
            
            self.finalize_upload(successful_count, failed_count)
            return self.bulk_upload
            
        except Exception as e:
            if self.bulk_upload:
                self.bulk_upload.status = 'FAILED'
                self.bulk_upload.error_details = [str(e)]
                self.bulk_upload.save()
            raise e
    
    def validate_account_row(self, row, row_num):
        """Validate and process a single account row"""
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if not row.get(field, '').strip():
                self.add_error(row_num, field, f"Required field '{field}' is missing", row)
                return None
        
        try:
            # Validate account type
            account_type = row['account_type'].upper().strip()
            if account_type not in self.ACCOUNT_TYPES:
                valid_types = ', '.join(self.ACCOUNT_TYPES.keys())
                self.add_error(row_num, 'account_type', 
                             f"Invalid account type. Valid types: {valid_types}", row)
                return None
            
            # Validate initial balance
            try:
                initial_balance = Decimal(row['initial_balance'].strip())
            except (InvalidOperation, ValueError):
                self.add_error(row_num, 'initial_balance', 
                             "Invalid initial balance format", row)
                return None
            
            # Check for duplicate account names
            if Account.objects.filter(company=self.company, name=row['name'].strip()).exists():
                self.add_error(row_num, 'name', 
                             f"Account with name '{row['name'].strip()}' already exists", row)
                return None
            
            # Prepare account data
            account_data = {
                'company': self.company,
                'name': row['name'].strip(),
                'account_type': account_type,
                'initial_balance': initial_balance,
                'current_balance': initial_balance,  # Default to initial balance
                'currency': row.get('currency', 'USD').strip(),
                'description': row.get('description', '').strip(),
                'account_number': row.get('account_number', '').strip(),
                'bank_name': row.get('bank_name', '').strip(),
            }
            
            return account_data
            
        except Exception as e:
            self.add_error(row_num, '', str(e), row)
            return None

class TransactionCSVProcessor(CSVProcessor):
    """Process transaction CSV uploads"""
    
    REQUIRED_FIELDS = ['account_name', 'transaction_type', 'amount', 'description', 'transaction_date']
    TRANSACTION_TYPES = dict(Transaction.TRANSACTION_TYPES)
    
    def process_csv(self, csv_file):
        """Process transactions CSV file"""
        try:
            content = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            rows = list(csv_reader)
            self.create_bulk_upload_record(csv_file.name, len(rows))
            
            successful_count = 0
            failed_count = 0
            
            with transaction.atomic():
                for row_num, row in enumerate(rows, start=2):
                    try:
                        transaction_data = self.validate_transaction_row(row, row_num)
                        if transaction_data:
                            Transaction.objects.create(**transaction_data)
                            self.processed_data.append(transaction_data)
                            successful_count += 1
                    except Exception as e:
                        failed_count += 1
                        self.add_error(row_num, '', str(e), row)
            
            self.finalize_upload(successful_count, failed_count)
            return self.bulk_upload
            
        except Exception as e:
            if self.bulk_upload:
                self.bulk_upload.status = 'FAILED'
                self.bulk_upload.error_details = [str(e)]
                self.bulk_upload.save()
            raise e
    
    def validate_transaction_row(self, row, row_num):
        """Validate and process a single transaction row"""
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if not row.get(field, '').strip():
                self.add_error(row_num, field, f"Required field '{field}' is missing", row)
                return None
        
        try:
            # Find account by name
            account_name = row['account_name'].strip()
            try:
                account = Account.objects.get(company=self.company, name=account_name)
            except Account.DoesNotExist:
                self.add_error(row_num, 'account_name', 
                             f"Account '{account_name}' not found", row)
                return None
            
            # Validate transaction type
            transaction_type = row['transaction_type'].upper().strip()
            if transaction_type not in self.TRANSACTION_TYPES:
                valid_types = ', '.join(self.TRANSACTION_TYPES.keys())
                self.add_error(row_num, 'transaction_type', 
                             f"Invalid transaction type. Valid types: {valid_types}", row)
                return None
            
            # Validate amount
            try:
                amount = Decimal(row['amount'].strip())
                if amount <= 0:
                    self.add_error(row_num, 'amount', "Amount must be positive", row)
                    return None
            except (InvalidOperation, ValueError):
                self.add_error(row_num, 'amount', "Invalid amount format", row)
                return None
            
            # Validate date
            try:
                transaction_date = datetime.strptime(row['transaction_date'].strip(), '%Y-%m-%d').date()
            except ValueError:
                try:
                    transaction_date = datetime.strptime(row['transaction_date'].strip(), '%m/%d/%Y').date()
                except ValueError:
                    self.add_error(row_num, 'transaction_date', 
                                 "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY", row)
                    return None
            
            # Find or create category if specified
            category = None
            if row.get('category_name', '').strip():
                category_name = row['category_name'].strip()
                try:
                    category = TransactionCategory.objects.get(
                        company=self.company, 
                        name=category_name
                    )
                except TransactionCategory.DoesNotExist:
                    # Create category if it doesn't exist
                    category = TransactionCategory.objects.create(
                        company=self.company,
                        name=category_name,
                        is_income=(transaction_type == 'INCOME')
                    )
            
            # Prepare transaction data
            transaction_data = {
                'company': self.company,
                'account': account,
                'category': category,
                'transaction_type': transaction_type,
                'amount': amount,
                'description': row['description'].strip(),
                'transaction_date': transaction_date,
                'reference_number': row.get('reference_number', '').strip(),
                'status': 'COMPLETED',  # Default status
            }
            
            return transaction_data
            
        except Exception as e:
            self.add_error(row_num, '', str(e), row)
            return None

class CategoryCSVProcessor(CSVProcessor):
    """Process category CSV uploads"""
    
    REQUIRED_FIELDS = ['name', 'is_income']
    
    def process_csv(self, csv_file):
        """Process categories CSV file"""
        try:
            content = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            rows = list(csv_reader)
            self.create_bulk_upload_record(csv_file.name, len(rows))
            
            successful_count = 0
            failed_count = 0
            
            with transaction.atomic():
                for row_num, row in enumerate(rows, start=2):
                    try:
                        category_data = self.validate_category_row(row, row_num)
                        if category_data:
                            TransactionCategory.objects.create(**category_data)
                            self.processed_data.append(category_data)
                            successful_count += 1
                    except Exception as e:
                        failed_count += 1
                        self.add_error(row_num, '', str(e), row)
            
            self.finalize_upload(successful_count, failed_count)
            return self.bulk_upload
            
        except Exception as e:
            if self.bulk_upload:
                self.bulk_upload.status = 'FAILED'
                self.bulk_upload.error_details = [str(e)]
                self.bulk_upload.save()
            raise e
    
    def validate_category_row(self, row, row_num):
        """Validate and process a single category row"""
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if not row.get(field, '').strip():
                self.add_error(row_num, field, f"Required field '{field}' is missing", row)
                return None
        
        try:
            # Check if category already exists
            if TransactionCategory.objects.filter(
                company=self.company, 
                name=row['name'].strip()
            ).exists():
                self.add_error(row_num, 'name', 
                             f"Category '{row['name'].strip()}' already exists", row)
                return None
            
            # Validate is_income
            is_income_str = row['is_income'].strip().lower()
            if is_income_str in ['true', '1', 'yes', 'income']:
                is_income = True
            elif is_income_str in ['false', '0', 'no', 'expense']:
                is_income = False
            else:
                self.add_error(row_num, 'is_income', 
                             "Invalid value for is_income. Use true/false or income/expense", row)
                return None
            
            # Prepare category data
            category_data = {
                'company': self.company,
                'name': row['name'].strip(),
                'description': row.get('description', '').strip(),
                'is_income': is_income,
                'color_code': row.get('color_code', '').strip() or None,
            }
            
            return category_data
            
        except Exception as e:
            self.add_error(row_num, '', str(e), row)
            return None

class CSVAnalyzer:
    """Analyze CSV data for insights generation"""
    
    def __init__(self, processor):
        self.processor = processor
        self.df = None
        
    def analyze_accounts_data(self):
        """Analyze accounts data for insights"""
        if not self.processor.processed_data:
            return {}
            
        accounts_data = self.processor.processed_data
        
        analysis = {
            'total_accounts': len(accounts_data),
            'account_types': {},
            'total_initial_balance': 0,
            'average_balance': 0,
            'balance_distribution': {},
            'currencies': set(),
        }
        
        balances = []
        for account in accounts_data:
            account_type = account['account_type']
            balance = float(account['initial_balance'])
            
            # Count by type
            analysis['account_types'][account_type] = analysis['account_types'].get(account_type, 0) + 1
            
            # Balance calculations
            analysis['total_initial_balance'] += balance
            balances.append(balance)
            analysis['currencies'].add(account['currency'])
        
        if balances:
            analysis['average_balance'] = sum(balances) / len(balances)
            analysis['min_balance'] = min(balances)
            analysis['max_balance'] = max(balances)
            analysis['median_balance'] = sorted(balances)[len(balances) // 2]
        
        analysis['currencies'] = list(analysis['currencies'])
        return analysis
    
    def analyze_transactions_data(self):
        """Analyze transactions data for insights"""
        if not self.processor.processed_data:
            return {}
            
        transactions_data = self.processor.processed_data
        
        analysis = {
            'total_transactions': len(transactions_data),
            'transaction_types': {},
            'total_amount': 0,
            'income_total': 0,
            'expense_total': 0,
            'categories': {},
            'accounts': {},
            'date_range': {},
            'amount_statistics': {},
        }
        
        amounts = []
        dates = []
        
        for txn in transactions_data:
            txn_type = txn['transaction_type']
            amount = float(txn['amount'])
            txn_date = txn['transaction_date']
            
            # Count by type
            analysis['transaction_types'][txn_type] = analysis['transaction_types'].get(txn_type, 0) + 1
            
            # Amount calculations
            analysis['total_amount'] += amount
            amounts.append(amount)
            
            if txn_type == 'INCOME':
                analysis['income_total'] += amount
            elif txn_type == 'EXPENSE':
                analysis['expense_total'] += amount
            
            # Category analysis
            if txn.get('category'):
                cat_name = txn['category'].name if hasattr(txn['category'], 'name') else str(txn['category'])
                analysis['categories'][cat_name] = analysis['categories'].get(cat_name, 0) + amount
            
            # Account analysis
            acc_name = txn['account'].name if hasattr(txn['account'], 'name') else str(txn['account'])
            analysis['accounts'][acc_name] = analysis['accounts'].get(acc_name, 0) + amount
            
            # Date analysis
            dates.append(txn_date)
        
        # Amount statistics
        if amounts:
            analysis['amount_statistics'] = {
                'average': sum(amounts) / len(amounts),
                'min': min(amounts),
                'max': max(amounts),
                'median': sorted(amounts)[len(amounts) // 2],
                'std_dev': np.std(amounts) if len(amounts) > 1 else 0,
            }
        
        # Date range
        if dates:
            analysis['date_range'] = {
                'start_date': min(dates),
                'end_date': max(dates),
                'span_days': (max(dates) - min(dates)).days if len(dates) > 1 else 0,
            }
        
        # Calculate net income
        analysis['net_income'] = analysis['income_total'] - analysis['expense_total']
        
        return analysis
