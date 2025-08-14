import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from django.conf import settings
from django.db.models import Sum, Count, Avg, Q
from .models import Company, Account, Transaction, TransactionCategory, BulkUpload


class FinancialDataRAG:
    """RAG system for analyzing financial data from CSV uploads using LlamaIndex"""
    
    def __init__(self, openai_api_key: str = None):
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        
        # Configure LlamaIndex settings for GitHub Models API
        Settings.llm = OpenAI(
            api_key=self.api_key, 
            model="gpt-3.5-turbo", 
            temperature=0.7,
            api_base="https://models.github.ai/inference"
        )
        Settings.embed_model = OpenAIEmbedding(
            api_key=self.api_key,
            api_base="https://models.github.ai/inference"
        )
        
        self.index = None
        self.query_engine = None
        
    def analyze_bulk_upload(self, bulk_upload: BulkUpload) -> Dict[str, Any]:
        """Analyze a bulk upload and provide comprehensive insights"""
        
        company = bulk_upload.company
        upload_type = bulk_upload.upload_type
        
        # Get data based on upload type
        if upload_type == 'transactions':
            return self._analyze_transaction_upload(company, bulk_upload)
        elif upload_type == 'accounts':
            return self._analyze_account_upload(company, bulk_upload)
        elif upload_type == 'categories':
            return self._analyze_category_upload(company, bulk_upload)
        else:
            return {'error': f'Unsupported upload type: {upload_type}'}
    
    def _analyze_transaction_upload(self, company: Company, bulk_upload: BulkUpload) -> Dict[str, Any]:
        """Analyze transaction data upload and provide insights"""
        
        # Get recent transactions (last 30 days from upload)
        end_date = bulk_upload.created_at.date()
        start_date = end_date - timedelta(days=30)
        
        transactions = Transaction.objects.filter(
            account__company=company,
            date__range=[start_date, end_date]
        ).select_related('account', 'category')
        
        if not transactions.exists():
            return {'error': 'No transactions found for analysis'}
        
        # Convert to DataFrame for analysis
        transaction_data = []
        for txn in transactions:
            transaction_data.append({
                'id': str(txn.id),
                'account': txn.account.name,
                'amount': float(txn.amount),
                'description': txn.description,
                'date': txn.transaction_date.isoformat(),
                'type': txn.transaction_type,
                'category': txn.category.name if txn.category else 'Uncategorized',
                'reference': txn.reference_number or '',
                'tags': txn.tags or ''
            })
        
        df = pd.DataFrame(transaction_data)
        
        # Perform statistical analysis
        stats = self._calculate_transaction_statistics(df)
        
        # Create vector store from transaction data
        documents = self._create_transaction_documents(df)
        self.index = VectorStoreIndex.from_documents(documents)
        self.query_engine = self.index.as_query_engine()
        
        # Generate insights using RAG
        insights = self._generate_transaction_insights(df, stats)
        
        # Get recommendations
        recommendations = self._get_transaction_recommendations(df, stats)
        
        # Identify areas for improvement
        improvements = self._identify_improvement_areas(df, stats)
        
        return {
            'upload_info': {
                'upload_id': str(bulk_upload.id),
                'upload_type': bulk_upload.upload_type,
                'total_rows': bulk_upload.total_rows,
                'successful_rows': bulk_upload.successful_rows,
                'analysis_period': f"{start_date} to {end_date}"
            },
            'statistics': stats,
            'insights': insights,
            'recommendations': recommendations,
            'improvement_areas': improvements,
            'summary': self._generate_executive_summary(stats, insights, recommendations)
        }
    
    def _calculate_transaction_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive transaction statistics"""
        
        stats = {
            'total_transactions': len(df),
            'total_amount': float(df['amount'].sum()),
            'average_transaction': float(df['amount'].mean()),
            'median_transaction': float(df['amount'].median()),
            'largest_transaction': float(df['amount'].max()),
            'smallest_transaction': float(df['amount'].min()),
        }
        
        # Income vs Expense breakdown
        income_txns = df[df['amount'] > 0]
        expense_txns = df[df['amount'] < 0]
        
        stats['income'] = {
            'total': float(income_txns['amount'].sum()),
            'count': len(income_txns),
            'average': float(income_txns['amount'].mean()) if len(income_txns) > 0 else 0
        }
        
        stats['expenses'] = {
            'total': float(abs(expense_txns['amount'].sum())),
            'count': len(expense_txns),
            'average': float(abs(expense_txns['amount'].mean())) if len(expense_txns) > 0 else 0
        }
        
        stats['net_cash_flow'] = stats['income']['total'] - stats['expenses']['total']
        
        # Category analysis
        category_stats = df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean']
        }).round(2)
        
        stats['top_expense_categories'] = []
        expense_categories = df[df['amount'] < 0].groupby('category')['amount'].sum().abs().sort_values(ascending=False)
        for category, amount in expense_categories.head(5).items():
            stats['top_expense_categories'].append({
                'category': category,
                'amount': float(amount),
                'percentage': float((amount / stats['expenses']['total']) * 100)
            })
        
        # Account analysis
        account_stats = df.groupby('account').agg({
            'amount': ['sum', 'count']
        }).round(2)
        
        stats['account_activity'] = []
        for account in df['account'].unique():
            account_data = df[df['account'] == account]
            stats['account_activity'].append({
                'account': account,
                'transaction_count': len(account_data),
                'total_amount': float(account_data['amount'].sum()),
                'average_amount': float(account_data['amount'].mean())
            })
        
        # Temporal patterns
        df['date'] = pd.to_datetime(df['date'])
        daily_totals = df.groupby(df['date'].dt.date)['amount'].sum()
        
        stats['temporal_patterns'] = {
            'daily_average': float(daily_totals.mean()),
            'most_active_day': daily_totals.idxmax().isoformat(),
            'highest_spending_day': daily_totals.idxmin().isoformat(),
            'days_with_transactions': len(daily_totals)
        }
        
        return stats
    
    def _create_transaction_documents(self, df: pd.DataFrame) -> List[Document]:
        """Create documents for vector store from transaction data"""
        
        documents = []
        
        # Create summary documents
        for category in df['category'].unique():
            category_data = df[df['category'] == category]
            total_amount = category_data['amount'].sum()
            count = len(category_data)
            avg_amount = category_data['amount'].mean()
            
            content = f"""
            Category: {category}
            Total transactions: {count}
            Total amount: ${total_amount:.2f}
            Average amount: ${avg_amount:.2f}
            Transaction type: {"Income" if total_amount > 0 else "Expense"}
            
            Sample descriptions:
            {category_data['description'].head(3).tolist()}
            """
            
            documents.append(Document(
                text=content,
                metadata={'type': 'category_summary', 'category': category}
            ))
        
        # Create account documents
        for account in df['account'].unique():
            account_data = df[df['account'] == account]
            total_amount = account_data['amount'].sum()
            count = len(account_data)
            
            content = f"""
            Account: {account}
            Total transactions: {count}
            Net amount: ${total_amount:.2f}
            Most common categories: {account_data['category'].value_counts().head(3).to_dict()}
            """
            
            documents.append(Document(
                text=content,
                metadata={'type': 'account_summary', 'account': account}
            ))
        
        return documents
    
    def _generate_transaction_insights(self, df: pd.DataFrame, stats: Dict[str, Any]) -> List[str]:
        """Generate AI-powered insights from transaction data"""
        
        insights = []
        
        # Cash flow insights
        if stats['net_cash_flow'] > 0:
            insights.append(f"Positive cash flow of ${stats['net_cash_flow']:.2f} indicates healthy financial position.")
        else:
            insights.append(f"Negative cash flow of ${abs(stats['net_cash_flow']):.2f} requires attention to spending patterns.")
        
        # Spending pattern insights
        if stats['expenses']['average'] > stats['income']['average']:
            insights.append("Average expense amount exceeds average income amount, suggesting frequent small expenses.")
        
        # Category insights
        if stats['top_expense_categories']:
            top_category = stats['top_expense_categories'][0]
            insights.append(f"'{top_category['category']}' is the largest expense category, representing {top_category['percentage']:.1f}% of total expenses.")
        
        # Transaction frequency insights
        total_days = (pd.to_datetime(df['date']).max() - pd.to_datetime(df['date']).min()).days + 1
        avg_transactions_per_day = stats['total_transactions'] / total_days
        
        if avg_transactions_per_day > 5:
            insights.append("High transaction frequency suggests active financial management or potentially frequent small purchases.")
        elif avg_transactions_per_day < 1:
            insights.append("Low transaction frequency might indicate infrequent account usage or batch transaction processing.")
        
        return insights
    
    def _get_transaction_recommendations(self, df: pd.DataFrame, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on transaction analysis"""
        
        recommendations = []
        
        # Cash flow recommendations
        if stats['net_cash_flow'] < 0:
            recommendations.append("Consider reviewing and reducing expenses in top spending categories to improve cash flow.")
        
        # Category-based recommendations
        if len(stats['top_expense_categories']) > 0:
            top_category = stats['top_expense_categories'][0]
            if top_category['percentage'] > 40:
                recommendations.append(f"Consider diversifying expenses as '{top_category['category']}' dominates your spending.")
        
        # Uncategorized transactions
        uncategorized_count = len(df[df['category'] == 'Uncategorized'])
        if uncategorized_count > 0:
            percentage = (uncategorized_count / len(df)) * 100
            recommendations.append(f"Categorize {uncategorized_count} uncategorized transactions ({percentage:.1f}%) for better expense tracking.")
        
        # Budget recommendations
        if stats['expenses']['total'] > 0:
            recommendations.append("Set up budgets for your top expense categories to control spending.")
            recommendations.append("Consider implementing automated savings transfers for positive cash flow periods.")
        
        return recommendations
    
    def _identify_improvement_areas(self, df: pd.DataFrame, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify specific areas for financial improvement"""
        
        improvements = []
        
        # Expense optimization
        if len(stats['top_expense_categories']) > 0:
            for category in stats['top_expense_categories'][:3]:
                improvements.append({
                    'area': 'Expense Optimization',
                    'category': category['category'],
                    'current_spending': category['amount'],
                    'suggestion': f"Reduce {category['category']} spending by 10-20%",
                    'potential_savings': category['amount'] * 0.15,
                    'priority': 'High' if category['percentage'] > 30 else 'Medium'
                })
        
        # Cash flow improvement
        if stats['net_cash_flow'] < 0:
            improvements.append({
                'area': 'Cash Flow Management',
                'category': 'Overall',
                'current_deficit': abs(stats['net_cash_flow']),
                'suggestion': 'Increase income or reduce expenses to achieve positive cash flow',
                'target_improvement': abs(stats['net_cash_flow']) * 1.2,
                'priority': 'Critical'
            })
        
        # Transaction management
        uncategorized_percentage = (len(df[df['category'] == 'Uncategorized']) / len(df)) * 100
        if uncategorized_percentage > 20:
            improvements.append({
                'area': 'Transaction Management',
                'category': 'Categorization',
                'current_rate': f"{uncategorized_percentage:.1f}% uncategorized",
                'suggestion': 'Implement better transaction categorization practices',
                'target_improvement': 'Reduce to under 10% uncategorized',
                'priority': 'Medium'
            })
        
        return improvements
    
    def _generate_executive_summary(self, stats: Dict[str, Any], insights: List[str], 
                                   recommendations: List[str]) -> str:
        """Generate an executive summary of the financial analysis"""
        
        summary_parts = [
            f"Financial Analysis Summary:",
            f"• Total transactions analyzed: {stats['total_transactions']}",
            f"• Net cash flow: ${stats['net_cash_flow']:.2f}",
            f"• Total income: ${stats['income']['total']:.2f}",
            f"• Total expenses: ${stats['expenses']['total']:.2f}",
            "",
            "Key Insights:",
        ]
        
        for insight in insights[:3]:  # Top 3 insights
            summary_parts.append(f"• {insight}")
        
        summary_parts.extend([
            "",
            "Priority Recommendations:",
        ])
        
        for rec in recommendations[:3]:  # Top 3 recommendations
            summary_parts.append(f"• {rec}")
        
        return "\n".join(summary_parts)
    
    def _analyze_account_upload(self, company: Company, bulk_upload: BulkUpload) -> Dict[str, Any]:
        """Analyze account data upload"""
        
        accounts = company.accounts.filter(is_active=True)
        
        if not accounts.exists():
            return {'error': 'No accounts found for analysis'}
        
        # Basic account analysis
        total_balance = sum(account.current_balance for account in accounts)
        account_types = {}
        
        for account in accounts:
            account_type = account.account_type
            if account_type not in account_types:
                account_types[account_type] = {'count': 0, 'total_balance': 0}
            account_types[account_type]['count'] += 1
            account_types[account_type]['total_balance'] += account.current_balance
        
        return {
            'upload_info': {
                'upload_id': str(bulk_upload.id),
                'upload_type': bulk_upload.upload_type,
                'successful_rows': bulk_upload.successful_rows
            },
            'account_summary': {
                'total_accounts': accounts.count(),
                'total_balance': float(total_balance),
                'account_types': account_types
            },
            'insights': [
                f"Portfolio consists of {accounts.count()} active accounts",
                f"Total portfolio value: ${total_balance:,.2f}",
                f"Account diversification across {len(account_types)} different types"
            ],
            'recommendations': [
                "Monitor account balances regularly for optimal cash management",
                "Consider consolidating accounts if managing multiple similar account types",
                "Ensure adequate emergency fund coverage across liquid accounts"
            ]
        }
    
    def _analyze_category_upload(self, company: Company, bulk_upload: BulkUpload) -> Dict[str, Any]:
        """Analyze category data upload"""
        
        categories = TransactionCategory.objects.filter(company=company, is_active=True)
        
        income_categories = categories.filter(category_type='income').count()
        expense_categories = categories.filter(category_type='expense').count()
        
        return {
            'upload_info': {
                'upload_id': str(bulk_upload.id),
                'upload_type': bulk_upload.upload_type,
                'successful_rows': bulk_upload.successful_rows
            },
            'category_summary': {
                'total_categories': categories.count(),
                'income_categories': income_categories,
                'expense_categories': expense_categories
            },
            'insights': [
                f"Budget structure includes {categories.count()} active categories",
                f"Income tracking across {income_categories} categories",
                f"Expense tracking across {expense_categories} categories"
            ],
            'recommendations': [
                "Ensure all major expense types have dedicated categories",
                "Review category usage regularly and deactivate unused ones",
                "Consider subcategories for detailed expense tracking in major areas"
            ]
        }
    
    def query_financial_data(self, query: str, company: Company) -> str:
        """Query financial data using RAG system"""
        
        if not self.index:
            # Build vector store from recent company data
            self._build_company_vector_store(company)
        
        if not self.index:
            return "No financial data available for analysis."
        
        # Query the system using LlamaIndex
        response = self.query_engine.query(query)
        return str(response)
    
    def _build_company_vector_store(self, company: Company):
        """Build vector store from company's financial data"""
        
        documents = []
        
        # Add account summaries
        for account in company.accounts.filter(is_active=True):
            content = f"""
            Account: {account.name}
            Type: {account.account_type}
            Balance: ${account.current_balance:.2f}
            Bank: {account.bank_name or 'N/A'}
            """
            documents.append(Document(
                text=content,
                metadata={'type': 'account', 'account_id': str(account.id)}
            ))
        
        # Add recent transaction summaries
        recent_transactions = Transaction.objects.filter(
            account__company=company,
            transaction_date__gte=datetime.now().date() - timedelta(days=30)
        )[:100]  # Limit to recent 100 transactions
        
        for txn in recent_transactions:
            content = f"""
            Transaction: {txn.description}
            Amount: ${txn.amount}
            Date: {txn.transaction_date}
            Account: {txn.account.name}
            Category: {txn.category.name if txn.category else 'Uncategorized'}
            """
            documents.append(Document(
                text=content,
                metadata={'type': 'transaction', 'transaction_id': str(txn.id)}
            ))
        
        if documents:
            self.index = VectorStoreIndex.from_documents(documents)
            self.query_engine = self.index.as_query_engine()
