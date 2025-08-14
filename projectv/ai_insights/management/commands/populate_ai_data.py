from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Company, Account, Transaction, TransactionCategory
from ai_insights.models import FinancialHealthScore, PredictionModel, AnomalyDetection, SmartCategorization, BudgetInsight, FinancialGoalRecommendation
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Populate sample AI insights data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample AI insights data...')
        
        # Get or create a company
        company, created = Company.objects.get_or_create(
            name='Sample Corp',
            defaults={
                'address': '123 Business St',
                'phone': '+1234567890',
                'email': 'info@samplecorp.com'
            }
        )
        
        # Create Financial Health Score
        health_score, created = FinancialHealthScore.objects.get_or_create(
            company=company,
            defaults={
                'score': 78,
                'factors': {
                    'cash_flow': 85,
                    'debt_ratio': 70,
                    'expense_management': 80,
                    'revenue_growth': 75
                },
                'recommendations': [
                    'Optimize cash flow by reducing payment terms',
                    'Consider refinancing high-interest debt',
                    'Implement automated expense tracking'
                ],
                'strengths': [
                    'Strong cash flow management',
                    'Consistent revenue growth',
                    'Low operational costs'
                ],
                'concerns': [
                    'High debt-to-equity ratio',
                    'Seasonal revenue fluctuations'
                ],
                'risk_level': 'MEDIUM'
            }
        )
        if created:
            self.stdout.write(f'Created financial health score: {health_score.score}')
        
        # Create Prediction Models
        prediction_types = ['CASH_FLOW', 'REVENUE', 'EXPENSES', 'BUDGET_BURN']
        for pred_type in prediction_types:
            prediction, created = PredictionModel.objects.get_or_create(
                company=company,
                prediction_type=pred_type,
                defaults={
                    'model_data': {
                        'algorithm': 'linear_regression',
                        'features': ['historical_data', 'seasonality', 'trends'],
                        'training_period': '12_months'
                    },
                    'accuracy_score': random.uniform(0.75, 0.95),
                    'predictions': {
                        'next_30_days': [random.uniform(1000, 5000) for _ in range(30)],
                        'next_90_days': [random.uniform(1000, 5000) for _ in range(90)],
                        'confidence_intervals': {
                            'lower': [random.uniform(800, 1200) for _ in range(30)],
                            'upper': [random.uniform(4000, 6000) for _ in range(30)]
                        }
                    }
                }
            )
            if created:
                self.stdout.write(f'Created prediction model: {pred_type}')
        
        # Get sample transactions for anomaly detection
        transactions = Transaction.objects.filter(company=company)[:5]
        
        # Create Anomaly Detections
        for i, transaction in enumerate(transactions):
            anomaly, created = AnomalyDetection.objects.get_or_create(
                transaction=transaction,
                defaults={
                    'anomaly_type': random.choice(['AMOUNT_UNUSUAL', 'TIME_UNUSUAL', 'FREQUENCY_HIGH', 'PATTERN_BREAK']),
                    'confidence_score': random.uniform(0.6, 0.95),
                    'risk_level': random.choice(['LOW', 'MEDIUM', 'HIGH']),
                    'explanation': f'Transaction amount significantly higher than historical average for this category'
                }
            )
            if created:
                self.stdout.write(f'Created anomaly detection for transaction: {transaction.description}')
        
        # Create Smart Categorizations
        categories = TransactionCategory.objects.filter(company=company)
        for transaction in transactions:
            if categories:
                categorization, created = SmartCategorization.objects.get_or_create(
                    transaction=transaction,
                    defaults={
                        'suggested_category': random.choice(categories),
                        'confidence_score': random.uniform(0.8, 0.98),
                        'reasoning': f'Based on transaction description and merchant patterns'
                    }
                )
                if created:
                    self.stdout.write(f'Created smart categorization for: {transaction.description}')
        
        # Create Budget Insights (without linking to specific budgets for now)
        insight_types = ['OVERSPEND', 'UNDERSPEND', 'TREND', 'OPTIMIZATION']
        for i, insight_type in enumerate(insight_types):
            insight, created = BudgetInsight.objects.get_or_create(
                company=company,
                insight_type=insight_type,
                defaults={
                    'severity': random.choice(['INFO', 'WARNING', 'CRITICAL']),
                    'title': f'{insight_type.replace("_", " ").title()} Alert',
                    'message': f'AI detected a {insight_type.lower().replace("_", " ")} pattern in your spending',
                    'recommended_action': f'Consider reviewing your budget allocation for better {insight_type.lower().replace("_", " ")} management',
                    'impact_score': random.uniform(0.3, 0.9)
                }
            )
            if created:
                self.stdout.write(f'Created budget insight: {insight_type}')
        
        # Create Financial Goal Recommendations
        goal_types = ['SAVINGS', 'REVENUE', 'EXPENSE_REDUCTION', 'INVESTMENT']
        for goal_type in goal_types:
            recommendation, created = FinancialGoalRecommendation.objects.get_or_create(
                company=company,
                goal_type=goal_type,
                defaults={
                    'name': f'{goal_type.replace("_", " ").title()} Goal',
                    'description': f'AI-recommended strategy for {goal_type.lower().replace("_", " ")}',
                    'target_amount': Decimal(str(random.uniform(10000, 50000))),
                    'timeframe_months': random.randint(6, 36),
                    'why_important': f'This goal will help improve your financial health by focusing on {goal_type.lower().replace("_", " ")}',
                    'confidence_score': random.uniform(0.7, 0.9)
                }
            )
            if created:
                self.stdout.write(f'Created goal recommendation: {goal_type}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated AI insights sample data!'))
        self.stdout.write('You can now test the AI insights APIs with sample data.')
