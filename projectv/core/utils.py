from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from .models import (
    Company, Account, Transaction, TransactionType, 
    TransactionStatus, AccountType
)


class FinancialAnalytics:
    """Utility class for financial analytics and calculations"""
    
    def __init__(self, company):
        self.company = company
    
    def get_cash_flow_analysis(self, start_date=None, end_date=None):
        """Analyze cash flow for a given period"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        transactions = Transaction.objects.filter(
            company=self.company,
            status=TransactionStatus.COMPLETED,
            transaction_date__range=[start_date, end_date]
        )
        
        income = transactions.filter(
            transaction_type=TransactionType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        expenses = transactions.filter(
            transaction_type=TransactionType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        net_cash_flow = income - expenses
        
        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_income': income,
            'total_expenses': expenses,
            'net_cash_flow': net_cash_flow,
            'cash_flow_ratio': (income / expenses) if expenses > 0 else 0,
            'transaction_count': transactions.count()
        }
    
    def get_account_balances_summary(self):
        """Get summary of all account balances"""
        accounts = self.company.accounts.filter(is_active=True)
        
        summary = {
            'total_assets': Decimal('0'),
            'total_liabilities': Decimal('0'),
            'checking_balance': Decimal('0'),
            'savings_balance': Decimal('0'),
            'credit_card_debt': Decimal('0'),
            'investment_balance': Decimal('0'),
        }
        
        for account in accounts:
            balance = account.current_balance
            
            if account.account_type in [AccountType.CHECKING, AccountType.SAVINGS, 
                                      AccountType.CASH, AccountType.PAYPAL, AccountType.STRIPE]:
                summary['total_assets'] += balance
                if account.account_type == AccountType.CHECKING:
                    summary['checking_balance'] += balance
                elif account.account_type == AccountType.SAVINGS:
                    summary['savings_balance'] += balance
            
            elif account.account_type == AccountType.CREDIT_CARD:
                summary['total_liabilities'] += abs(balance)  # Credit card balances are typically negative
                summary['credit_card_debt'] += abs(balance)
            
            elif account.account_type == AccountType.LOAN:
                summary['total_liabilities'] += abs(balance)
            
            elif account.account_type == AccountType.INVESTMENT:
                summary['total_assets'] += balance
                summary['investment_balance'] += balance
        
        summary['net_worth'] = summary['total_assets'] - summary['total_liabilities']
        
        return summary
    
    def get_category_spending_analysis(self, start_date=None, end_date=None, limit=10):
        """Analyze spending by category"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        category_stats = Transaction.objects.filter(
            company=self.company,
            status=TransactionStatus.COMPLETED,
            transaction_type=TransactionType.EXPENSE,
            transaction_date__range=[start_date, end_date]
        ).values(
            'category__id', 'category__name'
        ).annotate(
            total_amount=Sum('amount'),
            transaction_count=Count('id'),
            avg_amount=Avg('amount')
        ).order_by('-total_amount')[:limit]
        
        total_expenses = sum(stat['total_amount'] or 0 for stat in category_stats)
        
        # Add percentage calculation
        for stat in category_stats:
            if total_expenses > 0:
                stat['percentage_of_total'] = (stat['total_amount'] / total_expenses) * 100
            else:
                stat['percentage_of_total'] = 0
        
        return list(category_stats)
    
    def calculate_financial_health_score(self):
        """Calculate overall financial health score (0-100)"""
        score = 0
        factors = []
        
        # Factor 1: Cash Flow (25 points)
        cash_flow = self.get_cash_flow_analysis()
        if cash_flow['net_cash_flow'] > 0:
            score += 25
            factors.append(("Positive cash flow", 25))
        elif cash_flow['net_cash_flow'] >= 0:
            score += 15
            factors.append(("Break-even cash flow", 15))
        else:
            factors.append(("Negative cash flow", 0))
        
        # Factor 2: Account Balance Diversity (15 points)
        balances = self.get_account_balances_summary()
        active_accounts = self.company.accounts.filter(is_active=True).count()
        if active_accounts >= 3:
            score += 15
            factors.append(("Good account diversity", 15))
        elif active_accounts >= 2:
            score += 10
            factors.append(("Moderate account diversity", 10))
        else:
            score += 5
            factors.append(("Limited account diversity", 5))
        
        # Factor 3: Debt-to-Asset Ratio (20 points)
        if balances['total_assets'] > 0:
            debt_ratio = balances['total_liabilities'] / balances['total_assets']
            if debt_ratio <= 0.3:
                score += 20
                factors.append(("Low debt ratio", 20))
            elif debt_ratio <= 0.5:
                score += 15
                factors.append(("Moderate debt ratio", 15))
            elif debt_ratio <= 0.7:
                score += 10
                factors.append(("High debt ratio", 10))
            else:
                score += 5
                factors.append(("Very high debt ratio", 5))
        
        # Factor 4: Emergency Fund (15 points)
        monthly_expenses = abs(cash_flow['total_expenses'])
        emergency_fund = balances['savings_balance']
        if monthly_expenses > 0:
            months_covered = emergency_fund / monthly_expenses
            if months_covered >= 6:
                score += 15
                factors.append(("Strong emergency fund", 15))
            elif months_covered >= 3:
                score += 10
                factors.append(("Adequate emergency fund", 10))
            elif months_covered >= 1:
                score += 5
                factors.append(("Minimal emergency fund", 5))
            else:
                factors.append(("No emergency fund", 0))
        
        # Factor 5: Transaction Regularity (10 points)
        recent_transactions = Transaction.objects.filter(
            company=self.company,
            status=TransactionStatus.COMPLETED,
            transaction_date__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if recent_transactions >= 20:
            score += 10
            factors.append(("Active transaction history", 10))
        elif recent_transactions >= 10:
            score += 7
            factors.append(("Moderate transaction activity", 7))
        elif recent_transactions >= 5:
            score += 5
            factors.append(("Low transaction activity", 5))
        else:
            factors.append(("Very low transaction activity", 0))
        
        # Factor 6: Budget Adherence (15 points)
        # This would require budget tracking implementation
        # For now, give partial points if budgets exist
        budget_count = self.company.budgets.filter(is_active=True).count()
        if budget_count >= 3:
            score += 15
            factors.append(("Good budget planning", 15))
        elif budget_count >= 1:
            score += 10
            factors.append(("Basic budget planning", 10))
        else:
            score += 5
            factors.append(("No budget planning", 5))
        
        return {
            'score': min(score, 100),  # Cap at 100
            'factors': factors,
            'level': self._get_health_level(score),
            'recommendations': self._get_recommendations(score, balances, cash_flow)
        }
    
    def _get_health_level(self, score):
        """Get financial health level based on score"""
        if score >= 80:
            return "Excellent"
        elif score >= 65:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 35:
            return "Poor"
        else:
            return "Critical"
    
    def _get_recommendations(self, score, balances, cash_flow):
        """Generate recommendations based on financial analysis"""
        recommendations = []
        
        if cash_flow['net_cash_flow'] <= 0:
            recommendations.append("Focus on increasing income or reducing expenses to achieve positive cash flow")
        
        if balances['total_liabilities'] > balances['total_assets'] * 0.5:
            recommendations.append("Consider reducing debt to improve your debt-to-asset ratio")
        
        monthly_expenses = abs(cash_flow['total_expenses'])
        if balances['savings_balance'] < monthly_expenses * 3:
            recommendations.append("Build an emergency fund covering 3-6 months of expenses")
        
        if score < 50:
            recommendations.append("Review and optimize your financial strategy with a financial advisor")
        
        active_accounts = self.company.accounts.filter(is_active=True).count()
        if active_accounts < 2:
            recommendations.append("Consider diversifying your accounts for better financial management")
        
        return recommendations
    
    def detect_anomalies(self, start_date=None, end_date=None):
        """Detect anomalous transactions using simple statistical methods"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=90)  # Look at 90 days of data
        if not end_date:
            end_date = timezone.now()
        
        transactions = Transaction.objects.filter(
            company=self.company,
            status=TransactionStatus.COMPLETED,
            transaction_date__range=[start_date, end_date]
        )
        
        anomalies = []
        
        # Check for unusually large transactions
        for transaction_type in [TransactionType.INCOME, TransactionType.EXPENSE]:
            type_transactions = transactions.filter(transaction_type=transaction_type)
            
            if type_transactions.count() < 10:  # Need enough data
                continue
            
            amounts = [t.amount for t in type_transactions]
            avg_amount = sum(amounts) / len(amounts)
            
            # Simple anomaly detection: transactions > 3x average
            threshold = avg_amount * 3
            
            large_transactions = type_transactions.filter(amount__gt=threshold)
            for transaction in large_transactions:
                anomalies.append({
                    'transaction': transaction,
                    'reason': f'Amount {transaction.amount} is {transaction.amount/avg_amount:.1f}x the average',
                    'confidence': min(0.9, (transaction.amount / avg_amount) / 10)
                })
        
        return anomalies
