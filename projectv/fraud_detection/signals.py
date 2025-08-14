from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Transaction
from .ai_engine import fraud_engine
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def analyze_transaction_for_fraud(sender, instance, created, **kwargs):
    """Automatically analyze new transactions for fraud"""
    if created and instance.status == 'completed':
        try:
            # Run fraud analysis asynchronously (in production, use Celery)
            fraud_engine.analyze_transaction(instance)
        except Exception as e:
            logger.error(f"Fraud analysis failed for transaction {instance.id}: {str(e)}")
