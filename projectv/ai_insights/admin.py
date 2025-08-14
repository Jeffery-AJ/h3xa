from django.contrib import admin
from ai_insights.models import (
    FinancialHealthScore, AnomalyDetection, SmartCategorization,
    BudgetInsight, FinancialGoalRecommendation, AIAnalysisLog
)


@admin.register(FinancialHealthScore)
class FinancialHealthScoreAdmin(admin.ModelAdmin):
    list_display = ['company', 'score', 'risk_level', 'calculated_at']
    list_filter = ['risk_level', 'calculated_at', 'company']
    search_fields = ['company__name']
    readonly_fields = ['calculated_at']
    ordering = ['-calculated_at']


@admin.register(AnomalyDetection)
class AnomalyDetectionAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'anomaly_type', 'risk_level', 'confidence_score', 'is_false_positive', 'detected_at']
    list_filter = ['anomaly_type', 'risk_level', 'is_false_positive', 'detected_at']
    search_fields = ['transaction__description', 'explanation']
    readonly_fields = ['detected_at']
    ordering = ['-detected_at']


@admin.register(SmartCategorization)
class SmartCategorizationAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'suggested_category', 'confidence_score', 'is_accepted', 'created_at']
    list_filter = ['suggested_category', 'is_accepted', 'created_at']
    search_fields = ['transaction__description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(BudgetInsight)
class BudgetInsightAdmin(admin.ModelAdmin):
    list_display = ['company', 'budget', 'insight_type', 'severity', 'is_read', 'created_at']
    list_filter = ['insight_type', 'severity', 'is_read', 'created_at']
    search_fields = ['company__name', 'budget__name', 'title']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(FinancialGoalRecommendation)
class FinancialGoalRecommendationAdmin(admin.ModelAdmin):
    list_display = ['company', 'goal_type', 'target_amount', 'timeframe_months', 'is_accepted', 'created_at']
    list_filter = ['goal_type', 'is_accepted', 'created_at']
    search_fields = ['company__name', 'name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(AIAnalysisLog)
class AIAnalysisLogAdmin(admin.ModelAdmin):
    list_display = ['company', 'operation_type', 'status', 'created_at']
    list_filter = ['operation_type', 'status', 'created_at']
    search_fields = ['company__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
