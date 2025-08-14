from django.contrib import admin
from .models import (
    BankProvider, BankConnection, LinkedBankAccount,
    SyncLog, PaymentInitiation, ConsentManagement
)


@admin.register(BankProvider)
class BankProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'country_code', 'is_active', 'supports_payments']
    list_filter = ['provider_type', 'country_code', 'is_active', 'supports_payments']
    search_fields = ['name', 'provider_type']
    readonly_fields = ['created_at']


@admin.register(BankConnection)
class BankConnectionAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'company', 'provider', 'status', 'last_sync', 'created_at']
    list_filter = ['status', 'provider__provider_type', 'auto_sync_enabled']
    search_fields = ['bank_name', 'company__name']
    readonly_fields = ['created_at', 'updated_at', 'access_token', 'refresh_token']
    raw_id_fields = ['company', 'provider']


@admin.register(LinkedBankAccount)
class LinkedBankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'connection', 'account_type', 'current_balance', 'currency', 'is_active']
    list_filter = ['account_type', 'currency', 'is_active', 'sync_transactions']
    search_fields = ['account_name', 'connection__bank_name']
    readonly_fields = ['created_at', 'updated_at', 'external_account_id']
    raw_id_fields = ['connection', 'local_account']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['connection', 'sync_type', 'status', 'started_at', 'records_processed', 'records_created']
    list_filter = ['sync_type', 'status', 'started_at']
    search_fields = ['connection__bank_name']
    readonly_fields = ['id', 'started_at', 'completed_at']
    raw_id_fields = ['connection']


@admin.register(PaymentInitiation)
class PaymentInitiationAdmin(admin.ModelAdmin):
    list_display = ['recipient_name', 'amount', 'currency', 'payment_type', 'status', 'created_at']
    list_filter = ['payment_type', 'status', 'currency', 'created_at']
    search_fields = ['recipient_name', 'reference']
    readonly_fields = ['id', 'created_at', 'updated_at', 'external_payment_id']
    raw_id_fields = ['connection', 'local_transaction']


@admin.register(ConsentManagement)
class ConsentManagementAdmin(admin.ModelAdmin):
    list_display = ['connection', 'consent_type', 'status', 'granted_at', 'expires_at']
    list_filter = ['consent_type', 'status', 'granted_at']
    search_fields = ['connection__bank_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'external_consent_id']
    raw_id_fields = ['connection']
