from django.db import models
from core.models import Company, Transaction, Account, TransactionCategory
from django.contrib.auth import get_user_model

User = get_user_model()


class FinancialHealthScore(models.Model):
    """AI-calculated financial health scores for companies"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='health_scores')
    score = models.IntegerField(help_text="Score from 0-100")
    factors = models.JSONField(help_text="Breakdown of score factors")
    recommendations = models.JSONField(help_text="AI-generated recommendations")
    strengths = models.JSONField(default=list, help_text="Financial strengths identified")
    concerns = models.JSONField(default=list, help_text="Areas of concern")
    risk_level = models.CharField(max_length=10, choices=[
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
    ], default='MEDIUM')
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-calculated_at']
        get_latest_by = 'calculated_at'
    
    def __str__(self):
        return f"{self.company.name} - Health Score: {self.score}"


class PredictionModel(models.Model):
    """ML model data for financial predictions"""
    PREDICTION_TYPES = [
        ('CASH_FLOW', 'Cash Flow'),
        ('REVENUE', 'Revenue'),
        ('EXPENSES', 'Expenses'),
        ('BUDGET_BURN', 'Budget Burn Rate'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    prediction_type = models.CharField(max_length=20, choices=PREDICTION_TYPES)
    model_data = models.JSONField(help_text="Trained model parameters")
    accuracy_score = models.FloatField(help_text="Model accuracy score 0-1")
    predictions = models.JSONField(help_text="Future predictions data")
    last_trained = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'prediction_type']
    
    def __str__(self):
        return f"{self.company.name} - {self.prediction_type} Model"


class AnomalyDetection(models.Model):
    """AI-detected transaction anomalies"""
    ANOMALY_TYPES = [
        ('AMOUNT_UNUSUAL', 'Unusual Amount'),
        ('MERCHANT_UNKNOWN', 'Unknown Merchant'),
        ('TIME_UNUSUAL', 'Unusual Timing'),
        ('FREQUENCY_HIGH', 'High Frequency'),
        ('PATTERN_BREAK', 'Pattern Break'),
        ('FRAUD_RISK', 'Fraud Risk'),
    ]
    
    RISK_LEVELS = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]
    
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='anomaly_data')
    anomaly_type = models.CharField(max_length=20, choices=ANOMALY_TYPES)
    confidence_score = models.FloatField(help_text="Confidence score 0-1")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS)
    explanation = models.TextField(help_text="AI explanation of the anomaly")
    detected_at = models.DateTimeField(auto_now_add=True)
    is_false_positive = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"Anomaly: {self.transaction.description} - {self.anomaly_type}"


class SmartCategorization(models.Model):
    """AI-suggested transaction categorizations"""
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='ai_categorization')
    suggested_category = models.ForeignKey(TransactionCategory, on_delete=models.CASCADE)
    confidence_score = models.FloatField(help_text="Confidence score 0-1")
    reasoning = models.TextField(help_text="AI reasoning for categorization")
    is_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Category: {self.transaction.description} -> {self.suggested_category.name}"


class BudgetInsight(models.Model):
    """AI-generated budget insights and recommendations"""
    INSIGHT_TYPES = [
        ('OVERSPEND', 'Overspending Alert'),
        ('UNDERSPEND', 'Underspending Notice'),
        ('TREND', 'Spending Trend'),
        ('OPTIMIZATION', 'Optimization Opportunity'),
        ('FORECAST', 'Budget Forecast'),
    ]
    
    SEVERITY_LEVELS = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='budget_insights')
    budget = models.ForeignKey('core.Budget', on_delete=models.CASCADE, related_name='ai_insights', null=True, blank=True)
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    title = models.CharField(max_length=200)
    message = models.TextField(help_text="Human-readable insight message")
    recommended_action = models.TextField(help_text="What user should do")
    impact_score = models.FloatField(help_text="Impact score 0-1", default=0.5)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.title}"


class FinancialGoalRecommendation(models.Model):
    """AI-recommended financial goals"""
    GOAL_TYPES = [
        ('SAVINGS', 'Savings Goal'),
        ('REVENUE', 'Revenue Target'),
        ('EXPENSE_REDUCTION', 'Expense Reduction'),
        ('EMERGENCY_FUND', 'Emergency Fund'),
        ('INVESTMENT', 'Investment Goal'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ai_goal_recommendations')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField()
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    timeframe_months = models.IntegerField(help_text="Recommended timeframe in months")
    why_important = models.TextField(help_text="AI explanation of importance")
    confidence_score = models.FloatField(help_text="AI confidence in recommendation")
    is_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"


class AIAnalysisLog(models.Model):
    """Log of AI analysis operations"""
    OPERATION_TYPES = [
        ('CATEGORIZATION', 'Transaction Categorization'),
        ('ANOMALY_DETECTION', 'Anomaly Detection'),
        ('HEALTH_SCORING', 'Financial Health Scoring'),
        ('BUDGET_INSIGHTS', 'Budget Insights'),
        ('GOAL_RECOMMENDATION', 'Goal Recommendation'),
        ('PREDICTION', 'Financial Prediction'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    operation_type = models.CharField(max_length=25, choices=OPERATION_TYPES)
    status = models.CharField(max_length=20, choices=[
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial Success'),
    ])
    processing_time = models.FloatField(help_text="Processing time in seconds")
    tokens_used = models.IntegerField(default=0, help_text="OpenAI tokens used")
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, help_text="Additional operation data")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.operation_type} - {self.status} - {self.created_at}"
