from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from core.models import Transaction, Company
from ai_insights.models import AIAnalysisLog
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def auto_analyze_transaction(sender, instance, created, **kwargs):
    """
    Automatically analyze new transactions with AI:
    - Categorize if uncategorized
    - Detect anomalies
    - Log analysis results
    """
    if not created or not getattr(settings, 'AI_AUTO_ANALYSIS', True):
        return
        
    try:
        from ai_insights.ai_analyzer import ai_analyzer
        
        # Create analysis log
        log_entry = AIAnalysisLog.objects.create(
            company=instance.company,
            operation_type='CATEGORIZATION',
            status='SUCCESS',
            processing_time=0,
            metadata={'transaction_id': instance.id, 'auto_processed': True}
        )
        
        # Auto-categorize if no category assigned
        if not instance.category:
            logger.info(f"Auto-categorizing transaction {instance.id}")
            categorization = ai_analyzer.categorize_transaction(instance)
            
            # Auto-accept high confidence suggestions
            confidence_threshold = getattr(settings, 'AI_CONFIDENCE_THRESHOLD', 0.8)
            if (categorization and 
                categorization.confidence_score >= confidence_threshold and
                categorization.suggested_category):
                
                instance.category = categorization.suggested_category
                instance.save(update_fields=['category'])
                
                categorization.is_accepted = True
                categorization.save()
                
                logger.info(f"Auto-accepted categorization for transaction {instance.id}")
        
        # Auto-detect anomalies for all new transactions
        logger.info(f"Auto-analyzing transaction {instance.id} for anomalies")
        anomaly = ai_analyzer.detect_anomaly(instance)
        
        if anomaly and anomaly.risk_level in ['HIGH', 'CRITICAL']:
            instance.is_anomaly = True
            instance.save(update_fields=['is_anomaly'])
            logger.warning(f"Flagged transaction {instance.id} as anomaly: {anomaly.anomaly_type}")
            
    except Exception as e:
        logger.error(f"Error in auto-analysis for transaction {instance.id}: {e}")
        # Update log entry with error
        try:
            log_entry.status = 'FAILED'
            log_entry.error_message = str(e)
            log_entry.save()
        except:
            pass


@receiver(post_save, sender=Transaction)
def update_financial_health_score(sender, instance, created, **kwargs):
    """
    Update financial health score when significant transactions occur
    """
    if not created or not getattr(settings, 'AI_AUTO_HEALTH_SCORING', True):
        return
        
    try:
        from ai_insights.ai_analyzer import ai_analyzer
        from django.utils import timezone
        from datetime import timedelta
        
        # Only update for larger transactions to avoid too frequent updates
        transaction_amount = float(instance.amount)
        amount_threshold = getattr(settings, 'HEALTH_SCORE_THRESHOLD', 1000)
        
        if abs(transaction_amount) >= amount_threshold:
            # Check if we updated recently (avoid spam)
            recent_update = instance.company.health_scores.filter(
                calculated_at__gte=timezone.now() - timedelta(hours=1)
            ).exists()
            
            if not recent_update:
                logger.info(f"Updating health score for company {instance.company.id} due to large transaction")
                ai_analyzer.calculate_financial_health_score(instance.company.id)
                
    except Exception as e:
        logger.error(f"Error updating health score for company {instance.company.id}: {e}")


@receiver(post_save, sender=Company)
def setup_default_categories(sender, instance, created, **kwargs):
    """
    Create default transaction categories when a new company is created
    """
    if not created:
        return
        
    from core.models import TransactionCategory
    
    # Default categories for business
    default_categories = [
        # Income Categories
        ('Sales Revenue', True, '#4CAF50'),
        ('Service Revenue', True, '#8BC34A'),
        ('Interest Income', True, '#CDDC39'),
        ('Other Income', True, '#FFC107'),
        
        # Expense Categories
        ('Office Supplies', False, '#FF5722'),
        ('Marketing & Advertising', False, '#E91E63'),
        ('Software & Subscriptions', False, '#9C27B0'),
        ('Travel & Meals', False, '#673AB7'),
        ('Utilities', False, '#3F51B5'),
        ('Rent & Facilities', False, '#2196F3'),
        ('Professional Services', False, '#00BCD4'),
        ('Insurance', False, '#009688'),
        ('Equipment & Hardware', False, '#795548'),
        ('Bank Fees', False, '#607D8B'),
        ('Taxes', False, '#FF9800'),
        ('Other Expenses', False, '#F44336'),
    ]
    
    try:
        for name, is_income, color in default_categories:
            TransactionCategory.objects.get_or_create(
                company=instance,
                name=name,
                defaults={
                    'is_income': is_income,
                    'color': color,
                    'is_active': True
                }
            )
        
        logger.info(f"Created default categories for company {instance.name}")
        
    except Exception as e:
        logger.error(f"Failed to create default categories for company {instance.id}: {e}")
