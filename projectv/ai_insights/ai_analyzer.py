import openai
from langchain_openai import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from django.conf import settings
import logging
from core.models import Transaction, TransactionCategory, Company, Account, Budget
from ai_insights.models import (
    FinancialHealthScore, AnomalyDetection, SmartCategorization, 
    BudgetInsight, FinancialGoalRecommendation, AIAnalysisLog
)
from decimal import Decimal
import json
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q

logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')

class TransactionCategorization(BaseModel):
    category: str = Field(description="Best matching category for the transaction")
    confidence: float = Field(description="Confidence score between 0-1")
    reasoning: str = Field(description="Why this category was chosen")

class AnomalyAnalysis(BaseModel):
    is_anomaly: bool = Field(description="Whether transaction is anomalous")
    anomaly_type: str = Field(description="Type of anomaly detected")
    risk_level: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL")
    explanation: str = Field(description="Detailed explanation of the anomaly")
    confidence: float = Field(description="Confidence score between 0-1")

class FinancialInsight(BaseModel):
    insight_type: str = Field(description="Type of insight")
    title: str = Field(description="Short insight title")
    message: str = Field(description="Human-readable insight message")
    severity: str = Field(description="INFO, WARNING, CRITICAL")
    recommended_action: str = Field(description="What user should do")
    impact_score: float = Field(description="Impact score between 0-1")

class FinancialGoalSuggestion(BaseModel):
    name: str = Field(description="Goal name")
    goal_type: str = Field(description="SAVINGS, REVENUE, EXPENSE_REDUCTION, EMERGENCY_FUND, INVESTMENT")
    target_amount: float = Field(description="Target amount")
    timeframe_months: int = Field(description="Recommended timeframe in months")
    description: str = Field(description="Goal description")
    why_important: str = Field(description="Why this goal is important")
    confidence: float = Field(description="AI confidence in recommendation")

