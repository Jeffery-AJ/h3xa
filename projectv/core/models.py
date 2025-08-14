from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class Company(models.Model):
    """Company/Business entity that owns financial accounts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    tax_id = models.CharField(max_length=50, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    founded_date = models.DateField(null=True, blank=True)
    employees_count = models.PositiveIntegerField(null=True, blank=True)
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')  # ISO currency code
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class AccountType(models.TextChoices):
    """Types of financial accounts"""
    CHECKING = 'checking', 'Checking Account'
    SAVINGS = 'savings', 'Savings Account'
    CREDIT_CARD = 'credit_card', 'Credit Card'
    LOAN = 'loan', 'Loan Account'
    INVESTMENT = 'investment', 'Investment Account'
    CASH = 'cash', 'Cash Account'
    PAYPAL = 'paypal', 'PayPal'
    STRIPE = 'stripe', 'Stripe'
    OTHER = 'other', 'Other'


class Account(models.Model):
    """Financial accounts (bank accounts, credit cards, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['company', 'account_number']

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    @property
    def available_balance(self):
        """Calculate available balance considering credit limit"""
        if self.account_type == AccountType.CREDIT_CARD and self.credit_limit:
            return self.credit_limit + self.current_balance  # current_balance is negative for credit cards
        return self.current_balance


class TransactionCategory(models.Model):
    """Categories for transactions (Income, Expenses, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    color = models.CharField(max_length=7, default='#3498db')  # Hex color code
    icon = models.CharField(max_length=50, null=True, blank=True)
    is_income = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Transaction Categories"
        unique_together = ['company', 'name', 'parent']
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class TransactionType(models.TextChoices):
    """Types of transactions"""
    INCOME = 'income', 'Income'
    EXPENSE = 'expense', 'Expense'
    TRANSFER = 'transfer', 'Transfer'
    ADJUSTMENT = 'adjustment', 'Adjustment'


class TransactionStatus(models.TextChoices):
    """Status of transactions"""
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    FAILED = 'failed', 'Failed'


class Transaction(models.Model):
    """Financial transactions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name='incoming_transfers')
    
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField()
    reference_number = models.CharField(max_length=100, null=True, blank=True)
    
    transaction_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.COMPLETED)
    
    # External integration fields
    external_id = models.CharField(max_length=100, null=True, blank=True)
    external_source = models.CharField(max_length=50, null=True, blank=True)  # 'bank_api', 'stripe', 'manual', etc.
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # AI/ML flags
    is_anomaly = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, 
                                         validators=[MinValueValidator(0), MaxValueValidator(1)])

    class Meta:
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['company', 'transaction_date']),
            models.Index(fields=['account', 'transaction_date']),
            models.Index(fields=['category', 'transaction_date']),
            models.Index(fields=['transaction_type', 'transaction_date']),
        ]

    def __str__(self):
        return f"{self.transaction_type.title()}: {self.amount} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        """Update account balance when transaction is saved"""
        # This logic is complex and can cause issues with get_or_create.
        # It's better to handle balance updates in a separate process
        # or signal handler after the transaction is reliably saved.
        super().save(*args, **kwargs)

    def _update_account_balances(self, old_instance=None):
        """Update account balances based on transaction"""
        if self.status != TransactionStatus.COMPLETED:
            return
            
        # Revert old transaction if updating
        if old_instance and old_instance.status == TransactionStatus.COMPLETED:
            self._revert_balance_change(old_instance)
        
        # Apply new transaction
        if self.transaction_type == TransactionType.INCOME:
            self.account.current_balance += self.amount
        elif self.transaction_type == TransactionType.EXPENSE:
            self.account.current_balance -= self.amount
        elif self.transaction_type == TransactionType.TRANSFER and self.to_account:
            self.account.current_balance -= self.amount
            self.to_account.current_balance += self.amount
            self.to_account.save()
        
        self.account.save()

    def _revert_balance_change(self, old_instance):
        """Revert the balance change from the old transaction"""
        if old_instance.transaction_type == TransactionType.INCOME:
            self.account.current_balance -= old_instance.amount
        elif old_instance.transaction_type == TransactionType.EXPENSE:
            self.account.current_balance += old_instance.amount
        elif old_instance.transaction_type == TransactionType.TRANSFER and old_instance.to_account:
            self.account.current_balance += old_instance.amount
            old_instance.to_account.current_balance -= old_instance.amount
            old_instance.to_account.save()


class Budget(models.Model):
    """Budget planning and tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=100)
    category = models.ForeignKey(TransactionCategory, on_delete=models.CASCADE, null=True, blank=True)
    
    budgeted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    @property
    def remaining_amount(self):
        return self.budgeted_amount - self.spent_amount

    @property
    def percentage_used(self):
        if self.budgeted_amount == 0:
            return 0
        return (self.spent_amount / self.budgeted_amount) * 100


class FinancialGoal(models.Model):
    """Financial goals and targets"""
    GOAL_TYPES = [
        ('revenue', 'Revenue Target'),
        ('profit', 'Profit Target'),
        ('expense_reduction', 'Expense Reduction'),
        ('cash_flow', 'Cash Flow Target'),
        ('savings', 'Savings Goal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='financial_goals')
    name = models.CharField(max_length=100)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    target_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_achieved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-target_date']

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    @property
    def progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return min((self.current_amount / self.target_amount) * 100, 100)


class BulkUploadStatus(models.TextChoices):
    """Status of bulk upload operations"""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    PARTIAL = 'partial', 'Partial Success'


class BulkUpload(models.Model):
    """Track bulk upload operations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bulk_uploads')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bulk_uploads')
    upload_type = models.CharField(max_length=20, choices=[
        ('accounts', 'Accounts'),
        ('transactions', 'Transactions'),
        ('categories', 'Categories'),
        ('budgets', 'Budgets'),
        ('goals', 'Financial Goals')
    ])
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # Size in bytes
    status = models.CharField(max_length=20, choices=BulkUploadStatus.choices, default=BulkUploadStatus.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    processing_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.upload_type.title()} Upload - {self.file_name} ({self.status})"

    @property
    def success_rate(self):
        if self.total_rows == 0:
            return 0
        return (self.successful_rows / self.total_rows) * 100


class BulkUploadError(models.Model):
    """Individual errors from bulk upload operations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bulk_upload = models.ForeignKey(BulkUpload, on_delete=models.CASCADE, related_name='errors')
    row_number = models.PositiveIntegerField()
    field_name = models.CharField(max_length=100, blank=True)
    error_type = models.CharField(max_length=50)  # validation, duplicate, missing_field, etc.
    error_message = models.TextField()
    row_data = models.JSONField()  # Store the problematic row data
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"Row {self.row_number}: {self.error_type}"
