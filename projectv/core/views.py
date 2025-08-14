from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import logging

from .models import (
    Company, Account, TransactionCategory, Transaction, 
    Budget, FinancialGoal, TransactionType, TransactionStatus,
    BulkUpload, BulkUploadError
)
from .serializers import (
    CompanySerializer, AccountSerializer, TransactionCategorySerializer,
    TransactionSerializer, BudgetSerializer, FinancialGoalSerializer,
    AccountBalanceAnalyticsSerializer, CashFlowAnalyticsSerializer,
    CategoryAnalyticsSerializer, FinancialHealthSerializer,
    BulkUploadSerializer, BulkUploadErrorSerializer
)
from .rag_analyzer import FinancialDataRAG
# from .ai_cfo_agent import AICFOAgent

logger = logging.getLogger(__name__)


class CompanyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing companies"""
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry', 'currency', 'is_active']
    search_fields = ['name', 'registration_number', 'tax_id']
    ordering_fields = ['name', 'created_at', 'annual_revenue']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return companies owned by the current user"""
        return Company.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Set the owner to the current user"""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def financial_summary(self, request, pk=None):
        """Get financial summary for a company"""
        company = self.get_object()
        
        # Calculate key metrics
        total_accounts = company.accounts.filter(is_active=True).count()
        total_balance = sum(account.current_balance for account in company.accounts.filter(is_active=True))
        
        # Get recent transactions
        recent_transactions = company.transactions.filter(
            status=TransactionStatus.COMPLETED
        ).order_by('-transaction_date')[:10]
        
        # Monthly cash flow
        last_30_days = timezone.now() - timedelta(days=30)
        monthly_income = company.transactions.filter(
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.COMPLETED,
            transaction_date__gte=last_30_days
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_expenses = company.transactions.filter(
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            transaction_date__gte=last_30_days
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'company': CompanySerializer(company).data,
            'metrics': {
                'total_accounts': total_accounts,
                'total_balance': total_balance,
                'monthly_income': monthly_income,
                'monthly_expenses': monthly_expenses,
                'net_cash_flow': monthly_income - monthly_expenses,
            },
            'recent_transactions': TransactionSerializer(recent_transactions, many=True).data
        })

    @action(detail=True, methods=['get'])
    def ai_dashboard(self, request, pk=None):
        """Get AI-powered financial dashboard for a company"""
        company = self.get_object()
        
        try:
            from ai_insights.models import FinancialHealthScore, AnomalyDetection, SmartCategorization
            
            # Get latest health score
            health_score = FinancialHealthScore.objects.filter(
                company=company
            ).order_by('-calculated_at').first()
            
            # Get recent anomalies
            recent_anomalies = AnomalyDetection.objects.filter(
                transaction__company=company
            ).order_by('-detected_at')[:5]
            
            # Get categorization stats
            categorizations = SmartCategorization.objects.filter(
                transaction__company=company
            )
            total_suggestions = categorizations.count()
            accepted_suggestions = categorizations.filter(is_accepted=True).count()
            accuracy = (accepted_suggestions / total_suggestions * 100) if total_suggestions > 0 else 0
            
            return Response({
                'health_score': {
                    'score': health_score.score if health_score else 0,
                    'risk_level': health_score.risk_level if health_score else 'UNKNOWN',
                    'last_calculated': health_score.calculated_at if health_score else None,
                } if health_score else None,
                'anomalies': {
                    'count': recent_anomalies.count(),
                    'recent': [
                        {
                            'transaction_id': anomaly.transaction.id,
                            'type': anomaly.anomaly_type,
                            'risk_level': anomaly.risk_level,
                            'explanation': anomaly.explanation,
                            'detected_at': anomaly.detected_at
                        } for anomaly in recent_anomalies
                    ]
                },
                'categorization': {
                    'total_suggestions': total_suggestions,
                    'accepted_suggestions': accepted_suggestions,
                    'accuracy_percentage': round(accuracy, 2)
                }
            })
            
        except ImportError:
            return Response(
                {'error': 'AI insights not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error generating AI dashboard: {e}")
            return Response(
                {'error': 'Failed to generate AI dashboard'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def calculate_health_score(self, request, pk=None):
        """Calculate financial health score for a company"""
        company = self.get_object()
        
        try:
            from ai_insights.ai_analyzer import ai_analyzer
            health_score = ai_analyzer.calculate_financial_health_score(company.id)
            
            return Response({
                'company_id': company.id,
                'score': health_score.score,
                'risk_level': health_score.risk_level,
                'strengths': health_score.strengths,
                'weaknesses': health_score.weaknesses,
                'recommendations': health_score.recommendations,
                'calculated_at': health_score.calculated_at
            })
            
        except ImportError:
            return Response(
                {'error': 'AI insights not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return Response(
                {'error': 'Failed to calculate health score'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def analyze_transactions(self, request, pk=None):
        """Run AI analysis on all uncategorized transactions"""
        company = self.get_object()
        limit = min(int(request.data.get('limit', 20)), 50)  # Max 50 at once
        
        try:
            from ai_insights.ai_analyzer import ai_analyzer
            
            # Get uncategorized transactions
            uncategorized_transactions = company.transactions.filter(
                category__isnull=True
            )[:limit]
            
            results = {
                'processed': 0,
                'categorized': 0,
                'anomalies_detected': 0,
                'results': []
            }
            
            for transaction in uncategorized_transactions:
                try:
                    # Categorize transaction
                    categorization = ai_analyzer.categorize_transaction(transaction)
                    
                    # Detect anomalies
                    anomaly = ai_analyzer.detect_anomaly(transaction)
                    
                    result = {
                        'transaction_id': transaction.id,
                        'amount': float(transaction.amount),
                        'description': transaction.description,
                        'categorization': {
                            'suggested_category': categorization.suggested_category.name if categorization and categorization.suggested_category else None,
                            'confidence': categorization.confidence_score if categorization else 0,
                            'reasoning': categorization.reasoning if categorization else None
                        } if categorization else None,
                        'anomaly': {
                            'detected': bool(anomaly),
                            'type': anomaly.anomaly_type if anomaly else None,
                            'risk_level': anomaly.risk_level if anomaly else None,
                            'explanation': anomaly.explanation if anomaly else None
                        }
                    }
                    
                    results['results'].append(result)
                    results['processed'] += 1
                    
                    if categorization and categorization.suggested_category:
                        results['categorized'] += 1
                    
                    if anomaly:
                        results['anomalies_detected'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to analyze transaction {transaction.id}: {e}")
            
            return Response(results)
            
        except ImportError:
            return Response(
                {'error': 'AI insights not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error analyzing transactions: {e}")
            return Response(
                {'error': 'Failed to analyze transactions'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet for managing accounts"""
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'currency', 'is_active', 'company']
    search_fields = ['name', 'account_number', 'bank_name']
    ordering_fields = ['name', 'created_at', 'current_balance']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return accounts for companies owned by the current user"""
        return Account.objects.filter(company__owner=self.request.user)

    @action(detail=True, methods=['get'])
    def balance_history(self, request, pk=None):
        """Get balance history for an account"""
        account = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        transactions = account.transactions.filter(
            transaction_date__gte=start_date,
            status=TransactionStatus.COMPLETED
        ).order_by('transaction_date')
        
        balance_history = []
        running_balance = account.initial_balance
        
        for transaction in transactions:
            if transaction.transaction_type == TransactionType.INCOME:
                running_balance += transaction.amount
            elif transaction.transaction_type == TransactionType.EXPENSE:
                running_balance -= transaction.amount
            elif transaction.transaction_type == TransactionType.TRANSFER:
                if transaction.account == account:
                    running_balance -= transaction.amount
                elif transaction.to_account == account:
                    running_balance += transaction.amount
            
            balance_history.append({
                'date': transaction.transaction_date,
                'balance': running_balance,
                'transaction_id': transaction.id,
                'amount': transaction.amount,
                'type': transaction.transaction_type
            })
        
        return Response(balance_history)


class TransactionCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transaction categories"""
    serializer_class = TransactionCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_income', 'is_active', 'parent', 'company']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Return categories for companies owned by the current user"""
        return TransactionCategory.objects.filter(company__owner=self.request.user)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories in tree structure"""
        company_id = request.query_params.get('company')
        if not company_id:
            return Response({'error': 'Company ID is required'}, status=400)
        
        # Get root categories (no parent)
        root_categories = self.get_queryset().filter(
            company_id=company_id,
            parent__isnull=True,
            is_active=True
        )
        
        def build_tree(categories):
            tree = []
            for category in categories:
                node = TransactionCategorySerializer(category).data
                subcategories = category.subcategories.filter(is_active=True)
                if subcategories.exists():
                    node['children'] = build_tree(subcategories)
                tree.append(node)
            return tree
        
        return Response(build_tree(root_categories))


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transactions"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'status', 'account', 'category', 'is_anomaly']
    search_fields = ['description', 'reference_number']
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date']

    def get_queryset(self):
        """Return transactions for companies owned by the current user"""
        return Transaction.objects.filter(company__owner=self.request.user)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get transaction analytics"""
        company_id = request.query_params.get('company')
        days = int(request.query_params.get('days', 30))
        
        if not company_id:
            return Response({'error': 'Company ID is required'}, status=400)
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = self.get_queryset().filter(
            company_id=company_id,
            transaction_date__gte=start_date,
            status=TransactionStatus.COMPLETED
        )
        
        # Cash flow analytics
        income = queryset.filter(transaction_type=TransactionType.INCOME).aggregate(
            total=Sum('amount'), count=Count('id')
        )
        expenses = queryset.filter(transaction_type=TransactionType.EXPENSE).aggregate(
            total=Sum('amount'), count=Count('id')
        )
        
        # Category breakdown
        category_stats = queryset.values(
            'category__id', 'category__name'
        ).annotate(
            total_amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total_amount')
        
        # Daily cash flow
        daily_stats = queryset.extra(
            select={'day': 'date(transaction_date)'}
        ).values('day').annotate(
            income=Sum('amount', filter=Q(transaction_type=TransactionType.INCOME)),
            expenses=Sum('amount', filter=Q(transaction_type=TransactionType.EXPENSE))
        ).order_by('day')
        
        return Response({
            'summary': {
                'total_income': income['total'] or 0,
                'total_expenses': expenses['total'] or 0,
                'net_cash_flow': (income['total'] or 0) - (expenses['total'] or 0),
                'income_transactions': income['count'] or 0,
                'expense_transactions': expenses['count'] or 0,
            },
            'category_breakdown': category_stats,
            'daily_cash_flow': daily_stats,
        })

    @action(detail=False, methods=['get'])
    def anomalies(self, request):
        """Get transactions flagged as anomalies"""
        company_id = request.query_params.get('company')
        if not company_id:
            return Response({'error': 'Company ID is required'}, status=400)
        
        anomalies = self.get_queryset().filter(
            company_id=company_id,
            is_anomaly=True
        ).order_by('-transaction_date')
        
        return Response(TransactionSerializer(anomalies, many=True).data)

    @action(detail=True, methods=['post'])
    def ai_categorize(self, request, pk=None):
        """AI-powered categorization for a specific transaction"""
        transaction = self.get_object()
        
        try:
            from ai_insights.ai_analyzer import ai_analyzer
            categorization = ai_analyzer.categorize_transaction(transaction)
            
            return Response({
                'transaction_id': transaction.id,
                'suggested_category': categorization.suggested_category.name if categorization.suggested_category else None,
                'confidence_score': categorization.confidence_score,
                'reasoning': categorization.reasoning,
                'categorization_id': categorization.id
            })
        except ImportError:
            return Response(
                {'error': 'AI insights not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error in AI categorization: {e}")
            return Response(
                {'error': 'Failed to categorize transaction'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def ai_analyze_anomaly(self, request, pk=None):
        """AI-powered anomaly detection for a specific transaction"""
        transaction = self.get_object()
        
        try:
            from ai_insights.ai_analyzer import ai_analyzer
            anomaly = ai_analyzer.detect_anomaly(transaction)
            
            if anomaly:
                return Response({
                    'transaction_id': transaction.id,
                    'anomaly_detected': True,
                    'anomaly_type': anomaly.anomaly_type,
                    'risk_level': anomaly.risk_level,
                    'confidence_score': anomaly.confidence_score,
                    'explanation': anomaly.explanation,
                    'anomaly_id': anomaly.id
                })
            else:
                return Response({
                    'transaction_id': transaction.id,
                    'anomaly_detected': False,
                    'message': 'No anomaly detected'
                })
        except ImportError:
            return Response(
                {'error': 'AI insights not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error in AI anomaly detection: {e}")
            return Response(
                {'error': 'Failed to analyze transaction for anomalies'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def ai_bulk_categorize(self, request):
        """AI-powered bulk categorization for uncategorized transactions"""
        company_id = request.data.get('company_id')
        limit = min(int(request.data.get('limit', 10)), 50)  # Max 50 at a time
        
        if not company_id:
            return Response({'error': 'company_id is required'}, status=400)
        
        try:
            from ai_insights.ai_analyzer import ai_analyzer
            
            # Get uncategorized transactions
            uncategorized = self.get_queryset().filter(
                company_id=company_id,
                category__isnull=True
            )[:limit]
            
            categorizations = []
            for transaction in uncategorized:
                try:
                    categorization = ai_analyzer.categorize_transaction(transaction)
                    categorizations.append({
                        'transaction_id': transaction.id,
                        'suggested_category': categorization.suggested_category.name if categorization.suggested_category else None,
                        'confidence_score': categorization.confidence_score,
                        'categorization_id': categorization.id
                    })
                except Exception as e:
                    logger.error(f"Failed to categorize transaction {transaction.id}: {e}")
            
            return Response({
                'processed_count': len(categorizations),
                'categorizations': categorizations
            })
            
        except ImportError:
            return Response(
                {'error': 'AI insights not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error in bulk categorization: {e}")
            return Response(
                {'error': 'Failed to process bulk categorization'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BudgetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing budgets"""
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active', 'company']
    search_fields = ['name']
    ordering_fields = ['name', 'start_date', 'budgeted_amount']
    ordering = ['-start_date']

    def get_queryset(self):
        """Return budgets for companies owned by the current user"""
        return Budget.objects.filter(company__owner=self.request.user)

    @action(detail=True, methods=['post'])
    def update_spent_amount(self, request, pk=None):
        """Update spent amount for a budget based on transactions"""
        budget = self.get_object()
        
        # Calculate spent amount from transactions
        spent = Transaction.objects.filter(
            company=budget.company,
            category=budget.category,
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            transaction_date__gte=budget.start_date,
            transaction_date__lte=budget.end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        budget.spent_amount = spent
        budget.save()
        
        return Response(BudgetSerializer(budget).data)


class FinancialGoalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing financial goals"""
    serializer_class = FinancialGoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['goal_type', 'is_achieved', 'company']
    search_fields = ['name']
    ordering_fields = ['name', 'target_date', 'target_amount']
    ordering = ['-target_date']

    def get_queryset(self):
        """Return financial goals for companies owned by the current user"""
        return FinancialGoal.objects.filter(company__owner=self.request.user)



class FinancialRAGViewSet(viewsets.ViewSet):
    """ViewSet for RAG-based financial analysis"""
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rag_analyzer = FinancialDataRAG()
    
    @action(detail=False, methods=['post'])
    def analyze_upload(self, request):
        """Analyze a bulk upload using RAG"""
        try:
            bulk_upload_id = request.data.get('bulk_upload_id')
            if not bulk_upload_id:
                return Response(
                    {'error': 'bulk_upload_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get bulk upload
            try:
                bulk_upload = BulkUpload.objects.get(
                    id=bulk_upload_id,
                    company__owner=request.user
                )
            except BulkUpload.DoesNotExist:
                return Response(
                    {'error': 'Bulk upload not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Perform RAG analysis
            analysis = self.rag_analyzer.analyze_bulk_upload(bulk_upload)
            
            return Response(analysis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"RAG analysis error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def query_data(self, request):
        """Query financial data using natural language"""
        try:
            query = request.data.get('query')
            company_id = request.data.get('company_id')
            
            if not query:
                return Response(
                    {'error': 'query is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not company_id:
                return Response(
                    {'error': 'company_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get company
            try:
                company = Company.objects.get(id=company_id, owner=request.user)
            except Company.DoesNotExist:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Query using RAG
            response = self.rag_analyzer.query_financial_data(query, company)
            
            return Response({
                'query': query,
                'response': response,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"RAG query error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def analyze_csv_content(self, request):
        """Analyze CSV content directly with RAG insights"""
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            csv_file = request.FILES['file']
            
            # Read CSV and create insights
            import pandas as pd
            import io
            
            csv_content = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Create analysis prompt
            csv_summary = f"""
            CSV Analysis Summary:
            - Total rows: {len(df)}
            - Columns: {list(df.columns)}
            - Sample data: {df.head(3).to_dict('records')}
            
            Data types: {df.dtypes.to_dict()}
            """
            
            # Use RAG to analyze
            query = f"Analyze this financial CSV data and provide insights: {csv_summary}"
            
            # Create a simple LlamaIndex query without building full vector store
            from llama_index.core import Settings
            from llama_index.llms.openai import OpenAI
            from django.conf import settings
            
            llm = OpenAI(
                api_key=settings.OPENAI_API_KEY, 
                model="openai/gpt-5",
                api_base="https://models.github.ai/inference"
            )
            response = llm.complete(query)
            
            return Response({
                'csv_info': {
                    'rows': len(df),
                    'columns': list(df.columns),
                    'sample_data': df.head(3).to_dict('records')
                },
                'ai_insights': str(response),
                'suggestions': [
                    "Consider categorizing transactions by type",
                    "Review data for any missing or inconsistent entries",
                    "Identify patterns in spending or income"
                ],
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CSV analysis error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AICFOViewSet(viewsets.ViewSet):
    """ViewSet for AI CFO interactions"""
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cfo_agents = {}  # Cache CFO agents per company
    
    def get_cfo_agent(self, company):
        """Get or create CFO agent for company"""
        company_id = str(company.id)
        
        if company_id not in self.cfo_agents:
            from .ai_cfo_agent import AICFOAgent
            self.cfo_agents[company_id] = AICFOAgent(company)
        
        return self.cfo_agents[company_id]
    
    @action(detail=False, methods=['post'])
    def chat(self, request):
        """Chat with the AI CFO"""
        try:
            message = request.data.get('message')
            company_id = request.data.get('company_id')
            
            if not message:
                return Response(
                    {'error': 'message is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not company_id:
                return Response(
                    {'error': 'company_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get company
            try:
                company = Company.objects.get(id=company_id, owner=request.user)
            except Company.DoesNotExist:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get CFO agent and process chat
            cfo_agent = self.get_cfo_agent(company)
            response = cfo_agent.chat(message)
            
            return Response(response, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"AI CFO chat error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def get_financial_advice(self, request):
        """Get specialized financial advice"""
        try:
            topic = request.data.get('topic')
            company_id = request.data.get('company_id')
            
            if not topic:
                return Response(
                    {'error': 'topic is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not company_id:
                return Response(
                    {'error': 'company_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get company
            try:
                company = Company.objects.get(id=company_id, owner=request.user)
            except Company.DoesNotExist:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get CFO agent and specialized advice
            cfo_agent = self.get_cfo_agent(company)
            advice = cfo_agent.get_specialized_financial_advice(topic)
            
            return Response(advice, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"AI CFO advice error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def analyze_upload(self, request):
        """Get comprehensive CFO analysis of CSV upload"""
        try:
            bulk_upload_id = request.data.get('bulk_upload_id')
            company_id = request.data.get('company_id')
            
            if not bulk_upload_id:
                return Response(
                    {'error': 'bulk_upload_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not company_id:
                return Response(
                    {'error': 'company_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get company
            try:
                company = Company.objects.get(id=company_id, owner=request.user)
            except Company.DoesNotExist:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get CFO agent and comprehensive analysis
            cfo_agent = self.get_cfo_agent(company)
            analysis = cfo_agent.analyze_csv_upload_comprehensive(bulk_upload_id)
            
            return Response(analysis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"AI CFO upload analysis error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def expertise_areas(self, request):
        """Get available CFO expertise areas"""
        try:
            # Get a sample CFO agent to show expertise areas
            if hasattr(request.user, 'companies') and request.user.companies.exists():
                company = request.user.companies.first()
                cfo_agent = self.get_cfo_agent(company)
                
                return Response({
                    'expertise_areas': cfo_agent.expertise_areas,
                    'description': 'Available financial expertise areas for specialized advice'
                }, status=status.HTTP_200_OK)
            else:
                # Default expertise areas
                return Response({
                    'expertise_areas': {
                        'cash_flow': 'Cash Flow Management',
                        'cost_reduction': 'Cost Reduction & Optimization',
                        'investment': 'Investment Strategy',
                        'risk_management': 'Financial Risk Management'
                    },
                    'description': 'Available financial expertise areas for specialized advice'
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"AI CFO expertise areas error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def session_summary(self, request):
        """Get current conversation session summary"""
        try:
            company_id = request.query_params.get('company_id')
            
            if not company_id:
                return Response(
                    {'error': 'company_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get company
            try:
                company = Company.objects.get(id=company_id, owner=request.user)
            except Company.DoesNotExist:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get CFO agent session summary
            cfo_agent = self.get_cfo_agent(company)
            summary = cfo_agent.get_session_summary()
            
            return Response(summary, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"AI CFO session summary error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def clear_session(self, request):
        """Clear conversation session"""
        try:
            company_id = request.data.get('company_id')
            
            if not company_id:
                return Response(
                    {'error': 'company_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get company
            try:
                company = Company.objects.get(id=company_id, owner=request.user)
            except Company.DoesNotExist:
                return Response(
                    {'error': 'Company not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Clear CFO agent session
            cfo_agent = self.get_cfo_agent(company)
            cfo_agent.clear_session()
            
            return Response({
                'message': 'Session cleared successfully',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"AI CFO clear session error: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