class AIFinancialAnalyzer:
    def __init__(self):
        self.openai_key = getattr(settings, 'OPENAI_API_KEY', '')
        if not self.openai_key or self.openai_key == 'your-openai-key-here':
            logger.warning("OpenAI API key not configured. AI features will be limited.")
            self.llm = None
        else:
            try:
                self.llm = OpenAI(
                    temperature=0.1,
                    openai_api_key=self.openai_key,
                    model_name="gpt-3.5-turbo-instruct",
                    max_tokens=500
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.llm = None
    
    def _log_operation(self, company_id: int, operation_type: str, status: str, 
                      processing_time: float, error_message: str = "", tokens_used: int = 0, 
                      metadata: dict = None):
        """Log AI operation for tracking and debugging"""
        try:
            AIAnalysisLog.objects.create(
                company_id=company_id,
                operation_type=operation_type,
                status=status,
                processing_time=processing_time,
                tokens_used=tokens_used,
                error_message=error_message,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to log AI operation: {e}")
    
    def categorize_transaction(self, transaction: Transaction) -> SmartCategorization:
        """AI-powered transaction categorization"""
        start_time = time.time()
        
        if not self.llm:
            return self._fallback_categorization(transaction)
        
        try:
            # Get existing categories for context
            categories = list(TransactionCategory.objects.filter(
                company=transaction.company,
                is_active=True
            ).values_list('name', flat=True)[:20])
            
            parser = PydanticOutputParser(pydantic_object=TransactionCategorization)
            
            prompt = PromptTemplate(
                template="""
                Analyze this financial transaction and categorize it:
                
                Description: {description}
                Amount: ${amount}
                Transaction Type: {transaction_type}
                Date: {date}
                
                Available Categories: {categories}
                
                Consider:
                - Keywords in the description
                - Transaction amount patterns
                - Common business/expense patterns
                - Transaction type (income/expense)
                
                Choose the most appropriate category from the available list.
                If none fit well, suggest "Uncategorized".
                
                {format_instructions}
                """,
                input_variables=["description", "amount", "transaction_type", "date", "categories"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            result = chain.run(
                description=transaction.description or "No description",
                amount=float(transaction.amount),
                transaction_type=transaction.transaction_type,
                date=transaction.transaction_date.strftime("%Y-%m-%d"),
                categories=", ".join(categories) if categories else "No categories available"
            )
            
            categorization_result = parser.parse(result)
            
            # Find the suggested category
            suggested_category = TransactionCategory.objects.filter(
                company=transaction.company,
                name__icontains=categorization_result.category,
                is_active=True
            ).first()
            
            if not suggested_category:
                # Create or get "Uncategorized" category
                suggested_category, _ = TransactionCategory.objects.get_or_create(
                    company=transaction.company,
                    name="Uncategorized",
                    defaults={'is_income': transaction.transaction_type == 'INCOME'}
                )
            
            # Create SmartCategorization record
            smart_cat, created = SmartCategorization.objects.get_or_create(
                transaction=transaction,
                defaults={
                    'suggested_category': suggested_category,
                    'confidence_score': categorization_result.confidence,
                    'reasoning': categorization_result.reasoning,
                }
            )
            
            processing_time = time.time() - start_time
            self._log_operation(
                transaction.company.id, 
                'CATEGORIZATION', 
                'SUCCESS', 
                processing_time,
                tokens_used=len(result.split()) * 2  # Rough estimate
            )
            
            return smart_cat
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Categorization error: {e}")
            self._log_operation(
                transaction.company.id, 
                'CATEGORIZATION', 
                'FAILED', 
                processing_time,
                error_message=str(e)
            )
            return self._fallback_categorization(transaction)
    
    def _fallback_categorization(self, transaction: Transaction) -> SmartCategorization:
        """Fallback categorization when AI is unavailable"""
        # Simple rule-based categorization
        description = transaction.description.lower() if transaction.description else ""
        
        # Basic keyword matching
        category_keywords = {
            'Marketing': ['google', 'facebook', 'ads', 'marketing', 'social media'],
            'Office Supplies': ['office', 'supplies', 'stationary', 'printer'],
            'Software': ['software', 'subscription', 'saas', 'license'],
            'Travel': ['travel', 'hotel', 'flight', 'uber', 'taxi'],
            'Food': ['restaurant', 'food', 'lunch', 'dinner', 'coffee'],
        }
        
        suggested_category_name = "Uncategorized"
        for category, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                suggested_category_name = category
                break
        
        # Get or create category
        suggested_category, _ = TransactionCategory.objects.get_or_create(
            company=transaction.company,
            name=suggested_category_name,
            defaults={'is_income': transaction.transaction_type == 'INCOME'}
        )
        
        smart_cat, created = SmartCategorization.objects.get_or_create(
            transaction=transaction,
            defaults={
                'suggested_category': suggested_category,
                'confidence_score': 0.5,
                'reasoning': "Rule-based categorization (AI unavailable)",
            }
        )
        
        return smart_cat
    
    def detect_anomaly(self, transaction: Transaction) -> Optional[AnomalyDetection]:
        """AI-powered anomaly detection"""
        start_time = time.time()
        
        try:
            # Get historical transaction data
            historical_transactions = Transaction.objects.filter(
                company=transaction.company,
                transaction_date__lt=transaction.transaction_date,
                status='COMPLETED'
            ).order_by('-transaction_date')[:50]
            
            if historical_transactions.count() < 5:
                # Not enough data for anomaly detection
                return None
            
            # Calculate basic statistics
            amounts = [float(t.amount) for t in historical_transactions]
            avg_amount = np.mean(amounts)
            std_amount = np.std(amounts)
            max_amount = np.max(amounts)
            
            # Simple statistical anomaly detection
            current_amount = float(transaction.amount)
            z_score = abs((current_amount - avg_amount) / std_amount) if std_amount > 0 else 0
            
            is_statistical_anomaly = z_score > 2  # More than 2 standard deviations
            
            if not self.llm and not is_statistical_anomaly:
                return None
            
            if self.llm:
                # AI-powered anomaly detection
                historical_data = [
                    {
                        'amount': float(t.amount),
                        'description': t.description or '',
                        'date': t.transaction_date.strftime("%Y-%m-%d")
                    }
                    for t in historical_transactions[:10]
                ]
                
                parser = PydanticOutputParser(pydantic_object=AnomalyAnalysis)
                
                prompt = PromptTemplate(
                    template="""
                    Analyze this transaction for anomalies:
                    
                    Current Transaction:
                    - Amount: ${amount}
                    - Description: {description}
                    - Date: {date}
                    - Type: {transaction_type}
                    
                    Historical Context:
                    - Average amount: ${avg_amount:.2f}
                    - Maximum amount: ${max_amount:.2f}
                    - Standard deviation: ${std_amount:.2f}
                    - Z-score: {z_score:.2f}
                    
                    Recent transactions: {recent_transactions}
                    
                    Check for:
                    1. Unusual amounts (much higher/lower than normal)
                    2. Suspicious descriptions or patterns
                    3. Timing anomalies
                    4. Potential fraud indicators
                    
                    {format_instructions}
                    """,
                    input_variables=["amount", "description", "date", "transaction_type", 
                                   "avg_amount", "max_amount", "std_amount", "z_score", "recent_transactions"],
                    partial_variables={"format_instructions": parser.get_format_instructions()}
                )
                
                chain = LLMChain(llm=self.llm, prompt=prompt)
                
                result = chain.run(
                    amount=current_amount,
                    description=transaction.description or "No description",
                    date=transaction.transaction_date.strftime("%Y-%m-%d"),
                    transaction_type=transaction.transaction_type,
                    avg_amount=avg_amount,
                    max_amount=max_amount,
                    std_amount=std_amount,
                    z_score=z_score,
                    recent_transactions=str(historical_data)
                )
                
                anomaly_result = parser.parse(result)
                
                if anomaly_result.is_anomaly:
                    anomaly_detection = AnomalyDetection.objects.create(
                        transaction=transaction,
                        anomaly_type=anomaly_result.anomaly_type,
                        confidence_score=anomaly_result.confidence,
                        risk_level=anomaly_result.risk_level,
                        explanation=anomaly_result.explanation
                    )
                    
                    processing_time = time.time() - start_time
                    self._log_operation(
                        transaction.company.id, 
                        'ANOMALY_DETECTION', 
                        'SUCCESS', 
                        processing_time,
                        tokens_used=len(result.split()) * 2
                    )
                    
                    return anomaly_detection
            
            elif is_statistical_anomaly:
                # Fallback statistical anomaly detection
                anomaly_detection = AnomalyDetection.objects.create(
                    transaction=transaction,
                    anomaly_type='AMOUNT_UNUSUAL',
                    confidence_score=min(z_score / 5.0, 1.0),  # Normalize to 0-1
                    risk_level='HIGH' if z_score > 3 else 'MEDIUM',
                    explanation=f"Amount ${current_amount:.2f} is {z_score:.1f} standard deviations from average ${avg_amount:.2f}"
                )
                
                processing_time = time.time() - start_time
                self._log_operation(
                    transaction.company.id, 
                    'ANOMALY_DETECTION', 
                    'SUCCESS', 
                    processing_time
                )
                
                return anomaly_detection
            
            return None
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Anomaly detection error: {e}")
            self._log_operation(
                transaction.company.id, 
                'ANOMALY_DETECTION', 
                'FAILED', 
                processing_time,
                error_message=str(e)
            )
            return None
    
    def calculate_financial_health_score(self, company_id: int) -> FinancialHealthScore:
        """AI-powered financial health scoring"""
        start_time = time.time()
        
        try:
            company = Company.objects.get(id=company_id)
            
            # Get financial data
            transactions = Transaction.objects.filter(
                company=company, 
                status='COMPLETED'
            ).order_by('-transaction_date')[:100]
            
            accounts = Account.objects.filter(company=company, is_active=True)
            
            # Calculate metrics
            total_balance = sum(float(account.current_balance) for account in accounts)
            
            last_30_days = timezone.now() - timedelta(days=30)
            recent_income = transactions.filter(
                transaction_type='INCOME',
                transaction_date__gte=last_30_days
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            recent_expenses = transactions.filter(
                transaction_type='EXPENSE',
                transaction_date__gte=last_30_days
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            cash_flow = float(recent_income) - float(recent_expenses)
            
            # Basic scoring algorithm
            score = 50  # Base score
            
            # Cash flow factor (30 points)
            if cash_flow > 0:
                score += min(30, cash_flow / 10000 * 10)  # Scale based on cash flow
            else:
                score += max(-20, cash_flow / 10000 * 10)  # Penalty for negative cash flow
            
            # Balance factor (20 points)
            if total_balance > 50000:
                score += 20
            elif total_balance > 10000:
                score += 10
            elif total_balance < 0:
                score -= 15
            
            # Transaction consistency (10 points)
            if transactions.count() > 20:
                score += 10
            elif transactions.count() > 10:
                score += 5
            
            # Ensure score is between 0-100
            score = max(0, min(100, int(score)))
            
            # Generate AI insights if available
            if self.llm:
                try:
                    insights = self._generate_health_insights(company, score, total_balance, cash_flow, recent_income, recent_expenses)
                except Exception as e:
                    logger.error(f"Failed to generate AI insights: {e}")
                    insights = self._fallback_health_insights(score, total_balance, cash_flow)
            else:
                insights = self._fallback_health_insights(score, total_balance, cash_flow)
            
            # Create or update health score
            health_score, created = FinancialHealthScore.objects.update_or_create(
                company=company,
                defaults={
                    'score': score,
                    'factors': {
                        'total_balance': total_balance,
                        'monthly_cash_flow': cash_flow,
                        'monthly_income': float(recent_income),
                        'monthly_expenses': float(recent_expenses),
                        'transaction_count': transactions.count()
                    },
                    'recommendations': insights.get('recommendations', []),
                    'strengths': insights.get('strengths', []),
                    'concerns': insights.get('concerns', []),
                    'risk_level': 'LOW' if score >= 80 else 'MEDIUM' if score >= 60 else 'HIGH'
                }
            )
            
            processing_time = time.time() - start_time
            self._log_operation(
                company_id, 
                'HEALTH_SCORING', 
                'SUCCESS', 
                processing_time
            )
            
            return health_score
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Financial health scoring error: {e}")
            self._log_operation(
                company_id, 
                'HEALTH_SCORING', 
                'FAILED', 
                processing_time,
                error_message=str(e)
            )
            raise
    
    def _generate_health_insights(self, company, score, total_balance, cash_flow, income, expenses):
        """Generate AI-powered health insights"""
        prompt = PromptTemplate(
            template="""
            Analyze this business's financial health:
            
            Business: {company_name} ({industry})
            Health Score: {score}/100
            Total Balance: ${total_balance:,.2f}
            Monthly Cash Flow: ${cash_flow:,.2f}
            Monthly Income: ${income:,.2f}
            Monthly Expenses: ${expenses:,.2f}
            
            Provide analysis in JSON format:
            {{
                "strengths": ["strength1", "strength2", "strength3"],
                "concerns": ["concern1", "concern2", "concern3"],
                "recommendations": ["rec1", "rec2", "rec3", "rec4", "rec5"]
            }}
            
            Focus on actionable insights specific to this business.
            """,
            input_variables=["company_name", "industry", "score", "total_balance", "cash_flow", "income", "expenses"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        result = chain.run(
            company_name=company.name,
            industry=company.industry,
            score=score,
            total_balance=total_balance,
            cash_flow=cash_flow,
            income=income,
            expenses=expenses
        )
        
        return json.loads(result)
    
    def _fallback_health_insights(self, score, total_balance, cash_flow):
        """Fallback insights when AI is unavailable"""
        strengths = []
        concerns = []
        recommendations = []
        
        if cash_flow > 0:
            strengths.append("Positive monthly cash flow")
        else:
            concerns.append("Negative monthly cash flow")
            recommendations.append("Review and reduce unnecessary expenses")
        
        if total_balance > 50000:
            strengths.append("Strong cash reserves")
        elif total_balance < 10000:
            concerns.append("Low cash reserves")
            recommendations.append("Build emergency fund covering 3-6 months expenses")
        
        if score >= 80:
            strengths.append("Excellent financial health")
        elif score < 60:
            concerns.append("Below average financial health")
            recommendations.append("Focus on improving cash flow and reducing debt")
        
        # Add generic recommendations
        recommendations.extend([
            "Monitor cash flow trends regularly",
            "Set up automated savings goals",
            "Review and optimize recurring expenses"
        ])
        
        return {
            'strengths': strengths[:3],
            'concerns': concerns[:3],
            'recommendations': recommendations[:5]
        }


# Global AI analyzer instance
ai_analyzer = AIFinancialAnalyzer()
