from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models
from datetime import timedelta
import logging

from .models import (
    FraudDetectionRule, FraudAlert, FraudInvestigation,
    WhitelistEntry, FraudMetrics, BehavioralProfile
)
from .serializers import (
    FraudDetectionRuleSerializer, FraudAlertSerializer,
    FraudInvestigationSerializer, WhitelistEntrySerializer,
    FraudMetricsSerializer, BehavioralProfileSerializer
)
from .ai_engine import fraud_engine
from core.permissions import IsCompanyOwner
from core.models import Transaction

logger = logging.getLogger(__name__)


class FraudDetectionRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for fraud detection rules"""
    serializer_class = FraudDetectionRuleSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule_type', 'severity', 'is_active']

    def get_queryset(self):
        return FraudDetectionRule.objects.filter(
            company__owner=self.request.user
        )

    def perform_create(self, serializer):
        company = self.request.user.companies.first()
        if not company:
            raise ValueError("User must have a company")
        serializer.save(company=company)

    @action(detail=True, methods=['post'])
    def test_rule(self, request, pk=None):
        """Test a rule against recent transactions"""
        rule = self.get_object()
        
        # Get recent transactions to test against
        recent_transactions = Transaction.objects.filter(
            company=rule.company,
            transaction_date__gte=timezone.now() - timedelta(days=7)
        )[:100]  # Limit to 100 transactions
        
        test_results = []
        matches = 0
        
        for transaction in recent_transactions:
            try:
                profile = fraud_engine._get_behavioral_profile(transaction.account)
                result = fraud_engine._evaluate_rule(rule, transaction, profile)
                
                if result['triggered']:
                    matches += 1
                    test_results.append({
                        'transaction_id': str(transaction.id),
                        'amount': float(transaction.amount),
                        'date': transaction.transaction_date.isoformat(),
                        'score': result['score'],
                        'reason': result['reason'],
                        'factors': result['factors']
                    })
                    
            except Exception as e:
                logger.error(f"Error testing rule on transaction {transaction.id}: {str(e)}")
        
        return Response({
            'rule_name': rule.name,
            'transactions_tested': len(recent_transactions),
            'matches_found': matches,
            'match_rate': (matches / len(recent_transactions) * 100) if recent_transactions else 0,
            'sample_matches': test_results[:10]  # Return first 10 matches
        })

    @action(detail=False, methods=['get'])
    def rule_templates(self, request):
        """Get predefined rule templates"""
        templates = [
            {
                'name': 'High Velocity Detection',
                'rule_type': 'VELOCITY',
                'severity': 'HIGH',
                'parameters': {
                    'time_window_hours': 24,
                },
                'thresholds': {
                    'max_amount_per_window': 10000,
                    'max_transactions_per_window': 20
                }
            },
            {
                'name': 'Large Amount Anomaly',
                'rule_type': 'AMOUNT_ANOMALY',
                'severity': 'MEDIUM',
                'parameters': {},
                'thresholds': {
                    'anomaly_multiplier': 3.0,
                    'min_amount': 1000
                }
            },
            {
                'name': 'Unusual Time Detection',
                'rule_type': 'TIME_ANOMALY',
                'severity': 'LOW',
                'parameters': {},
                'thresholds': {}
            }
        ]
        return Response({'templates': templates})


class FraudAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for fraud alerts"""
    serializer_class = FraudAlertSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'risk_score', 'transaction_blocked']

    def get_queryset(self):
        return FraudAlert.objects.filter(
            company__owner=self.request.user
        ).select_related('transaction', 'rule')

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a fraud alert"""
        alert = self.get_object()
        resolution = request.data.get('resolution')  # 'fraud', 'legitimate', 'false_positive'
        notes = request.data.get('notes', '')
        
        if resolution not in ['fraud', 'legitimate', 'false_positive']:
            return Response(
                {'error': 'Invalid resolution. Must be fraud, legitimate, or false_positive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update alert status
        status_mapping = {
            'fraud': 'RESOLVED_FRAUD',
            'legitimate': 'RESOLVED_LEGITIMATE',
            'false_positive': 'FALSE_POSITIVE'
        }
        
        alert.status = status_mapping[resolution]
        alert.resolution_notes = notes
        alert.resolved_at = timezone.now()
        alert.save()
        
        # Create investigation if it's confirmed fraud
        if resolution == 'fraud' and not hasattr(alert, 'investigation'):
            from .models import FraudInvestigation
            investigation = FraudInvestigation.objects.create(
                company=alert.company,
                alert=alert,
                case_number=f"INV-{timezone.now().strftime('%Y%m%d')}-{alert.id.hex[:8].upper()}",
                priority='HIGH' if alert.risk_score > 80 else 'MEDIUM',
                investigator=request.user
            )
        
        return Response({
            'status': 'success',
            'alert_status': alert.status,
            'investigation_created': resolution == 'fraud'
        })

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate a fraud alert"""
        alert = self.get_object()
        
        alert.escalated = True
        alert.assigned_to = request.user
        alert.save()
        
        return Response({
            'status': 'success',
            'message': 'Alert escalated successfully'
        })

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get fraud alert dashboard data"""
        queryset = self.get_queryset()
        
        # Recent alerts (last 7 days)
        recent_date = timezone.now() - timedelta(days=7)
        recent_alerts = queryset.filter(created_at__gte=recent_date)
        
        # Count by status
        status_counts = {}
        for status_choice in FraudAlert.STATUS_CHOICES:
            status_key = status_choice[0]
            status_counts[status_key] = recent_alerts.filter(status=status_key).count()
        
        # High risk alerts
        high_risk_alerts = recent_alerts.filter(risk_score__gte=75).count()
        
        # Blocked transactions
        blocked_transactions = recent_alerts.filter(transaction_blocked=True).count()
        
        # Recent high-priority alerts
        high_priority = recent_alerts.filter(
            risk_score__gte=75,
            status__in=['OPEN', 'INVESTIGATING']
        ).order_by('-created_at')[:10]
        
        return Response({
            'summary': {
                'total_alerts_7d': recent_alerts.count(),
                'high_risk_alerts': high_risk_alerts,
                'blocked_transactions': blocked_transactions,
                'status_breakdown': status_counts
            },
            'high_priority_alerts': FraudAlertSerializer(high_priority, many=True).data
        })


class FraudInvestigationViewSet(viewsets.ModelViewSet):
    """ViewSet for fraud investigations"""
    serializer_class = FraudInvestigationSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'investigator']

    def get_queryset(self):
        return FraudInvestigation.objects.filter(
            company__owner=self.request.user
        ).select_related('alert', 'investigator')

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign investigation to a user"""
        investigation = self.get_object()
        investigation.investigator = request.user
        investigation.assigned_at = timezone.now()
        if investigation.status == 'OPEN':
            investigation.status = 'IN_PROGRESS'
        investigation.save()
        
        return Response({
            'status': 'success',
            'assigned_to': request.user.username
        })

    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add investigation note"""
        investigation = self.get_object()
        note = request.data.get('note', '')
        
        if not note:
            return Response(
                {'error': 'Note content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Append to investigation notes
        current_notes = investigation.investigation_notes or ''
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        new_note = f"\n[{timestamp}] {request.user.username}: {note}"
        investigation.investigation_notes = current_notes + new_note
        investigation.save()
        
        return Response({
            'status': 'success',
            'message': 'Note added successfully'
        })

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close investigation"""
        investigation = self.get_object()
        resolution = request.data.get('resolution')
        summary = request.data.get('summary', '')
        
        if resolution not in ['CLOSED_FRAUD', 'CLOSED_LEGITIMATE', 'CLOSED_INCONCLUSIVE']:
            return Response(
                {'error': 'Invalid resolution'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        investigation.status = resolution
        investigation.resolution_summary = summary
        investigation.closed_at = timezone.now()
        investigation.save()
        
        return Response({
            'status': 'success',
            'investigation_status': investigation.status
        })


class WhitelistEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for whitelist entries"""
    serializer_class = WhitelistEntrySerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entity_type', 'is_active']

    def get_queryset(self):
        return WhitelistEntry.objects.filter(
            company__owner=self.request.user
        )

    def perform_create(self, serializer):
        company = self.request.user.companies.first()
        if not company:
            raise ValueError("User must have a company")
        serializer.save(company=company, added_by=self.request.user)


class FraudMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for fraud metrics"""
    serializer_class = FraudMetricsSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date']

    def get_queryset(self):
        return FraudMetrics.objects.filter(
            company__owner=self.request.user
        )

    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get fraud detection trends"""
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        metrics = self.get_queryset().filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        # Calculate trends
        trend_data = []
        for metric in metrics:
            fraud_rate = (metric.confirmed_fraud / metric.total_transactions * 100) if metric.total_transactions > 0 else 0
            detection_rate = metric.detection_rate
            false_positive_rate = metric.false_positive_rate
            
            trend_data.append({
                'date': metric.date.isoformat(),
                'total_transactions': metric.total_transactions,
                'flagged_transactions': metric.flagged_transactions,
                'confirmed_fraud': metric.confirmed_fraud,
                'fraud_rate': round(fraud_rate, 2),
                'detection_rate': float(detection_rate),
                'false_positive_rate': float(false_positive_rate),
                'fraud_amount_detected': float(metric.fraud_amount_detected),
                'fraud_amount_prevented': float(metric.fraud_amount_prevented)
            })
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'trends': trend_data
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get fraud metrics summary"""
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        metrics = self.get_queryset().filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        if not metrics.exists():
            return Response({
                'message': 'No data available for the selected period',
                'summary': {}
            })
        
        # Aggregate metrics
        total_transactions = sum(m.total_transactions for m in metrics)
        total_flagged = sum(m.flagged_transactions for m in metrics)
        total_fraud = sum(m.confirmed_fraud for m in metrics)
        total_false_positives = sum(m.false_positives for m in metrics)
        total_amount_detected = sum(m.fraud_amount_detected for m in metrics)
        total_amount_prevented = sum(m.fraud_amount_prevented for m in metrics)
        
        # Calculate rates
        fraud_rate = (total_fraud / total_transactions * 100) if total_transactions > 0 else 0
        detection_rate = (total_flagged / total_transactions * 100) if total_transactions > 0 else 0
        false_positive_rate = (total_false_positives / total_flagged * 100) if total_flagged > 0 else 0
        precision = (total_fraud / total_flagged * 100) if total_flagged > 0 else 0
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {
                'total_transactions': total_transactions,
                'total_flagged': total_flagged,
                'total_fraud_confirmed': total_fraud,
                'total_false_positives': total_false_positives,
                'fraud_rate': round(fraud_rate, 2),
                'detection_rate': round(detection_rate, 2),
                'false_positive_rate': round(false_positive_rate, 2),
                'precision': round(precision, 2),
                'total_amount_detected': float(total_amount_detected),
                'total_amount_prevented': float(total_amount_prevented)
            }
        })
