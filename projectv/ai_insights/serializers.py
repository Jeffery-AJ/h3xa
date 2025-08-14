from rest_framework import serializers
from ai_insights.models import (
    FinancialHealthScore, AnomalyDetection, SmartCategorization,
    BudgetInsight, FinancialGoalRecommendation, AIAnalysisLog
)
from core.serializers import TransactionSerializer, TransactionCategorySerializer


class FinancialHealthScoreSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = FinancialHealthScore
        fields = [
            'id', 'company', 'company_name', 'score', 'factors', 
            'recommendations', 'strengths', 'concerns', 'risk_level', 
            'calculated_at'
        ]
        read_only_fields = ['calculated_at']


class AnomalyDetectionSerializer(serializers.ModelSerializer):
    transaction_detail = TransactionSerializer(source='transaction', read_only=True)
    
    class Meta:
        model = AnomalyDetection
        fields = [
            'id', 'transaction', 'transaction_detail', 'anomaly_type', 
            'confidence_score', 'risk_level', 'explanation', 'detected_at',
            'is_false_positive', 'reviewed_by', 'notes'
        ]
        read_only_fields = ['detected_at']


class SmartCategorizationSerializer(serializers.ModelSerializer):
    transaction_detail = TransactionSerializer(source='transaction', read_only=True)
    suggested_category_detail = TransactionCategorySerializer(source='suggested_category', read_only=True)
    
    class Meta:
        model = SmartCategorization
        fields = [
            'id', 'transaction', 'transaction_detail', 'suggested_category',
            'suggested_category_detail', 'confidence_score', 'reasoning',
            'is_accepted', 'accepted_by', 'created_at'
        ]
        read_only_fields = ['created_at']


class BudgetInsightSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    budget_name = serializers.CharField(source='budget.name', read_only=True)
    
    class Meta:
        model = BudgetInsight
        fields = [
            'id', 'company', 'company_name', 'budget', 'budget_name',
            'insight_type', 'severity', 'title', 'message', 'recommended_action',
            'impact_score', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']


class FinancialGoalRecommendationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = FinancialGoalRecommendation
        fields = [
            'id', 'company', 'company_name', 'goal_type', 'name', 'description',
            'target_amount', 'timeframe_months', 'why_important', 'confidence_score',
            'is_accepted', 'accepted_by', 'created_at'
        ]
        read_only_fields = ['created_at']


class AIAnalysisLogSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = AIAnalysisLog
        fields = [
            'id', 'company', 'company_name', 'operation_type', 'status',
            'processing_time', 'tokens_used', 'error_message', 'metadata',
            'created_at'
        ]
        read_only_fields = ['created_at']


# Quick insight serializers for dashboard
class QuickHealthInsightSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    risk_level = serializers.CharField()
    key_insight = serializers.CharField()
    recommendation = serializers.CharField()


class QuickAnomalySerializer(serializers.Serializer):
    count = serializers.IntegerField()
    high_risk_count = serializers.IntegerField()
    latest_anomaly = serializers.CharField()


class AIDashboardSerializer(serializers.Serializer):
    """Comprehensive AI insights for dashboard"""
    health_score = QuickHealthInsightSerializer()
    anomalies = QuickAnomalySerializer()
    categorization_accuracy = serializers.FloatField()
    budget_alerts = serializers.IntegerField()
    goal_recommendations = serializers.IntegerField()
    last_analysis = serializers.DateTimeField()
