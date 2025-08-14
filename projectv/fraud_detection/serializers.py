from rest_framework import serializers
from .models import (
    FraudDetectionRule, FraudAlert, FraudInvestigation,
    WhitelistEntry, FraudMetrics, BehavioralProfile
)
from core.serializers import TransactionSerializer


class FraudDetectionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudDetectionRule
        fields = [
            'id', 'name', 'rule_type', 'severity', 'parameters', 'thresholds',
            'is_active', 'auto_block', 'model_version', 'model_accuracy',
            'last_trained', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FraudAlertSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer(read_only=True)
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    
    class Meta:
        model = FraudAlert
        fields = [
            'id', 'transaction', 'rule_name', 'status', 'risk_score', 'confidence_score',
            'alert_reason', 'anomaly_factors', 'risk_indicators', 'assigned_to',
            'investigated_at', 'resolution_notes', 'transaction_blocked',
            'customer_notified', 'escalated', 'created_at', 'resolved_at'
        ]
        read_only_fields = [
            'id', 'risk_score', 'confidence_score', 'alert_reason',
            'anomaly_factors', 'risk_indicators', 'created_at'
        ]


class FraudInvestigationSerializer(serializers.ModelSerializer):
    alert = FraudAlertSerializer(read_only=True)
    investigator_name = serializers.CharField(source='investigator.username', read_only=True)
    
    class Meta:
        model = FraudInvestigation
        fields = [
            'id', 'alert', 'case_number', 'status', 'priority', 'investigator',
            'investigator_name', 'investigation_notes', 'evidence_collected',
            'external_references', 'created_at', 'assigned_at', 'first_response_at',
            'closed_at', 'resolution_summary', 'actions_taken', 'lessons_learned'
        ]
        read_only_fields = [
            'id', 'case_number', 'created_at', 'assigned_at', 'first_response_at', 'closed_at'
        ]


class WhitelistEntrySerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(source='added_by.username', read_only=True)
    
    class Meta:
        model = WhitelistEntry
        fields = [
            'id', 'entity_type', 'entity_value', 'entity_details', 'reason',
            'added_by', 'added_by_name', 'is_active', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'added_by', 'created_at']


class FraudMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudMetrics
        fields = [
            'id', 'date', 'total_transactions', 'flagged_transactions',
            'confirmed_fraud', 'false_positives', 'avg_risk_score',
            'high_risk_count', 'blocked_transactions', 'fraud_amount_detected',
            'fraud_amount_prevented', 'false_positive_amount', 'model_accuracy',
            'detection_rate', 'false_positive_rate', 'created_at'
        ]
        read_only_fields = '__all__'


class BehavioralProfileSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    
    class Meta:
        model = BehavioralProfile
        fields = [
            'id', 'account', 'account_name', 'avg_transaction_amount',
            'std_transaction_amount', 'typical_transaction_times',
            'typical_transaction_days', 'frequent_merchants', 'typical_categories',
            'geographical_patterns', 'max_daily_amount', 'max_daily_count',
            'avg_time_between_transactions', 'risk_indicators', 'anomaly_threshold',
            'last_updated', 'created_at'
        ]
        read_only_fields = '__all__'
