from rest_framework import serializers
from .models import (
    BankProvider, BankConnection, LinkedBankAccount, 
    SyncLog, PaymentInitiation, ConsentManagement
)
from core.serializers import AccountSerializer


class BankProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankProvider
        fields = [
            'id', 'name', 'provider_type', 'country_code', 
            'is_sandbox', 'supports_payments', 'supports_account_info'
        ]
        read_only_fields = ['id']


class BankConnectionSerializer(serializers.ModelSerializer):
    provider = BankProviderSerializer(read_only=True)
    provider_id = serializers.UUIDField(write_only=True)
    days_until_expiry = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = BankConnection
        fields = [
            'id', 'provider', 'provider_id', 'bank_name', 'bank_logo_url',
            'status', 'consent_expires_at', 'last_sync', 'next_sync',
            'auto_sync_enabled', 'sync_frequency_hours', 'include_pending',
            'days_until_expiry', 'is_expired', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'consent_expires_at', 'last_sync', 'next_sync', 'created_at'
        ]


class LinkedBankAccountSerializer(serializers.ModelSerializer):
    connection = BankConnectionSerializer(read_only=True)
    local_account = AccountSerializer(read_only=True)
    
    class Meta:
        model = LinkedBankAccount
        fields = [
            'id', 'connection', 'local_account', 'account_name', 'account_type',
            'current_balance', 'available_balance', 'credit_limit', 'currency',
            'is_active', 'sync_transactions', 'last_transaction_sync', 'created_at'
        ]
        read_only_fields = [
            'id', 'current_balance', 'available_balance', 'last_transaction_sync', 'created_at'
        ]


class SyncLogSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = SyncLog
        fields = [
            'id', 'sync_type', 'status', 'started_at', 'completed_at',
            'records_processed', 'records_created', 'records_updated', 'records_failed',
            'error_message', 'duration_seconds'
        ]
        read_only_fields = '__all__'
    
    def get_duration_seconds(self, obj):
        if obj.completed_at and obj.started_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class PaymentInitiationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInitiation
        fields = [
            'id', 'payment_type', 'status', 'amount', 'currency', 'reference',
            'recipient_name', 'requested_execution_date', 'executed_at', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'executed_at', 'created_at']


class ConsentManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentManagement
        fields = [
            'id', 'consent_type', 'status', 'granted_at', 'expires_at',
            'permissions', 'restrictions', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'granted_at', 'expires_at', 'created_at'
        ]


class BankConnectionCreateSerializer(serializers.Serializer):
    """Serializer for initiating bank connection"""
    provider_id = serializers.UUIDField()
    institution_id = serializers.CharField(max_length=100, required=False)
    callback_url = serializers.URLField(required=False)
    permissions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['ReadAccountsBasic', 'ReadTransactionsBasic', 'ReadBalances']
    )


class PaymentRequestSerializer(serializers.Serializer):
    """Serializer for payment initiation request"""
    connection_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    recipient_name = serializers.CharField(max_length=100)
    recipient_account = serializers.CharField(max_length=50)
    recipient_sort_code = serializers.CharField(max_length=20, required=False)
    recipient_iban = serializers.CharField(max_length=34, required=False)
    reference = serializers.CharField(max_length=100, required=False)
    requested_execution_date = serializers.DateField(required=False)
    payment_type = serializers.ChoiceField(
        choices=PaymentInitiation.PAYMENT_TYPES,
        default='SINGLE'
    )
