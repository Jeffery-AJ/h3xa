import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Any, Optional
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    Company, Account, Transaction, TransactionCategory, Budget, FinancialGoal,
    BulkUpload, BulkUploadError, AccountType, TransactionType
)


class CSVProcessor:
    """Base class for CSV processing operations"""
    
    def __init__(self, company: Company, user: User):
        self.company = company
        self.user = user
        self.errors = []
        self.successful_rows = 0
        self.failed_rows = 0
        
    def validate_required_fields(self, row: Dict, required_fields: List[str], row_number: int) -> bool:
        """Validate that all required fields are present and not empty"""
        missing_fields = []
        for field in required_fields:
            if field not in row or not str(row[field]).strip():
                missing_fields.append(field)
        
        if missing_fields:
            self.add_error(row_number, '', 'missing_field', 
                          f"Missing required fields: {', '.join(missing_fields)}", row)
            return False
        return True
    
    def add_error(self, row_number: int, field_name: str, error_type: str, 
                  error_message: str, row_data: Dict):
        """Add an error to the error list"""
        self.errors.append({
            'row_number': row_number,
            'field_name': field_name,
            'error_type': error_type,
            'error_message': error_message,
            'row_data': row_data
        })
        self.failed_rows += 1
    
    def parse_decimal(self, value: str, field_name: str) -> Optional[Decimal]:
        """Parse decimal value from string"""
        if not value or str(value).strip() == '':
            return None
        try:
            # Remove any currency symbols or commas
            cleaned_value = str(value).replace('$', '').replace(',', '').strip()
            return Decimal(cleaned_value)
        except (InvalidOperation, ValueError):
            return None
    
    def parse_date(self, value: str, field_name: str) -> Optional[datetime]:
        """Parse date value from string"""
        if not value or str(value).strip() == '':
            return None
        
        # Try different date formats
        date_formats = [
            '%Y-%m-%d',  # 2023-12-01
            '%m/%d/%Y',  # 12/01/2023
            '%d/%m/%Y',  # 01/12/2023
            '%Y-%m-%d %H:%M:%S',  # 2023-12-01 10:30:00
            '%m/%d/%Y %H:%M:%S',  # 12/01/2023 10:30:00
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(str(value).strip(), date_format)
            except ValueError:
                continue
        
        return None


class AccountCSVProcessor(CSVProcessor):
    """Process CSV files for Account import"""
    
    REQUIRED_FIELDS = ['name', 'account_type', 'balance']
    OPTIONAL_FIELDS = ['account_number', 'bank_name', 'currency', 'is_active']
    
    def process_csv(self, csv_file, bulk_upload: BulkUpload) -> Tuple[int, int]:
        """Process the CSV file and create Account objects"""
        
        # Read CSV content
        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        total_rows = 0
        
        with transaction.atomic():
            for row_number, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header
                total_rows += 1
                
                # Validate required fields
                if not self.validate_required_fields(row, self.REQUIRED_FIELDS, row_number):
                    continue
                
                try:
                    # Validate account type
                    account_type = row['account_type'].lower().strip()
                    if account_type not in [choice[0] for choice in AccountType.choices]:
                        self.add_error(row_number, 'account_type', 'invalid_choice',
                                     f"Invalid account type: {account_type}. Valid choices: {[choice[0] for choice in AccountType.choices]}", row)
                        continue
                    
                    # Parse balance
                    balance = self.parse_decimal(row['balance'], 'balance')
                    if balance is None:
                        self.add_error(row_number, 'balance', 'invalid_decimal',
                                     f"Invalid balance value: {row['balance']}", row)
                        continue
                    
                    # Check for duplicate account names within company
                    if Account.objects.filter(company=self.company, name=row['name'].strip()).exists():
                        self.add_error(row_number, 'name', 'duplicate',
                                     f"Account with name '{row['name'].strip()}' already exists", row)
                        continue
                    
                    # Create account
                    account = Account.objects.create(
                        company=self.company,
                        name=row['name'].strip(),
                        account_type=account_type,
                        balance=balance,
                        account_number=row.get('account_number', '').strip() or None,
                        bank_name=row.get('bank_name', '').strip() or None,
                        currency=row.get('currency', 'USD').strip().upper(),
                        is_active=str(row.get('is_active', 'true')).lower() in ['true', '1', 'yes']
                    )
                    
                    self.successful_rows += 1
                    
                except Exception as e:
                    self.add_error(row_number, '', 'processing_error', str(e), row)
            
            # Update bulk upload record
            bulk_upload.total_rows = total_rows
            bulk_upload.successful_rows = self.successful_rows
            bulk_upload.failed_rows = self.failed_rows
            
            if self.failed_rows == 0:
                bulk_upload.status = 'completed'
            elif self.successful_rows > 0:
                bulk_upload.status = 'partial'
            else:
                bulk_upload.status = 'failed'
            
            bulk_upload.completed_at = datetime.now()
            bulk_upload.save()
            
            # Save errors
            for error in self.errors:
                BulkUploadError.objects.create(
                    bulk_upload=bulk_upload,
                    row_number=error['row_number'],
                    field_name=error['field_name'],
                    error_type=error['error_type'],
                    error_message=error['error_message'],
                    row_data=error['row_data']
                )
        
        return self.successful_rows, self.failed_rows


class TransactionCSVProcessor(CSVProcessor):
    """Process CSV files for Transaction import"""
    
    REQUIRED_FIELDS = ['account_name', 'amount', 'description', 'date']
    OPTIONAL_FIELDS = ['transaction_type', 'category', 'reference_number', 'tags']
    
    def process_csv(self, csv_file, bulk_upload: BulkUpload) -> Tuple[int, int]:
        """Process the CSV file and create Transaction objects"""
        
        # Read CSV content
        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        total_rows = 0
        
        with transaction.atomic():
            for row_number, row in enumerate(csv_reader, start=2):
                total_rows += 1
                
                # Validate required fields
                if not self.validate_required_fields(row, self.REQUIRED_FIELDS, row_number):
                    continue
                
                try:
                    # Find account by name
                    try:
                        account = Account.objects.get(
                            company=self.company, 
                            name=row['account_name'].strip()
                        )
                    except Account.DoesNotExist:
                        self.add_error(row_number, 'account_name', 'not_found',
                                     f"Account with name '{row['account_name'].strip()}' not found", row)
                        continue
                    
                    # Parse amount
                    amount = self.parse_decimal(row['amount'], 'amount')
                    if amount is None:
                        self.add_error(row_number, 'amount', 'invalid_decimal',
                                     f"Invalid amount value: {row['amount']}", row)
                        continue
                    
                    # Parse date
                    transaction_date = self.parse_date(row['date'], 'date')
                    if transaction_date is None:
                        self.add_error(row_number, 'date', 'invalid_date',
                                     f"Invalid date value: {row['date']}", row)
                        continue
                    
                    # Determine transaction type
                    transaction_type = row.get('transaction_type', '').lower().strip()
                    if not transaction_type:
                        transaction_type = 'expense' if amount < 0 else 'income'
                    elif transaction_type not in [choice[0] for choice in TransactionType.choices]:
                        self.add_error(row_number, 'transaction_type', 'invalid_choice',
                                     f"Invalid transaction type: {transaction_type}", row)
                        continue
                    
                    # Handle category
                    category = None
                    category_name = row.get('category', '').strip()
                    if category_name:
                        category, created = TransactionCategory.objects.get_or_create(
                            company=self.company,
                            name=category_name,
                            defaults={'category_type': transaction_type}
                        )
                    
                    # Create transaction
                    Transaction.objects.create(
                        account=account,
                        amount=amount,
                        description=row['description'].strip(),
                        date=transaction_date.date(),
                        transaction_type=transaction_type,
                        category=category,
                        reference_number=row.get('reference_number', '').strip() or None,
                        tags=row.get('tags', '').strip() or None
                    )
                    
                    self.successful_rows += 1
                    
                except Exception as e:
                    self.add_error(row_number, '', 'processing_error', str(e), row)
            
            # Update bulk upload record
            bulk_upload.total_rows = total_rows
            bulk_upload.successful_rows = self.successful_rows
            bulk_upload.failed_rows = self.failed_rows
            
            if self.failed_rows == 0:
                bulk_upload.status = 'completed'
            elif self.successful_rows > 0:
                bulk_upload.status = 'partial'
            else:
                bulk_upload.status = 'failed'
            
            bulk_upload.completed_at = datetime.now()
            bulk_upload.save()
            
            # Save errors
            for error in self.errors:
                BulkUploadError.objects.create(
                    bulk_upload=bulk_upload,
                    row_number=error['row_number'],
                    field_name=error['field_name'],
                    error_type=error['error_type'],
                    error_message=error['error_message'],
                    row_data=error['row_data']
                )
        
        return self.successful_rows, self.failed_rows


class CategoryCSVProcessor(CSVProcessor):
    """Process CSV files for TransactionCategory import"""
    
    REQUIRED_FIELDS = ['name', 'category_type']
    OPTIONAL_FIELDS = ['description', 'is_active']
    
    def process_csv(self, csv_file, bulk_upload: BulkUpload) -> Tuple[int, int]:
        """Process the CSV file and create TransactionCategory objects"""
        
        # Read CSV content
        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        total_rows = 0
        
        with transaction.atomic():
            for row_number, row in enumerate(csv_reader, start=2):
                total_rows += 1
                
                # Validate required fields
                if not self.validate_required_fields(row, self.REQUIRED_FIELDS, row_number):
                    continue
                
                try:
                    # Validate category type
                    category_type = row['category_type'].lower().strip()
                    valid_types = ['income', 'expense']
                    if category_type not in valid_types:
                        self.add_error(row_number, 'category_type', 'invalid_choice',
                                     f"Invalid category type: {category_type}. Valid choices: {valid_types}", row)
                        continue
                    
                    # Check for duplicate category names within company
                    if TransactionCategory.objects.filter(company=self.company, name=row['name'].strip()).exists():
                        self.add_error(row_number, 'name', 'duplicate',
                                     f"Category with name '{row['name'].strip()}' already exists", row)
                        continue
                    
                    # Create category
                    TransactionCategory.objects.create(
                        company=self.company,
                        name=row['name'].strip(),
                        category_type=category_type,
                        description=row.get('description', '').strip() or None,
                        is_active=str(row.get('is_active', 'true')).lower() in ['true', '1', 'yes']
                    )
                    
                    self.successful_rows += 1
                    
                except Exception as e:
                    self.add_error(row_number, '', 'processing_error', str(e), row)
            
            # Update bulk upload record
            bulk_upload.total_rows = total_rows
            bulk_upload.successful_rows = self.successful_rows
            bulk_upload.failed_rows = self.failed_rows
            
            if self.failed_rows == 0:
                bulk_upload.status = 'completed'
            elif self.successful_rows > 0:
                bulk_upload.status = 'partial'
            else:
                bulk_upload.status = 'failed'
            
            bulk_upload.completed_at = datetime.now()
            bulk_upload.save()
            
            # Save errors
            for error in self.errors:
                BulkUploadError.objects.create(
                    bulk_upload=bulk_upload,
                    row_number=error['row_number'],
                    field_name=error['field_name'],
                    error_type=error['error_type'],
                    error_message=error['error_message'],
                    row_data=error['row_data']
                )
        
        return self.successful_rows, self.failed_rows


def get_csv_processor(upload_type: str, company: Company, user: User) -> CSVProcessor:
    """Factory function to get the appropriate CSV processor"""
    processors = {
        'accounts': AccountCSVProcessor,
        'transactions': TransactionCSVProcessor,
        'categories': CategoryCSVProcessor,
    }
    
    processor_class = processors.get(upload_type)
    if not processor_class:
        raise ValueError(f"Unsupported upload type: {upload_type}")
    
    return processor_class(company, user)
