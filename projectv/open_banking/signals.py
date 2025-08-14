from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import BankConnection, LinkedBankAccount, SyncLog
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BankConnection)
def schedule_next_sync(sender, instance, created, **kwargs):
    """Schedule next sync when connection is created or updated"""
    if instance.status == 'CONNECTED' and instance.auto_sync_enabled:
        instance.next_sync = timezone.now() + timedelta(hours=instance.sync_frequency_hours)
        # Use update to avoid infinite recursion
        BankConnection.objects.filter(id=instance.id).update(next_sync=instance.next_sync)


@receiver(post_save, sender=LinkedBankAccount)
def update_local_account_balance(sender, instance, created, **kwargs):
    """Update local account balance when linked account balance changes"""
    if instance.local_account and not created:
        # Check if balance changed
        old_instance = LinkedBankAccount.objects.filter(id=instance.id).first()
        if old_instance and old_instance.current_balance != instance.current_balance:
            instance.local_account.current_balance = instance.current_balance
            instance.local_account.save()


@receiver(post_save, sender=SyncLog)
def update_connection_sync_status(sender, instance, created, **kwargs):
    """Update connection last sync when sync log is completed"""
    if instance.status in ['SUCCESS', 'PARTIAL', 'FAILED'] and instance.completed_at:
        connection = instance.connection
        connection.last_sync = instance.completed_at
        
        # Schedule next sync if auto sync is enabled
        if connection.auto_sync_enabled and instance.status in ['SUCCESS', 'PARTIAL']:
            connection.next_sync = instance.completed_at + timedelta(
                hours=connection.sync_frequency_hours
            )
        
        connection.save()


@receiver(pre_delete, sender=BankConnection)
def cleanup_connection_data(sender, instance, **kwargs):
    """Clean up related data when connection is deleted"""
    logger.info(f"Cleaning up data for deleted connection: {instance.id}")
    
    # Deactivate linked accounts
    instance.linked_accounts.update(is_active=False, sync_transactions=False)
    
    # Mark local accounts as disconnected
    for linked_account in instance.linked_accounts.all():
        if linked_account.local_account:
            linked_account.local_account.metadata = linked_account.local_account.metadata or {}
            linked_account.local_account.metadata['bank_connection_deleted'] = True
            linked_account.local_account.save()
