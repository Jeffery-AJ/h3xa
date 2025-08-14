"""
Advanced AI Financial Analytics Engine
Provides sophisticated AI-powered insights for financial data
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import logging
import pickle
import os

from core.models import Transaction, Account, Company, TransactionCategory, TransactionType
from ai_insights.models import FinancialHealthScore, PredictionModel, AnomalyDetection
from fraud_detection.models import BehavioralProfile

logger = logging.getLogger(__name__)


class AdvancedAIEngine:
    """Advanced AI engine for financial analytics"""
    
    def __init__(self):
        self.scalers = {}
        self.encoders = {}
        self.models = {}
    
    def generate_comprehensive_insights(self, company: Company) -> Dict:
        """Generate comprehensive AI insights for a company"""
        try:
            insights = {
                'company_id': str(company.id),
                'generated_at': timezone.now().isoformat(),
                'health_score': {},
                'predictions': {},
                'anomalies': [],
                'recommendations': [],
                'cash_flow_analysis': {},
                'spending_patterns': {},
                'risk_assessment': {},
                'optimization_opportunities': []
            }
            
            # Calculate financial health score
            insights['health_score'] = self._calculate_advanced_health_score(company)
            
            # Generate predictions
            insights['predictions'] = self._generate_predictions(company)
            
            # Detect anomalies
            insights['anomalies'] = self._detect_financial_anomalies(company)
            
            # Analyze cash flow
            insights['cash_flow_analysis'] = self._analyze_cash_flow(company)
            
            # Analyze spending patterns
            insights['spending_patterns'] = self._analyze_spending_patterns(company)
            
            # Assess risks
            insights['risk_assessment'] = self._assess_financial_risks(company)
            
            # Generate recommendations
            insights['recommendations'] = self._generate_ai_recommendations(company, insights)
            
            # Find optimization opportunities
            insights['optimization_opportunities'] = self._find_optimization_opportunities(company)
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive insights: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_advanced_health_score(self, company: Company) -> Dict:
        """Calculate advanced financial health score using multiple factors"""
        try:
            score_components = {
                'cash_flow': 0,
                'revenue_stability': 0,
                'expense_control': 0,
                'liquidity': 0,
                'growth_trajectory': 0,
                'risk_factors': 0
            }
            
            # Get transaction data for analysis
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            transactions = Transaction.objects.filter(
                company=company,
                transaction_date__gte=start_date,
                status='completed'
            )
            
            if not transactions.exists():
                return {'score': 50, 'message': 'Insufficient data for health score calculation'}
            
            # Calculate cash flow score (30% weight)
            cash_flow_score = self._calculate_cash_flow_score(transactions)
            score_components['cash_flow'] = cash_flow_score
            
            # Calculate revenue stability (25% weight)
            revenue_stability = self._calculate_revenue_stability(transactions)
            score_components['revenue_stability'] = revenue_stability
            
            # Calculate expense control (20% weight)
            expense_control = self._calculate_expense_control(transactions)
            score_components['expense_control'] = expense_control
            
            # Calculate liquidity score (15% weight)
            liquidity_score = self._calculate_liquidity_score(company)
            score_components['liquidity'] = liquidity_score
            
            # Calculate growth trajectory (10% weight)
            growth_score = self._calculate_growth_trajectory(transactions)
            score_components['growth_trajectory'] = growth_score
            
            # Calculate overall score
            weights = {
                'cash_flow': 0.30,
                'revenue_stability': 0.25,
                'expense_control': 0.20,
                'liquidity': 0.15,
                'growth_trajectory': 0.10
            }
            
            overall_score = sum(
                score_components[component] * weights[component]
                for component in weights
            )
            
            # Determine risk level
            if overall_score >= 80:
                risk_level = 'LOW'
            elif overall_score >= 60:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'HIGH'
            
            return {
                'score': round(overall_score, 1),
                'risk_level': risk_level,
                'components': score_components,
                'weights': weights,
                'analysis_period_days': 90
            }
            
        except Exception as e:
            logger.error(f"Health score calculation failed: {str(e)}")
            return {'score': 0, 'error': str(e)}
    
    def _calculate_cash_flow_score(self, transactions) -> float:
        """Calculate cash flow health score"""
        try:
            income = transactions.filter(transaction_type=TransactionType.INCOME).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            expenses = transactions.filter(transaction_type=TransactionType.EXPENSE).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            if income == 0:
                return 0
            
            cash_flow_ratio = float((income - expenses) / income)
            
            # Score based on cash flow ratio
            if cash_flow_ratio >= 0.3:  # 30% or more positive cash flow
                return 100
            elif cash_flow_ratio >= 0.2:
                return 85
            elif cash_flow_ratio >= 0.1:
                return 70
            elif cash_flow_ratio >= 0:
                return 55
            elif cash_flow_ratio >= -0.1:
                return 40
            else:
                return 20
                
        except Exception as e:
            logger.error(f"Cash flow score calculation failed: {str(e)}")
            return 0
    
    def _calculate_revenue_stability(self, transactions) -> float:
        """Calculate revenue stability score"""
        try:
            # Group income by week
            income_transactions = transactions.filter(transaction_type=TransactionType.INCOME)
            
            weekly_income = []
            current_date = transactions.first().transaction_date.date()
            end_date = transactions.last().transaction_date.date()
            
            while current_date <= end_date:
                week_end = current_date + timedelta(days=7)
                week_income = income_transactions.filter(
                    transaction_date__date__gte=current_date,
                    transaction_date__date__lt=week_end
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                weekly_income.append(float(week_income))
                current_date = week_end
            
            if len(weekly_income) < 2:
                return 50  # Insufficient data
            
            # Calculate coefficient of variation (lower is better)
            mean_income = np.mean(weekly_income)
            std_income = np.std(weekly_income)
            
            if mean_income == 0:
                return 0
            
            cv = std_income / mean_income
            
            # Score based on coefficient of variation
            if cv <= 0.2:  # Very stable
                return 100
            elif cv <= 0.4:
                return 80
            elif cv <= 0.6:
                return 60
            elif cv <= 0.8:
                return 40
            else:
                return 20
                
        except Exception as e:
            logger.error(f"Revenue stability calculation failed: {str(e)}")
            return 50
    
    def _calculate_expense_control(self, transactions) -> float:
        """Calculate expense control score"""
        try:
            # Analyze expense trends
            expense_transactions = transactions.filter(transaction_type=TransactionType.EXPENSE)
            
            # Group by month and calculate trend
            monthly_expenses = []
            current_date = timezone.now().date().replace(day=1)
            
            for i in range(3):  # Last 3 months
                month_start = current_date - timedelta(days=30 * i)
                month_end = month_start + timedelta(days=30)
                
                month_expenses = expense_transactions.filter(
                    transaction_date__date__gte=month_start,
                    transaction_date__date__lt=month_end
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                monthly_expenses.append(float(month_expenses))
            
            if len(monthly_expenses) < 2:
                return 50
            
            # Calculate trend (negative slope is good)
            x = np.arange(len(monthly_expenses))
            slope = np.polyfit(x, monthly_expenses, 1)[0]
            
            # Normalize slope relative to average expenses
            avg_expenses = np.mean(monthly_expenses)
            if avg_expenses > 0:
                normalized_slope = slope / avg_expenses
            else:
                return 50
            
            # Score based on expense trend
            if normalized_slope <= -0.1:  # Decreasing expenses
                return 100
            elif normalized_slope <= 0:  # Stable expenses
                return 80
            elif normalized_slope <= 0.05:  # Slight increase
                return 60
            elif normalized_slope <= 0.1:  # Moderate increase
                return 40
            else:  # High increase
                return 20
                
        except Exception as e:
            logger.error(f"Expense control calculation failed: {str(e)}")
            return 50
    
    def _calculate_liquidity_score(self, company: Company) -> float:
        """Calculate liquidity score based on account balances"""
        try:
            accounts = company.accounts.filter(is_active=True)
            total_balance = sum(float(acc.current_balance) for acc in accounts)
            
            # Get recent monthly expenses for comparison
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            monthly_expenses = Transaction.objects.filter(
                company=company,
                transaction_type=TransactionType.EXPENSE,
                transaction_date__gte=start_date,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            if float(monthly_expenses) == 0:
                return 80  # No expenses, good liquidity
            
            # Calculate months of expenses covered
            months_covered = total_balance / float(monthly_expenses)
            
            # Score based on liquidity coverage
            if months_covered >= 6:  # 6+ months
                return 100
            elif months_covered >= 3:  # 3-6 months
                return 80
            elif months_covered >= 1:  # 1-3 months
                return 60
            elif months_covered >= 0.5:  # 2-4 weeks
                return 40
            else:  # Less than 2 weeks
                return 20
                
        except Exception as e:
            logger.error(f"Liquidity score calculation failed: {str(e)}")
            return 50
    
    def _calculate_growth_trajectory(self, transactions) -> float:
        """Calculate growth trajectory score"""
        try:
            # Compare current month with previous months
            current_month_start = timezone.now().date().replace(day=1)
            prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
            
            current_income = transactions.filter(
                transaction_type=TransactionType.INCOME,
                transaction_date__date__gte=current_month_start
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            prev_income = transactions.filter(
                transaction_type=TransactionType.INCOME,
                transaction_date__date__gte=prev_month_start,
                transaction_date__date__lt=current_month_start
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            if float(prev_income) == 0:
                return 50  # Insufficient data
            
            growth_rate = (float(current_income) - float(prev_income)) / float(prev_income)
            
            # Score based on growth rate
            if growth_rate >= 0.2:  # 20%+ growth
                return 100
            elif growth_rate >= 0.1:  # 10-20% growth
                return 85
            elif growth_rate >= 0.05:  # 5-10% growth
                return 70
            elif growth_rate >= 0:  # Positive growth
                return 60
            elif growth_rate >= -0.05:  # Slight decline
                return 45
            elif growth_rate >= -0.1:  # Moderate decline
                return 30
            else:  # Significant decline
                return 15
                
        except Exception as e:
            logger.error(f"Growth trajectory calculation failed: {str(e)}")
            return 50
    
    def _generate_predictions(self, company: Company) -> Dict:
        """Generate financial predictions using ML models"""
        try:
            predictions = {
                'cash_flow': {},
                'revenue': {},
                'expenses': {},
                'account_balances': {}
            }
            
            # Get historical data
            transactions = Transaction.objects.filter(
                company=company,
                status='completed'
            ).order_by('transaction_date')
            
            if transactions.count() < 30:  # Need minimum data
                return {'message': 'Insufficient historical data for predictions'}
            
            # Prepare data for ML models
            df = self._prepare_prediction_data(transactions)
            
            # Generate cash flow predictions
            predictions['cash_flow'] = self._predict_cash_flow(df)
            
            # Generate revenue predictions
            predictions['revenue'] = self._predict_revenue(df)
            
            # Generate expense predictions
            predictions['expenses'] = self._predict_expenses(df)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {str(e)}")
            return {'error': str(e)}
    
    def _prepare_prediction_data(self, transactions) -> pd.DataFrame:
        """Prepare transaction data for ML predictions"""
        data = []
        
        for transaction in transactions:
            data.append({
                'date': transaction.transaction_date.date(),
                'amount': float(transaction.amount),
                'type': transaction.transaction_type,
                'category': transaction.category.name if transaction.category else 'Unknown',
                'day_of_week': transaction.transaction_date.weekday(),
                'month': transaction.transaction_date.month,
                'year': transaction.transaction_date.year,
                'hour': transaction.transaction_date.hour
            })
        
        df = pd.DataFrame(data)
        
        # Group by date and type for daily aggregations
        daily_data = df.groupby(['date', 'type']).agg({
            'amount': 'sum'
        }).reset_index()
        
        # Pivot to get income and expense columns
        daily_pivot = daily_data.pivot(index='date', columns='type', values='amount').fillna(0)
        
        # Add time-based features
        daily_pivot['day_of_week'] = daily_pivot.index.map(lambda x: x.weekday())
        daily_pivot['month'] = daily_pivot.index.map(lambda x: x.month)
        daily_pivot['day_of_month'] = daily_pivot.index.map(lambda x: x.day)
        
        # Add rolling averages
        if 'income' in daily_pivot.columns:
            daily_pivot['income_7d_avg'] = daily_pivot['income'].rolling(7, min_periods=1).mean()
            daily_pivot['income_30d_avg'] = daily_pivot['income'].rolling(30, min_periods=1).mean()
        
        if 'expense' in daily_pivot.columns:
            daily_pivot['expense_7d_avg'] = daily_pivot['expense'].rolling(7, min_periods=1).mean()
            daily_pivot['expense_30d_avg'] = daily_pivot['expense'].rolling(30, min_periods=1).mean()
        
        return daily_pivot
    
    def _predict_cash_flow(self, df: pd.DataFrame) -> Dict:
        """Predict future cash flow"""
        try:
            if 'income' not in df.columns or 'expense' not in df.columns:
                return {'message': 'Insufficient data for cash flow prediction'}
            
            # Calculate daily cash flow
            df['cash_flow'] = df['income'] - df['expense']
            
            # Prepare features and target
            features = ['day_of_week', 'month', 'day_of_month']
            if 'income_7d_avg' in df.columns:
                features.extend(['income_7d_avg', 'expense_7d_avg'])
            
            X = df[features].fillna(0)
            y = df['cash_flow']
            
            if len(X) < 10:
                return {'message': 'Insufficient data for reliable prediction'}
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            
            # Predict next 30 days
            predictions = []
            last_date = df.index.max()
            
            for i in range(1, 31):
                future_date = last_date + timedelta(days=i)
                
                # Create feature vector for future date
                future_features = [
                    future_date.weekday(),  # day_of_week
                    future_date.month,      # month
                    future_date.day,        # day_of_month
                ]
                
                # Add rolling averages if available
                if 'income_7d_avg' in df.columns:
                    future_features.extend([
                        df['income_7d_avg'].iloc[-1],
                        df['expense_7d_avg'].iloc[-1]
                    ])
                
                predicted_cash_flow = model.predict([future_features])[0]
                
                predictions.append({
                    'date': future_date.isoformat(),
                    'predicted_cash_flow': round(predicted_cash_flow, 2)
                })
            
            # Calculate summary statistics
            predicted_values = [p['predicted_cash_flow'] for p in predictions]
            
            return {
                'predictions': predictions,
                'summary': {
                    'avg_daily_cash_flow': round(np.mean(predicted_values), 2),
                    'total_30d_cash_flow': round(sum(predicted_values), 2),
                    'positive_days': sum(1 for v in predicted_values if v > 0),
                    'negative_days': sum(1 for v in predicted_values if v < 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Cash flow prediction failed: {str(e)}")
            return {'error': str(e)}
    
    def _predict_revenue(self, df: pd.DataFrame) -> Dict:
        """Predict future revenue"""
        try:
            if 'income' not in df.columns:
                return {'message': 'No income data available'}
            
            # Group by week for revenue prediction
            weekly_revenue = df.resample('W')['income'].sum()
            
            if len(weekly_revenue) < 4:
                return {'message': 'Insufficient data for revenue prediction'}
            
            # Simple trend-based prediction
            x = np.arange(len(weekly_revenue))
            y = weekly_revenue.values
            
            # Fit linear trend
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs
            
            # Predict next 4 weeks
            predictions = []
            for i in range(1, 5):
                future_week = len(weekly_revenue) + i
                predicted_revenue = slope * future_week + intercept
                
                predictions.append({
                    'week': i,
                    'predicted_revenue': max(0, round(predicted_revenue, 2))
                })
            
            return {
                'weekly_predictions': predictions,
                'trend': 'increasing' if slope > 0 else 'decreasing',
                'weekly_growth_rate': round((slope / np.mean(y)) * 100, 2) if np.mean(y) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Revenue prediction failed: {str(e)}")
            return {'error': str(e)}
    
    def _predict_expenses(self, df: pd.DataFrame) -> Dict:
        """Predict future expenses"""
        try:
            if 'expense' not in df.columns:
                return {'message': 'No expense data available'}
            
            # Similar to revenue prediction but for expenses
            weekly_expenses = df.resample('W')['expense'].sum()
            
            if len(weekly_expenses) < 4:
                return {'message': 'Insufficient data for expense prediction'}
            
            x = np.arange(len(weekly_expenses))
            y = weekly_expenses.values
            
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs
            
            predictions = []
            for i in range(1, 5):
                future_week = len(weekly_expenses) + i
                predicted_expense = slope * future_week + intercept
                
                predictions.append({
                    'week': i,
                    'predicted_expense': max(0, round(predicted_expense, 2))
                })
            
            return {
                'weekly_predictions': predictions,
                'trend': 'increasing' if slope > 0 else 'decreasing',
                'weekly_growth_rate': round((slope / np.mean(y)) * 100, 2) if np.mean(y) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Expense prediction failed: {str(e)}")
            return {'error': str(e)}
    
    def _detect_financial_anomalies(self, company: Company) -> List[Dict]:
        """Detect financial anomalies using AI"""
        try:
            anomalies = []
            
            # Get recent transactions
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            transactions = Transaction.objects.filter(
                company=company,
                transaction_date__gte=start_date,
                status='completed'
            )
            
            # Detect amount anomalies
            amount_anomalies = self._detect_amount_anomalies(transactions)
            anomalies.extend(amount_anomalies)
            
            # Detect frequency anomalies
            frequency_anomalies = self._detect_frequency_anomalies(transactions)
            anomalies.extend(frequency_anomalies)
            
            # Detect pattern anomalies
            pattern_anomalies = self._detect_pattern_anomalies(transactions)
            anomalies.extend(pattern_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            return []
    
    def _analyze_cash_flow(self, company: Company) -> Dict:
        """Analyze cash flow patterns"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            transactions = Transaction.objects.filter(
                company=company,
                transaction_date__gte=start_date,
                status='completed'
            )
            
            # Daily cash flow analysis
            daily_cashflow = {}
            current_date = start_date.date()
            
            while current_date <= end_date.date():
                day_income = transactions.filter(
                    transaction_type=TransactionType.INCOME,
                    transaction_date__date=current_date
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                day_expenses = transactions.filter(
                    transaction_type=TransactionType.EXPENSE,
                    transaction_date__date=current_date
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                net_flow = float(day_income - day_expenses)
                daily_cashflow[current_date.isoformat()] = {
                    'income': float(day_income),
                    'expenses': float(day_expenses),
                    'net_flow': net_flow
                }
                
                current_date += timedelta(days=1)
            
            # Calculate statistics
            net_flows = [day['net_flow'] for day in daily_cashflow.values()]
            positive_days = sum(1 for flow in net_flows if flow > 0)
            negative_days = sum(1 for flow in net_flows if flow < 0)
            
            return {
                'daily_cashflow': daily_cashflow,
                'summary': {
                    'avg_daily_flow': round(np.mean(net_flows), 2),
                    'total_net_flow': round(sum(net_flows), 2),
                    'positive_days': positive_days,
                    'negative_days': negative_days,
                    'volatility': round(np.std(net_flows), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Cash flow analysis failed: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_spending_patterns(self, company: Company) -> Dict:
        """Analyze spending patterns"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            expense_transactions = Transaction.objects.filter(
                company=company,
                transaction_type=TransactionType.EXPENSE,
                transaction_date__gte=start_date,
                status='completed'
            )
            
            # Category analysis
            category_spending = expense_transactions.values(
                'category__name'
            ).annotate(
                total=Sum('amount'),
                count=Count('id'),
                avg=Avg('amount')
            ).order_by('-total')
            
            # Time pattern analysis
            hourly_spending = expense_transactions.extra(
                select={'hour': 'EXTRACT(hour FROM transaction_date)'}
            ).values('hour').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('hour')
            
            # Day of week analysis
            dow_spending = expense_transactions.extra(
                select={'dow': 'EXTRACT(dow FROM transaction_date)'}
            ).values('dow').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('dow')
            
            return {
                'by_category': list(category_spending),
                'by_hour': list(hourly_spending),
                'by_day_of_week': list(dow_spending),
                'total_expenses': float(
                    expense_transactions.aggregate(total=Sum('amount'))['total'] or 0
                ),
                'transaction_count': expense_transactions.count()
            }
            
        except Exception as e:
            logger.error(f"Spending pattern analysis failed: {str(e)}")
            return {'error': str(e)}
    
    def _assess_financial_risks(self, company: Company) -> Dict:
        """Assess various financial risks"""
        try:
            risks = {
                'liquidity_risk': 'low',
                'concentration_risk': 'low',
                'volatility_risk': 'low',
                'growth_risk': 'low',
                'overall_risk': 'low'
            }
            
            # Assess liquidity risk
            liquidity_score = self._calculate_liquidity_score(company)
            if liquidity_score < 40:
                risks['liquidity_risk'] = 'high'
            elif liquidity_score < 60:
                risks['liquidity_risk'] = 'medium'
            
            # Assess income concentration risk
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            income_by_source = Transaction.objects.filter(
                company=company,
                transaction_type=TransactionType.INCOME,
                transaction_date__gte=start_date
            ).values('description').annotate(
                total=Sum('amount')
            ).order_by('-total')
            
            if income_by_source:
                total_income = sum(float(item['total']) for item in income_by_source)
                if total_income > 0:
                    top_source_pct = float(income_by_source[0]['total']) / total_income
                    if top_source_pct > 0.8:
                        risks['concentration_risk'] = 'high'
                    elif top_source_pct > 0.6:
                        risks['concentration_risk'] = 'medium'
            
            # Calculate overall risk
            risk_scores = {
                'low': 1,
                'medium': 2,
                'high': 3
            }
            
            avg_risk = np.mean([
                risk_scores[risks['liquidity_risk']],
                risk_scores[risks['concentration_risk']],
                risk_scores[risks['volatility_risk']],
                risk_scores[risks['growth_risk']]
            ])
            
            if avg_risk >= 2.5:
                risks['overall_risk'] = 'high'
            elif avg_risk >= 1.5:
                risks['overall_risk'] = 'medium'
            
            return risks
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {str(e)}")
            return {'error': str(e)}
    
    def _generate_ai_recommendations(self, company: Company, insights: Dict) -> List[Dict]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        try:
            health_score = insights.get('health_score', {}).get('score', 0)
            cash_flow = insights.get('cash_flow_analysis', {})
            risks = insights.get('risk_assessment', {})
            
            # Health score based recommendations
            if health_score < 60:
                recommendations.append({
                    'type': 'urgent',
                    'category': 'financial_health',
                    'title': 'Improve Financial Health',
                    'description': 'Your financial health score is below optimal. Consider reviewing expenses and increasing income.',
                    'priority': 'high',
                    'impact': 'high'
                })
            
            # Cash flow recommendations
            if cash_flow.get('summary', {}).get('negative_days', 0) > 10:
                recommendations.append({
                    'type': 'operational',
                    'category': 'cash_flow',
                    'title': 'Address Cash Flow Issues',
                    'description': 'You have frequent negative cash flow days. Consider improving payment collection or managing expenses.',
                    'priority': 'high',
                    'impact': 'high'
                })
            
            # Risk-based recommendations
            if risks.get('liquidity_risk') == 'high':
                recommendations.append({
                    'type': 'strategic',
                    'category': 'liquidity',
                    'title': 'Build Emergency Fund',
                    'description': 'Your liquidity risk is high. Consider building an emergency fund covering 3-6 months of expenses.',
                    'priority': 'high',
                    'impact': 'medium'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            return []
    
    def _find_optimization_opportunities(self, company: Company) -> List[Dict]:
        """Find opportunities for financial optimization"""
        opportunities = []
        
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            # Expense optimization opportunities
            expense_categories = Transaction.objects.filter(
                company=company,
                transaction_type=TransactionType.EXPENSE,
                transaction_date__gte=start_date
            ).values('category__name').annotate(
                total=Sum('amount'),
                count=Count('id'),
                avg=Avg('amount')
            ).order_by('-total')
            
            # Find categories with high spending
            for category in expense_categories[:5]:  # Top 5 categories
                total_spent = float(category['total'])
                if total_spent > 1000:  # Significant spending
                    opportunities.append({
                        'type': 'cost_reduction',
                        'category': category['category__name'] or 'Uncategorized',
                        'current_spending': total_spent,
                        'potential_savings': round(total_spent * 0.1, 2),  # 10% reduction
                        'description': f"Review and optimize spending in {category['category__name']} category"
                    })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Optimization opportunity analysis failed: {str(e)}")
            return []


# Initialize the advanced AI engine
advanced_ai_engine = AdvancedAIEngine()
