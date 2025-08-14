from django.db import models
from django.contrib.auth.models import User
from core.models import Company, Account, Transaction
from encrypted_model_fields.fields import EncryptedTextField, EncryptedCharField
import uuid
from datetime import datetime, timedelta
from django.utils import timezone


class BankProvider(models.Model):
    """Supported bank providers for Open Banking"""
    PROVIDER_TYPES = [
        ('UK_OPEN_BANKING', 'UK Open Banking'),
        ('PSD2_EU', 'PSD2 European'),
        ('PLAID', 'Plaid (US)'),
        ('YODLEE', 'Yodlee'),
        ('SALTEDGE', 'Salt Edge'),
        ('TINK', 'Tink'),
        ('TRUELAYER', 'TrueLayer'),
        ('YAPILY', 'Yapily'),
        ('NORDIGEN', 'Nordigen'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    country_code = models.CharField(max_length=3)  # ISO country code
    base_url = models.URLField()
    api_version = models.CharField(max_length=10, default='v1')
    is_sandbox = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    supports_payments = models.BooleanField(default=False)
    supports_account_info = models.BooleanField(default=True)
    rate_limit_per_minute = models.IntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.country_code})"


class BankConnection(models.Model):
    """User's bank connection through Open Banking"""
    STATUS_CHOICES = [
        ('CONNECTING', 'Connecting'),
        ('CONNECTED', 'Connected'),
        ('EXPIRED', 'Expired'),
        ('REVOKED', 'Revoked'),
        ('ERROR', 'Error'),
        ('REFRESH_REQUIRED', 'Refresh Required'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bank_connections')
    provider = models.ForeignKey(BankProvider, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100)
    bank_logo_url = models.URLField(null=True, blank=True)
    
    # Encrypted credentials
    access_token = EncryptedTextField(null=True, blank=True)
    refresh_token = EncryptedTextField(null=True, blank=True)
    consent_id = EncryptedCharField(max_length=255, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONNECTING')
    consent_expires_at = models.DateTimeField(null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    next_sync = models.DateTimeField(null=True, blank=True)
    
    # Connection metadata
    institution_id = models.CharField(max_length=100, null=True, blank=True)
    request_id = models.CharField(max_length=100, null=True, blank=True)
    callback_url = models.URLField(null=True, blank=True)
    
    # Sync settings
    auto_sync_enabled = models.BooleanField(default=True)
    sync_frequency_hours = models.IntegerField(default=24)  # How often to sync
    include_pending = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['company', 'bank_name', 'provider']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.bank_name} - {self.company.name}"
    
    @property
    def is_expired(self):
        if not self.consent_expires_at:
            return False
        return timezone.now() > self.consent_expires_at
    
    @property
    def days_until_expiry(self):
        if not self.consent_expires_at:
            return None
        delta = self.consent_expires_at - timezone.now()
        return delta.days if delta.days > 0 else 0


class LinkedBankAccount(models.Model):
    """Bank accounts linked through Open Banking"""
    ACCOUNT_TYPES = [
        ('CURRENT', 'Current Account'),
        ('SAVINGS', 'Savings Account'),
        ('CREDIT_CARD', 'Credit Card'),
        ('LOAN', 'Loan Account'),
        ('MORTGAGE', 'Mortgage'),
        ('INVESTMENT', 'Investment Account'),
        ('PENSION', 'Pension'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(BankConnection, on_delete=models.CASCADE, related_name='linked_accounts')
    local_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='bank_link')
    
    # Bank account details
    external_account_id = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    account_number = EncryptedCharField(max_length=50, null=True, blank=True)
    sort_code = EncryptedCharField(max_length=20, null=True, blank=True)
    iban = EncryptedCharField(max_length=34, null=True, blank=True)
    bic = EncryptedCharField(max_length=11, null=True, blank=True)
    
    # Balance information
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Sync settings
    is_active = models.BooleanField(default=True)
    sync_transactions = models.BooleanField(default=True)
    last_transaction_sync = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['connection', 'external_account_id']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.account_name} - {self.connection.bank_name}"


class SyncLog(models.Model):
    """Log of synchronization attempts"""
    SYNC_TYPES = [
        ('ACCOUNTS', 'Accounts'),
        ('TRANSACTIONS', 'Transactions'),
        ('BALANCES', 'Balances'),
        ('FULL', 'Full Sync'),
    ]
    
    STATUS_CHOICES = [
        ('STARTED', 'Started'),
        ('SUCCESS', 'Success'),
        ('PARTIAL', 'Partial Success'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(BankConnection, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='STARTED')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Sync results
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    
    error_message = models.TextField(null=True, blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.sync_type} - {self.connection} - {self.status}"


class PaymentInitiation(models.Model):
    """Payment initiation through Open Banking"""
    PAYMENT_TYPES = [
        ('SINGLE', 'Single Payment'),
        ('BULK', 'Bulk Payment'),
        ('STANDING_ORDER', 'Standing Order'),
        ('SCHEDULED', 'Scheduled Payment'),
    ]
    
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('AUTHORIZED', 'Authorized'),
        ('EXECUTED', 'Executed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(BankConnection, on_delete=models.CASCADE, related_name='payments')
    local_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='INITIATED')
    
    # Payment details
    external_payment_id = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    reference = models.CharField(max_length=100, null=True, blank=True)
    
    # Recipient details
    recipient_name = models.CharField(max_length=100)
    recipient_account = EncryptedCharField(max_length=50)
    recipient_sort_code = EncryptedCharField(max_length=20, null=True, blank=True)
    recipient_iban = EncryptedCharField(max_length=34, null=True, blank=True)
    
    # Timing
    requested_execution_date = models.DateField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.amount} {self.currency} to {self.recipient_name}"


class ConsentManagement(models.Model):
    """Manage user consents for data access"""
    CONSENT_TYPES = [
        ('ACCOUNT_INFO', 'Account Information'),
        ('PAYMENT_INITIATION', 'Payment Initiation'),
        ('TRANSACTION_HISTORY', 'Transaction History'),
        ('BALANCE_CHECK', 'Balance Check'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('GRANTED', 'Granted'),
        ('EXPIRED', 'Expired'),
        ('REVOKED', 'Revoked'),
        ('REJECTED', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(BankConnection, on_delete=models.CASCADE, related_name='consents')
    consent_type = models.CharField(max_length=20, choices=CONSENT_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    external_consent_id = models.CharField(max_length=100, null=True, blank=True)
    consent_url = models.URLField(null=True, blank=True)
    
    granted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    # Consent details
    permissions = models.JSONField(default=list)
    restrictions = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['connection', 'consent_type']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.consent_type} - {self.connection} - {self.status}"
