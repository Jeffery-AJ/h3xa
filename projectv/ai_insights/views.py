from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import logging

from ai_insights.models import (
    FinancialHealthScore, AnomalyDetection, SmartCategorization,
    BudgetInsight, FinancialGoalRecommendation, AIAnalysisLog
)
from ai_insights.serializers import (
    FinancialHealthScoreSerializer, AnomalyDetectionSerializer,
    SmartCategorizationSerializer, BudgetInsightSerializer,
    FinancialGoalRecommendationSerializer, AIAnalysisLogSerializer,
    AIDashboardSerializer
)
from ai_insights.ai_analyzer import ai_analyzer
from core.models import Company, Transaction, Budget

logger = logging.getLogger(__name__)


class FinancialHealthViewSet(viewsets.ModelViewSet):
    """AI-powered financial health scoring"""
    serializer_class = FinancialHealthScoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'risk_level']
    ordering = ['-calculated_at']

    def get_queryset(self):
        return FinancialHealthScore.objects.filter(
            company__owner=self.request.user
        )

    @action(detail=False, methods=['post'])
    def calculate_score(self, request):
        """Calculate financial health score for a company"""
        company_id = request.data.get('company_id')
        if not company_id:
            return Response(
                {'error': 'company_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if user owns the company
            company = Company.objects.get(id=company_id, owner=request.user)
            
            # Calculate health score using AI
            health_score = ai_analyzer.calculate_financial_health_score(company_id)
            
            serializer = self.get_serializer(health_score)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found or not owned by user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return Response(
                {'error': 'Failed to calculate health score'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def company_latest(self, request):
        """Get latest health score for a company"""
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response(
                {'error': 'company_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            health_score = self.get_queryset().filter(
                company_id=company_id
            ).latest('calculated_at')
            
            serializer = self.get_serializer(health_score)
            return Response(serializer.data)
            
        except FinancialHealthScore.DoesNotExist:
            return Response(
                {'error': 'No health score found for this company'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AnomalyDetectionViewSet(viewsets.ModelViewSet):
    """AI-powered transaction anomaly detection"""
    serializer_class = AnomalyDetectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['anomaly_type', 'risk_level', 'is_false_positive']
    ordering = ['-detected_at']

    def get_queryset(self):
        return AnomalyDetection.objects.filter(
            transaction__company__owner=self.request.user
        )

    @action(detail=False, methods=['post'])
    def analyze_transaction(self, request):
        """Analyze a specific transaction for anomalies"""
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transaction = Transaction.objects.get(
                id=transaction_id, 
                company__owner=request.user
            )
            
            # Run AI anomaly detection
            anomaly = ai_analyzer.detect_anomaly(transaction)
            
            if anomaly:
                serializer = self.get_serializer(anomaly)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'message': 'No anomaly detected'}, 
                    status=status.HTTP_200_OK
                )
                
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found or not owned by user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error analyzing transaction: {e}")
            return Response(
                {'error': 'Failed to analyze transaction'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """Mark an anomaly as false positive"""
        anomaly = self.get_object()
        anomaly.is_false_positive = True
        anomaly.reviewed_by = request.user
        anomaly.notes = request.data.get('notes', '')
        anomaly.save()

        serializer = self.get_serializer(anomaly)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def company_summary(self, request):
        """Get anomaly summary for a company"""
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response(
                {'error': 'company_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(
            transaction__company_id=company_id
        )

        summary = {
            'total_anomalies': queryset.count(),
            'high_risk': queryset.filter(risk_level='HIGH').count(),
            'critical_risk': queryset.filter(risk_level='CRITICAL').count(),
            'false_positives': queryset.filter(is_false_positive=True).count(),
            'by_type': dict(queryset.values_list('anomaly_type').annotate(count=Count('id'))),
            'recent_anomalies': AnomalyDetectionSerializer(
                queryset[:5], many=True
            ).data
        }

        return Response(summary)


class SmartCategorizationViewSet(viewsets.ModelViewSet):
    """AI-powered transaction categorization"""
    serializer_class = SmartCategorizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_accepted', 'suggested_category']
    ordering = ['-created_at']

    def get_queryset(self):
        return SmartCategorization.objects.filter(
            transaction__company__owner=self.request.user
        )

    @action(detail=False, methods=['post'])
    def categorize_transaction(self, request):
        """Categorize a specific transaction using AI"""
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transaction = Transaction.objects.get(
                id=transaction_id, 
                company__owner=request.user
            )
            
            # Run AI categorization
            categorization = ai_analyzer.categorize_transaction(transaction)
            
            serializer = self.get_serializer(categorization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found or not owned by user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error categorizing transaction: {e}")
            return Response(
                {'error': 'Failed to categorize transaction'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def accept_suggestion(self, request, pk=None):
        """Accept AI categorization suggestion"""
        categorization = self.get_object()
        
        # Update the transaction with suggested category
        transaction = categorization.transaction
        transaction.category = categorization.suggested_category
        transaction.save()
        
        # Mark as accepted
        categorization.is_accepted = True
        categorization.accepted_by = request.user
        categorization.save()

        serializer = self.get_serializer(categorization)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_categorize(self, request):
        """Categorize multiple transactions using AI"""
        company_id = request.data.get('company_id')
        limit = int(request.data.get('limit', 10))
        
        if not company_id:
            return Response(
                {'error': 'company_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get uncategorized transactions
            transactions = Transaction.objects.filter(
                company_id=company_id,
                company__owner=request.user,
                category__isnull=True
            )[:limit]

            categorizations = []
            for transaction in transactions:
                try:
                    categorization = ai_analyzer.categorize_transaction(transaction)
                    categorizations.append(categorization)
                except Exception as e:
                    logger.error(f"Failed to categorize transaction {transaction.id}: {e}")

            serializer = self.get_serializer(categorizations, many=True)
            return Response({
                'categorized_count': len(categorizations),
                'categorizations': serializer.data
            })
                
        except Exception as e:
            logger.error(f"Error in bulk categorization: {e}")
            return Response(
                {'error': 'Failed to categorize transactions'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BudgetInsightViewSet(viewsets.ModelViewSet):
    """AI-powered budget insights and recommendations"""
    serializer_class = BudgetInsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'budget', 'insight_type', 'severity', 'is_read']
    ordering = ['-created_at']

    def get_queryset(self):
        return BudgetInsight.objects.filter(
            company__owner=self.request.user
        )

    @action(detail=False, methods=['post'])
    def generate_insights(self, request):
        """Generate AI budget insights for a company"""
        company_id = request.data.get('company_id')
        if not company_id:
            return Response(
                {'error': 'company_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
            
            # Generate budget insights using AI
            insights = ai_analyzer.generate_budget_insights(company_id)
            
            return Response({
                'insights_count': len(insights),
                'insights': insights
            })
            
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found or not owned by user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating budget insights: {e}")
            return Response(
                {'error': 'Failed to generate budget insights'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FinancialGoalRecommendationViewSet(viewsets.ModelViewSet):
    """AI-powered financial goal recommendations"""
    serializer_class = FinancialGoalRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'goal_type', 'is_accepted']
    ordering = ['-created_at']

    def get_queryset(self):
        return FinancialGoalRecommendation.objects.filter(
            company__owner=self.request.user
        )

    @action(detail=False, methods=['post'])
    def generate_recommendations(self, request):
        """Generate AI goal recommendations for a company"""
        company_id = request.data.get('company_id')
        if not company_id:
            return Response(
                {'error': 'company_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
            
            # Generate goal recommendations using AI
            recommendations = ai_analyzer.recommend_financial_goals(company_id)
            
            return Response({
                'recommendations_count': len(recommendations),
                'recommendations': recommendations
            })
            
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found or not owned by user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating goal recommendations: {e}")
            return Response(
                {'error': 'Failed to generate goal recommendations'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIDashboardViewSet(viewsets.ViewSet):
    """AI Dashboard with comprehensive insights"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def company_overview(self, request):
        """Get comprehensive AI insights overview for a company"""
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response(
                {'error': 'company_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
            
            # Get latest health score
            try:
                health_score = FinancialHealthScore.objects.filter(
                    company=company
                ).latest('calculated_at')
                health_data = {
                    'score': health_score.score,
                    'risk_level': health_score.risk_level,
                    'key_insight': health_score.strengths[0] if health_score.strengths else "No insights available",
                    'recommendation': health_score.recommendations[0] if health_score.recommendations else "No recommendations available"
                }
            except FinancialHealthScore.DoesNotExist:
                health_data = {
                    'score': 0,
                    'risk_level': 'UNKNOWN',
                    'key_insight': 'Health score not calculated',
                    'recommendation': 'Run health analysis'
                }

            # Get anomaly summary
            anomalies = AnomalyDetection.objects.filter(
                transaction__company=company
            )
            anomaly_data = {
                'count': anomalies.count(),
                'high_risk_count': anomalies.filter(risk_level__in=['HIGH', 'CRITICAL']).count(),
                'latest_anomaly': anomalies.first().explanation if anomalies.exists() else "No anomalies detected"
            }

            # Get categorization accuracy
            categorizations = SmartCategorization.objects.filter(
                transaction__company=company
            )
            accuracy = categorizations.filter(is_accepted=True).count() / max(categorizations.count(), 1)

            # Get budget alerts
            budget_alerts = BudgetInsight.objects.filter(
                company=company,
                severity__in=['WARNING', 'CRITICAL'],
                is_read=False
            ).count()

            # Get goal recommendations
            goal_recommendations = FinancialGoalRecommendation.objects.filter(
                company=company,
                is_accepted=False
            ).count()

            # Get last analysis time
            last_analysis = AIAnalysisLog.objects.filter(
                company=company
            ).order_by('-created_at').first()

            dashboard_data = {
                'health_score': health_data,
                'anomalies': anomaly_data,
                'categorization_accuracy': accuracy,
                'budget_alerts': budget_alerts,
                'goal_recommendations': goal_recommendations,
                'last_analysis': last_analysis.created_at if last_analysis else None
            }

            serializer = AIDashboardSerializer(dashboard_data)
            return Response(serializer.data)

        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found or not owned by user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating AI dashboard: {e}")
            return Response(
                {'error': 'Failed to generate AI dashboard'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
