import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from django.conf import settings
from django.db.models import Sum, Count, Avg, Q
from .models import Company, Account, Transaction, TransactionCategory, Budget, FinancialGoal, BulkUpload
from .rag_analyzer import FinancialDataRAG


class AICFOAgent:
    """AI-powered CFO Agent for comprehensive financial advisory using LangChain + LlamaIndex"""
    
    def __init__(self, company: Company, openai_api_key: str = None):
        self.company = company
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        
        # Configure LlamaIndex settings for GitHub Models API
        Settings.llm = OpenAI(
            api_key=self.api_key, 
            model="gpt-3.5-turbo", 
            temperature=0.3,
            api_base="https://models.github.ai/inference"
        )
        Settings.embed_model = OpenAIEmbedding(
            api_key=self.api_key,
            api_base="https://models.github.ai/inference"
        )
        
        # LangChain memory for conversation continuity
        self.memory = ConversationBufferWindowMemory(k=15, return_messages=True)
        
        # LlamaIndex for financial data RAG
        self.rag_analyzer = FinancialDataRAG(openai_api_key=self.api_key)
        self.financial_index = None
        self.query_engine = None
        
        # Cache for financial context
        self._financial_context = None
        self._context_updated = None
        
        # CFO expertise areas
        self.expertise_areas = {
            'cash_flow': 'Cash Flow Management and Working Capital Optimization',
            'cost_reduction': 'Cost Structure Analysis and Expense Optimization',
            'investment': 'Investment Strategy and Capital Allocation',
            'budgeting': 'Strategic Budgeting and Financial Planning',
            'risk_management': 'Financial Risk Assessment and Mitigation',
            'growth': 'Growth Financing and Capital Structure',
            'tax_optimization': 'Tax Strategy and Compliance Optimization',
            'debt_management': 'Debt Structure and Leverage Management',
            'performance': 'Financial Performance Analysis and KPIs',
            'compliance': 'Financial Compliance and Regulatory Matters'
        }
        
        self._initialize_financial_knowledge_base()
        
    def _initialize_financial_knowledge_base(self):
        """Initialize the financial knowledge base with company data"""
        try:
            self._update_financial_context()
            if self._financial_context:
                documents = self._create_financial_documents()
                if documents:
                    self.financial_index = VectorStoreIndex.from_documents(documents)
                    self.query_engine = self.financial_index.as_query_engine(
                        response_mode="tree_summarize",
                        verbose=False
                    )
        except Exception as e:
            print(f"Warning: Could not initialize financial knowledge base: {e}")
    
    def _create_financial_documents(self) -> List[Document]:
        """Create comprehensive financial documents for the knowledge base"""
        documents = []
        
        # Company overview document
        company_doc = f"""
        Company: {self.company.name}
        Industry: {self.company.industry or 'Not specified'}
        Currency: {self.company.currency}
        Employees: {self.company.employees_count or 'Not specified'}
        Annual Revenue: ${self.company.annual_revenue or 'Not specified'}
        Founded: {self.company.founded_date or 'Not specified'}
        
        Financial Overview:
        Total Accounts: {self._financial_context['accounts']['total_count']}
        Total Balance: ${self._financial_context['accounts']['total_balance']:,.2f}
        Recent Cash Flow: ${self._financial_context['recent_activity']['net_cash_flow']:,.2f}
        """
        
        documents.append(Document(
            text=company_doc,
            metadata={'type': 'company_overview', 'company_id': str(self.company.id)}
        ))
        
        # Account portfolio analysis
        for acc_type, data in self._financial_context['accounts']['by_type'].items():
            account_doc = f"""
            Account Type: {acc_type.replace('_', ' ').title()}
            Number of Accounts: {data['count']}
            Total Balance: ${data['total_balance']:,.2f}
            Percentage of Portfolio: {(data['total_balance'] / self._financial_context['accounts']['total_balance'] * 100):.1f}%
            """
            
            documents.append(Document(
                text=account_doc,
                metadata={'type': 'account_analysis', 'account_type': acc_type}
            ))
        
        # Recent financial activity analysis
        activity_doc = f"""
        Recent Financial Activity (30 days):
        Total Transactions: {self._financial_context['recent_activity']['total_transactions']}
        Income: ${self._financial_context['recent_activity']['income']['total']:,.2f} ({self._financial_context['recent_activity']['income']['count']} transactions)
        Expenses: ${self._financial_context['recent_activity']['expenses']['total']:,.2f} ({self._financial_context['recent_activity']['expenses']['count']} transactions)
        Net Cash Flow: ${self._financial_context['recent_activity']['net_cash_flow']:,.2f}
        
        Financial Health Indicators:
        - Cash Flow Trend: {'Positive' if self._financial_context['recent_activity']['net_cash_flow'] > 0 else 'Negative'}
        - Income Stability: {'Regular' if self._financial_context['recent_activity']['income']['count'] > 0 else 'Irregular'}
        - Expense Management: {'Active' if self._financial_context['recent_activity']['expenses']['count'] > 0 else 'Minimal'}
        """
        
        documents.append(Document(
            text=activity_doc,
            metadata={'type': 'activity_analysis', 'period': '30_days'}
        ))
        
        # Budget and goals analysis
        budget_doc = f"""
        Budget Management:
        Active Budgets: {self._financial_context['budgets']['active_count']}
        Total Allocated: ${self._financial_context['budgets']['total_allocated']:,.2f}
        
        Financial Goals:
        Total Goals: {self._financial_context['goals']['total_count']}
        Achieved Goals: {self._financial_context['goals']['achieved_count']}
        Target Amount: ${self._financial_context['goals']['total_target']:,.2f}
        Success Rate: {(self._financial_context['goals']['achieved_count'] / max(self._financial_context['goals']['total_count'], 1) * 100):.1f}%
        """
        
        documents.append(Document(
            text=budget_doc,
            metadata={'type': 'budget_goals_analysis'}
        ))
        
        return documents
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """Enhanced chat interface with professional CFO advisory"""
        
        try:
            # Refresh financial context if needed
            self._update_financial_context()
            
            # Determine the type of inquiry
            inquiry_type = self._classify_inquiry(user_message)
            
            # Get context-aware response
            if inquiry_type in ['data_query', 'analysis']:
                response = self._handle_data_inquiry(user_message)
            elif inquiry_type == 'advisory':
                response = self._handle_advisory_inquiry(user_message)
            elif inquiry_type == 'strategic':
                response = self._handle_strategic_inquiry(user_message)
            else:
                response = self._handle_general_inquiry(user_message)
            
            # Store conversation in memory
            self.memory.chat_memory.add_user_message(user_message)
            self.memory.chat_memory.add_ai_message(response)
            
            return {
                'response': response,
                'inquiry_type': inquiry_type,
                'timestamp': datetime.now().isoformat(),
                'confidence': 'high',
                'context_used': True,
                'follow_up_suggestions': self._get_follow_up_suggestions(inquiry_type)
            }
            
        except Exception as e:
            return {
                'response': f"I apologize, but I encountered an error while processing your request. As your CFO, I want to ensure accuracy in all financial matters. Please rephrase your question or contact support if this persists. Error: {str(e)}",
                'error': True,
                'timestamp': datetime.now().isoformat()
            }
    
    def _classify_inquiry(self, message: str) -> str:
        """Classify the type of financial inquiry"""
        message_lower = message.lower()
        
        # Data and reporting queries
        if any(word in message_lower for word in ['show', 'what', 'how much', 'list', 'report', 'data', 'numbers']):
            return 'data_query'
        
        # Analysis requests
        elif any(word in message_lower for word in ['analyze', 'analysis', 'trend', 'pattern', 'performance']):
            return 'analysis'
        
        # Strategic and planning
        elif any(word in message_lower for word in ['strategy', 'plan', 'should', 'recommend', 'advice', 'future']):
            return 'strategic'
        
        # Advisory requests
        elif any(word in message_lower for word in ['help', 'improve', 'optimize', 'reduce', 'increase']):
            return 'advisory'
        
        return 'general'
    
    def _handle_data_inquiry(self, message: str) -> str:
        """Handle data and reporting inquiries using RAG"""
        
        if self.query_engine:
            # Use LlamaIndex for data retrieval
            financial_data_response = self.query_engine.query(message)
            
            # Enhance with CFO perspective
            cfo_prompt = f"""
            As the CFO of {self.company.name}, provide a professional response to this inquiry: "{message}"
            
            Financial Data Context: {str(financial_data_response)}
            
            Please provide:
            1. Direct answer to the question
            2. Financial implications
            3. Key metrics or ratios if relevant
            4. Any concerns or opportunities identified
            
            Keep the response professional and data-driven.
            """
            
            llm = Settings.llm
            enhanced_response = llm.complete(cfo_prompt)
            return str(enhanced_response)
        else:
            # Fallback to basic financial summary
            return self._get_basic_financial_summary()
    
    def _handle_advisory_inquiry(self, message: str) -> str:
        """Handle advisory and optimization inquiries"""
        
        context = self._format_context_for_advisory()
        
        advisory_prompt = f"""
        As the CFO of {self.company.name}, provide professional financial advisory for: "{message}"
        
        Current Financial Position:
        {context}
        
        Please provide:
        1. Professional assessment of the situation
        2. Specific, actionable recommendations
        3. Implementation timeline and priorities
        4. Risk factors to consider
        5. Expected outcomes and metrics to track
        
        Maintain a professional, authoritative tone appropriate for C-level communication.
        """
        
        llm = Settings.llm
        response = llm.complete(advisory_prompt)
        return str(response)
    
    def _handle_strategic_inquiry(self, message: str) -> str:
        """Handle strategic planning and high-level financial strategy"""
        
        context = self._format_context_for_strategy()
        
        strategic_prompt = f"""
        As the CFO of {self.company.name}, provide strategic financial guidance for: "{message}"
        
        Company Financial Profile:
        {context}
        
        Industry Context: {self.company.industry or 'General Business'}
        
        Please provide:
        1. Strategic financial perspective
        2. Long-term implications and considerations
        3. Capital allocation recommendations
        4. Risk assessment and mitigation strategies
        5. Performance indicators to monitor
        6. Alignment with business objectives
        
        Respond as a senior financial executive with deep industry knowledge.
        """
        
        llm = Settings.llm
        response = llm.complete(strategic_prompt)
        return str(response)
    
    def _handle_general_inquiry(self, message: str) -> str:
        """Handle general financial inquiries"""
        
        general_prompt = f"""
        As the CFO of {self.company.name}, respond professionally to: "{message}"
        
        Company: {self.company.name}
        Industry: {self.company.industry or 'General Business'}
        
        Provide a helpful, professional response that demonstrates financial expertise and maintains the dignity of the CFO role.
        """
        
        llm = Settings.llm
        response = llm.complete(general_prompt)
        return str(response)
    
    def _format_context_for_advisory(self) -> str:
        """Format financial context for advisory responses"""
        ctx = self._financial_context
        
        return f"""
        Financial Position Summary:
        • Total Assets: ${ctx['accounts']['total_balance']:,.2f}
        • 30-Day Cash Flow: ${ctx['recent_activity']['net_cash_flow']:,.2f}
        • Revenue: ${ctx['recent_activity']['income']['total']:,.2f}
        • Expenses: ${ctx['recent_activity']['expenses']['total']:,.2f}
        • Active Budgets: {ctx['budgets']['active_count']}
        • Financial Goals: {ctx['goals']['total_count']} ({ctx['goals']['achieved_count']} achieved)
        
        Account Portfolio:
        {chr(10).join([f'• {acc_type.replace("_", " ").title()}: ${data["total_balance"]:,.2f}' for acc_type, data in ctx['accounts']['by_type'].items()])}
        """
    
    def _format_context_for_strategy(self) -> str:
        """Format financial context for strategic responses"""
        ctx = self._financial_context
        
        cash_flow_trend = "Positive" if ctx['recent_activity']['net_cash_flow'] > 0 else "Negative"
        liquidity_ratio = ctx['accounts']['total_balance'] / max(ctx['recent_activity']['expenses']['total'], 1)
        
        return f"""
        Strategic Financial Overview:
        • Company: {self.company.name}
        • Annual Revenue: ${self.company.annual_revenue or 0:,.2f}
        • Current Liquidity: ${ctx['accounts']['total_balance']:,.2f}
        • Liquidity Ratio: {liquidity_ratio:.2f}x monthly expenses
        • Cash Flow Trend: {cash_flow_trend}
        • Growth Capacity: {'Strong' if ctx['recent_activity']['net_cash_flow'] > 0 else 'Limited'}
        • Risk Profile: {'Conservative' if ctx['accounts']['total_balance'] > ctx['recent_activity']['expenses']['total'] * 3 else 'Moderate'}
        """
    
    def _get_follow_up_suggestions(self, inquiry_type: str) -> List[str]:
        """Get contextual follow-up suggestions"""
        
        base_suggestions = {
            'data_query': [
                "Would you like me to analyze trends in this data?",
                "Should I provide benchmarking insights?",
                "Do you want recommendations based on these numbers?"
            ],
            'analysis': [
                "Would you like specific action items based on this analysis?",
                "Should I create a monitoring dashboard for these metrics?",
                "Do you want me to assess the financial impact?"
            ],
            'advisory': [
                "Would you like me to create an implementation timeline?",
                "Should I assess the ROI of these recommendations?",
                "Do you want risk mitigation strategies?"
            ],
            'strategic': [
                "Would you like me to model different scenarios?",
                "Should I create a strategic roadmap?",
                "Do you want competitive analysis insights?"
            ]
        }
        
        return base_suggestions.get(inquiry_type, [
            "How else can I assist with your financial strategy?",
            "Would you like me to analyze any specific metrics?",
            "Should I provide additional financial insights?"
        ])
    
    def _get_financial_context_summary(self) -> str:
        """Get a summary of financial context for the prompt"""
        if not self._financial_context:
            return "No recent financial data available."
        
        try:
            context = self._financial_context
            summary = f"""
            Financial Summary:
            - Total Accounts: {context.get('accounts', {}).get('total_count', 0)}
            - Total Balance: ${context.get('accounts', {}).get('total_balance', 0):,.2f}
            - Recent 30-day Cash Flow: ${context.get('recent_activity', {}).get('net_cash_flow', 0):,.2f}
            - Recent Transactions: {context.get('recent_activity', {}).get('total_transactions', 0)}
            """
            
            recent_activity = context.get('recent_activity', {})
            income_data = recent_activity.get('income', {})
            expenses_data = recent_activity.get('expenses', {})
            
            if income_data.get('count', 0) > 0:
                summary += f"\n- Recent Income: ${income_data.get('total', 0):,.2f} ({income_data.get('count', 0)} transactions)"
            
            if expenses_data.get('count', 0) > 0:
                summary += f"\n- Recent Expenses: ${expenses_data.get('total', 0):,.2f} ({expenses_data.get('count', 0)} transactions)"
            
            return summary
            
        except Exception as e:
            return "Financial data temporarily unavailable."
    
    def _update_financial_context(self):
        """Update cached financial context"""
        
        # Update context every 5 minutes or if not set
        now = datetime.now()
        if (self._context_updated is None or 
            (now - self._context_updated).total_seconds() > 300):
            
            self._financial_context = self._get_current_financial_context()
            self._context_updated = now
    
    def _get_current_financial_context(self) -> Dict[str, Any]:
        """Get current financial context for the company"""
        
        try:
            context = {
                'company': {
                    'name': self.company.name,
                    'industry': self.company.industry,
                    'currency': self.company.currency,
                    'employees': self.company.employees_count,
                    'annual_revenue': float(self.company.annual_revenue) if self.company.annual_revenue else None
                }
            }
            
            # Account summary
            accounts = self.company.accounts.filter(is_active=True)
            context['accounts'] = {
                'total_count': accounts.count(),
                'total_balance': float(sum(acc.current_balance for acc in accounts)),
                'by_type': {}
            }
            
            for account in accounts:
                acc_type = account.account_type
                if acc_type not in context['accounts']['by_type']:
                    context['accounts']['by_type'][acc_type] = {
                        'count': 0,
                        'total_balance': 0
                    }
                context['accounts']['by_type'][acc_type]['count'] += 1
                context['accounts']['by_type'][acc_type]['total_balance'] += float(account.current_balance)
            
            # Recent transaction summary (last 30 days)
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            recent_transactions = Transaction.objects.filter(
                account__company=self.company,
                transaction_date__gte=thirty_days_ago
            )
            
            income_txns = recent_transactions.filter(amount__gt=0)
            expense_txns = recent_transactions.filter(amount__lt=0)
            
            context['recent_activity'] = {
                'period': '30_days',
                'total_transactions': recent_transactions.count(),
                'income': {
                    'total': float(income_txns.aggregate(Sum('amount'))['amount__sum'] or 0),
                    'count': income_txns.count()
                },
                'expenses': {
                    'total': float(abs(expense_txns.aggregate(Sum('amount'))['amount__sum'] or 0)),
                    'count': expense_txns.count()
                }
            }
            
            context['recent_activity']['net_cash_flow'] = (
                context['recent_activity']['income']['total'] - 
                context['recent_activity']['expenses']['total']
            )
            
            # Budget summary
            active_budgets = Budget.objects.filter(company=self.company, is_active=True)
            context['budgets'] = {
                'active_count': active_budgets.count(),
                'total_allocated': float(sum(budget.budgeted_amount for budget in active_budgets))
            }
            
            # Financial goals
            active_goals = FinancialGoal.objects.filter(company=self.company)
            context['goals'] = {
                'total_count': active_goals.count(),
                'achieved_count': active_goals.filter(is_achieved=True).count(),
                'total_target': float(sum(goal.target_amount for goal in active_goals))
            }
            
            return context
        
        except Exception as e:
            # Return minimal context if there's an error
            return {
                'company': {
                    'name': self.company.name,
                    'currency': self.company.currency
                },
                'accounts': {'total_count': 0, 'total_balance': 0},
                'recent_activity': {
                    'total_transactions': 0,
                    'income': {'total': 0, 'count': 0},
                    'expenses': {'total': 0, 'count': 0},
                    'net_cash_flow': 0
                },
                'budgets': {'active_count': 0},
                'goals': {'total_count': 0, 'achieved_count': 0}
            }
    
    def _enhance_message_with_context(self, message: str) -> str:
        """Enhance user message with relevant financial context"""
        
        # Keywords that trigger financial data inclusion
        financial_keywords = [
            'balance', 'cash', 'revenue', 'profit', 'expense', 'budget',
            'account', 'transaction', 'income', 'spending', 'financial',
            'performance', 'analysis', 'report', 'summary', 'overview'
        ]
        
        message_lower = message.lower()
        needs_context = any(keyword in message_lower for keyword in financial_keywords)
        
        if needs_context and self._financial_context:
            context_summary = self._format_context_for_prompt()
            enhanced_message = f"{message}\n\n[Financial Context: {context_summary}]"
            return enhanced_message
        
        return message
    
    def _format_context_for_prompt(self) -> str:
        """Format financial context for inclusion in prompt"""
        
        ctx = self._financial_context
        
        parts = [
            f"Total accounts: {ctx['accounts']['total_count']}",
            f"Total balance: ${ctx['accounts']['total_balance']:,.2f}",
            f"30-day income: ${ctx['recent_activity']['income']['total']:,.2f}",
            f"30-day expenses: ${ctx['recent_activity']['expenses']['total']:,.2f}",
            f"Net cash flow: ${ctx['recent_activity']['net_cash_flow']:,.2f}",
            f"Active budgets: {ctx['budgets']['active_count']}",
            f"Financial goals: {ctx['goals']['total_count']} ({ctx['goals']['achieved_count']} achieved)"
        ]
        
        return "; ".join(parts)
    
    def _extract_financial_data_if_requested(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract specific financial data if requested by user"""
        
        message_lower = message.lower()
        
        # Check for specific data requests
        if any(word in message_lower for word in ['show', 'display', 'list', 'data', 'numbers']):
            
            data = {}
            
            if 'account' in message_lower:
                data['accounts'] = self._get_account_data()
            
            if any(word in message_lower for word in ['transaction', 'recent', 'activity']):
                data['recent_transactions'] = self._get_recent_transaction_data()
            
            if 'budget' in message_lower:
                data['budgets'] = self._get_budget_data()
            
            if 'goal' in message_lower:
                data['goals'] = self._get_goal_data()
            
            if any(word in message_lower for word in ['summary', 'overview', 'report']):
                data = self._financial_context
            
            return data if data else None
        
        return None
    
    def _get_account_data(self) -> List[Dict[str, Any]]:
        """Get detailed account data"""
        
        accounts = self.company.accounts.filter(is_active=True)
        return [
            {
                'name': account.name,
                'type': account.get_account_type_display(),
                'balance': float(account.current_balance),
                'bank': account.bank_name or 'N/A'
            }
            for account in accounts
        ]
    
    def _get_recent_transaction_data(self) -> List[Dict[str, Any]]:
        """Get recent transaction data"""
        
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        transactions = Transaction.objects.filter(
            account__company=self.company,
            transaction_date__gte=thirty_days_ago
        ).select_related('account', 'category').order_by('-transaction_date')[:20]
        
        return [
            {
                'date': txn.transaction_date.isoformat(),
                'description': txn.description,
                'amount': float(txn.amount),
                'account': txn.account.name,
                'category': txn.category.name if txn.category else 'Uncategorized',
                'type': txn.get_transaction_type_display()
            }
            for txn in transactions
        ]
    
    def _get_budget_data(self) -> List[Dict[str, Any]]:
        """Get budget data"""
        
        budgets = Budget.objects.filter(company=self.company, is_active=True)
        return [
            {
                'category': budget.category.name if budget.category else 'No Category',
                'allocated': float(budget.budgeted_amount),
                'spent': float(budget.spent_amount),
                'remaining': float(budget.remaining_amount),
                'start_date': budget.start_date.isoformat(),
                'end_date': budget.end_date.isoformat(),
                'status': 'Over Budget' if budget.spent_amount > budget.budgeted_amount else 'On Track'
            }
            for budget in budgets
        ]
    
    def _get_goal_data(self) -> List[Dict[str, Any]]:
        """Get financial goal data"""
        
        goals = FinancialGoal.objects.filter(company=self.company)
        return [
            {
                'name': goal.name,
                'type': goal.goal_type,
                'target_amount': float(goal.target_amount),
                'current_amount': float(goal.current_amount),
                'target_date': goal.target_date.isoformat(),
                'progress_percentage': goal.progress_percentage,
                'is_achieved': goal.is_achieved
            }
            for goal in goals
        ]
    
    def get_financial_advice(self, topic: str) -> Dict[str, Any]:
        """Get specific financial advice on a topic"""
        
        advice_prompts = {
            'cash_flow': "How can we improve our cash flow management?",
            'cost_reduction': "What are the best strategies for reducing costs?",
            'investment': "What investment opportunities should we consider?",
            'budgeting': "How can we improve our budgeting process?",
            'risk_management': "What financial risks should we be aware of?",
            'growth': "How can we finance business growth?",
            'tax_optimization': "What tax optimization strategies should we consider?",
            'debt_management': "How should we manage our debt effectively?"
        }
        
        prompt = advice_prompts.get(topic, f"Please provide financial advice about {topic}")
        return self.chat(prompt)
    
    def analyze_csv_upload(self, bulk_upload_id: str) -> Dict[str, Any]:
        """Analyze a CSV upload and provide insights through the CFO lens"""
        
        try:
            from .models import BulkUpload
            bulk_upload = BulkUpload.objects.get(id=bulk_upload_id, company=self.company)
            
            # Get RAG analysis
            rag_analysis = self.rag_analyzer.analyze_bulk_upload(bulk_upload)
            
            # Generate CFO perspective
            cfo_prompt = f"""
            As the CFO, please analyze this recent data upload and provide strategic insights:
            
            Upload Summary: {bulk_upload.upload_type} upload with {bulk_upload.successful_rows} successful records
            
            Key Findings: {rag_analysis.get('insights', [])}
            
            Please provide:
            1. Strategic implications of this data
            2. Risk assessment
            3. Opportunities identified
            4. Action items for management
            5. Impact on business objectives
            """
            
            cfo_response = self.chat(cfo_prompt)
            
            return {
                'rag_analysis': rag_analysis,
                'cfo_perspective': cfo_response,
                'combined_recommendations': self._combine_recommendations(
                    rag_analysis.get('recommendations', []),
                    cfo_response.get('response', '')
                )
            }
            
        except Exception as e:
            return {
                'error': f"Failed to analyze upload: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _combine_recommendations(self, rag_recommendations: List[str], 
                                cfo_response: str) -> List[str]:
        """Combine RAG and CFO recommendations"""
        
        combined = []
        combined.extend(rag_recommendations)
        
        # Extract action items from CFO response
        if "action items" in cfo_response.lower():
            lines = cfo_response.split('\n')
            in_action_section = False
            
            for line in lines:
                if "action items" in line.lower():
                    in_action_section = True
                elif in_action_section and line.strip():
                    if line.strip().startswith(('•', '-', '*', '1.', '2.', '3.')):
                        combined.append(line.strip())
        
        return combined
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of the current conversation session"""
        
        messages = []
        if hasattr(self.memory, 'chat_memory') and hasattr(self.memory.chat_memory, 'messages'):
            for msg in self.memory.chat_memory.messages:
                messages.append({
                    'type': msg.__class__.__name__,
                    'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content
                })
        
        return {
            'session_length': len(messages),
            'messages': messages,
            'financial_context_last_updated': self._context_updated.isoformat() if self._context_updated else None,
            'company': self.company.name
        }
    
    def clear_session(self):
        """Clear the conversation memory"""
        self.memory.clear()
        self._financial_context = None
        self._context_updated = None
    
    def get_specialized_financial_advice(self, topic: str) -> Dict[str, Any]:
        """Get specialized financial advice on specific CFO expertise areas"""
        
        if topic not in self.expertise_areas:
            return {
                'error': f'Topic "{topic}" not recognized. Available topics: {list(self.expertise_areas.keys())}',
                'timestamp': datetime.now().isoformat()
            }
        
        # Get current financial context
        self._update_financial_context()
        context = self._format_context_for_advisory()
        
        # Specialized prompts for each expertise area
        specialized_prompts = {
            'cash_flow': f"""
            As CFO, provide comprehensive cash flow management advice for {self.company.name}.
            
            Current Financial Position:
            {context}
            
            Please address:
            1. Current cash flow analysis and health assessment
            2. Working capital optimization strategies
            3. Cash flow forecasting recommendations
            4. Liquidity management best practices
            5. Cash conversion cycle improvements
            6. Emergency fund adequacy assessment
            7. Specific action items with timelines
            """,
            
            'cost_reduction': f"""
            As CFO, provide strategic cost reduction and expense optimization advice for {self.company.name}.
            
            Current Financial Position:
            {context}
            
            Please address:
            1. Cost structure analysis and identification of reduction opportunities
            2. Fixed vs variable cost optimization
            3. Vendor negotiation strategies
            4. Process efficiency improvements
            5. Technology investments for cost savings
            6. ROI calculations for cost reduction initiatives
            7. Implementation roadmap with priorities
            """,
            
            'investment': f"""
            As CFO, provide investment strategy and capital allocation advice for {self.company.name}.
            
            Current Financial Position:
            {context}
            
            Please address:
            1. Current investment capacity assessment
            2. Investment priority framework
            3. Risk-adjusted return expectations
            4. Portfolio diversification recommendations
            5. Capital allocation strategy
            6. Investment timeline and milestones
            7. Performance monitoring metrics
            """,
            
            'risk_management': f"""
            As CFO, provide comprehensive financial risk management advice for {self.company.name}.
            
            Current Financial Position:
            {context}
            
            Please address:
            1. Financial risk assessment and identification
            2. Risk mitigation strategies and controls
            3. Insurance and hedging recommendations
            4. Scenario planning and stress testing
            5. Regulatory compliance considerations
            6. Risk monitoring and reporting framework
            7. Crisis management financial protocols
            """
        }
        
        # Get the prompt for the specific topic
        prompt = specialized_prompts.get(topic, f"""
        As CFO, provide expert advice on {self.expertise_areas[topic]} for {self.company.name}.
        
        Current Financial Position:
        {context}
        
        Please provide comprehensive, actionable advice with specific recommendations and implementation guidance.
        """)
        
        # Generate specialized advice
        llm = Settings.llm
        advice_response = llm.complete(prompt)
        
        return {
            'topic': topic,
            'expertise_area': self.expertise_areas[topic],
            'advice': str(advice_response),
            'financial_context': self._get_key_metrics_summary(),
            'next_steps': self._get_next_steps_for_topic(topic),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_next_steps_for_topic(self, topic: str) -> List[str]:
        """Get specific next steps for each advice topic"""
        
        next_steps = {
            'cash_flow': [
                "Set up weekly cash flow monitoring",
                "Implement accounts receivable optimization",
                "Review payment terms with vendors",
                "Establish cash flow forecasting model"
            ],
            'cost_reduction': [
                "Conduct comprehensive expense audit",
                "Negotiate with top 3 vendors",
                "Implement expense approval workflows",
                "Set up cost center tracking"
            ],
            'investment': [
                "Define investment criteria and thresholds",
                "Establish investment committee",
                "Create due diligence framework",
                "Set up performance tracking system"
            ],
            'risk_management': [
                "Conduct risk assessment workshop",
                "Document risk management policies",
                "Implement monitoring dashboards",
                "Schedule quarterly risk reviews"
            ]
        }
        
        return next_steps.get(topic, [
            f"Schedule follow-up meeting to discuss {topic} strategy",
            "Prepare detailed implementation plan",
            "Identify required resources and timeline",
            "Set up monitoring and review process"
        ])
    
    def analyze_csv_upload_comprehensive(self, bulk_upload_id: str) -> Dict[str, Any]:
        """Comprehensive CFO analysis of CSV upload with strategic insights"""
        
        try:
            bulk_upload = BulkUpload.objects.get(id=bulk_upload_id, company=self.company)
            
            # Get RAG analysis first
            rag_analysis = self.rag_analyzer.analyze_bulk_upload(bulk_upload)
            
            # Generate CFO strategic perspective
            cfo_strategic_prompt = f"""
            As the CFO of {self.company.name}, analyze this recent data upload and provide strategic financial insights.
            
            Upload Summary:
            - Type: {bulk_upload.upload_type}
            - Success Rate: {bulk_upload.success_rate:.1f}%
            - Rows Processed: {bulk_upload.successful_rows}
            
            Data Insights from Analysis:
            {json.dumps(rag_analysis.get('insights', []), indent=2)}
            
            Statistical Overview:
            {json.dumps(rag_analysis.get('statistics', {}), indent=2)}
            
            As CFO, provide:
            1. Strategic implications of this data for business operations
            2. Financial performance assessment and trends
            3. Risk factors and opportunities identified
            4. Capital allocation recommendations
            5. Operational efficiency insights
            6. Board-level summary and key takeaways
            7. Immediate action items for management team
            8. Long-term strategic considerations
            
            Maintain executive-level perspective with focus on business value and financial health.
            """
            
            llm = Settings.llm
            cfo_analysis = llm.complete(cfo_strategic_prompt)
            
            # Generate board report summary
            board_summary = self._generate_board_summary(rag_analysis, str(cfo_analysis))
            
            return {
                'upload_info': {
                    'upload_id': str(bulk_upload.id),
                    'upload_type': bulk_upload.upload_type,
                    'success_rate': bulk_upload.success_rate,
                    'data_quality': 'High' if bulk_upload.success_rate > 95 else 'Moderate' if bulk_upload.success_rate > 80 else 'Needs Review'
                },
                'rag_analysis': rag_analysis,
                'cfo_strategic_analysis': str(cfo_analysis),
                'board_summary': board_summary,
                'executive_recommendations': self._extract_executive_recommendations(str(cfo_analysis)),
                'risk_assessment': self._assess_financial_risks(rag_analysis),
                'performance_indicators': self._identify_key_performance_indicators(rag_analysis),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f"Failed to complete CFO analysis: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_board_summary(self, rag_analysis: Dict, cfo_analysis: str) -> str:
        """Generate executive summary for board presentation"""
        
        stats = rag_analysis.get('statistics', {})
        
        summary = f"""
        EXECUTIVE FINANCIAL SUMMARY - {self.company.name}
        
        DATA OVERVIEW:
        • Analysis Period: Recent upload with {stats.get('total_transactions', 'N/A')} transactions
        • Financial Impact: ${stats.get('total_amount', 0):,.2f} total transaction value
        • Net Position: ${stats.get('net_cash_flow', 0):,.2f} net cash flow
        
        KEY FINANCIAL METRICS:
        • Revenue Performance: ${stats.get('income', {}).get('total', 0):,.2f}
        • Expense Management: ${stats.get('expenses', {}).get('total', 0):,.2f}
        • Operational Efficiency: {len(stats.get('top_expense_categories', []))} major expense categories
        
        STRATEGIC INSIGHTS:
        {chr(10).join(['• ' + insight for insight in rag_analysis.get('insights', [])[:3]])}
        
        BOARD RECOMMENDATIONS:
        {chr(10).join(['• ' + rec for rec in rag_analysis.get('recommendations', [])[:3]])}
        
        CFO ASSESSMENT: Based on the data analysis, the company shows {'strong' if stats.get('net_cash_flow', 0) > 0 else 'challenging'} financial performance with clear opportunities for optimization and growth.
        """
        
        return summary
    
    def _extract_executive_recommendations(self, cfo_analysis: str) -> List[str]:
        """Extract actionable recommendations from CFO analysis"""
        
        # Simple extraction - in production, could use NLP for better parsing
        lines = cfo_analysis.split('\n')
        recommendations = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['recommend', 'should', 'must', 'action', 'implement']):
                cleaned = line.strip('• -')
                if len(cleaned) > 20:  # Filter out short fragments
                    recommendations.append(cleaned)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _assess_financial_risks(self, rag_analysis: Dict) -> Dict[str, Any]:
        """Assess financial risks based on analysis"""
        
        stats = rag_analysis.get('statistics', {})
        risks = {
            'cash_flow_risk': 'Low',
            'concentration_risk': 'Low',
            'liquidity_risk': 'Low',
            'operational_risk': 'Low'
        }
        
        # Cash flow risk
        if stats.get('net_cash_flow', 0) < 0:
            risks['cash_flow_risk'] = 'High'
        elif stats.get('net_cash_flow', 0) < stats.get('expenses', {}).get('total', 0) * 0.1:
            risks['cash_flow_risk'] = 'Medium'
        
        # Concentration risk (if top category > 50% of expenses)
        top_categories = stats.get('top_expense_categories', [])
        if top_categories and top_categories[0].get('percentage', 0) > 50:
            risks['concentration_risk'] = 'High'
        elif top_categories and top_categories[0].get('percentage', 0) > 30:
            risks['concentration_risk'] = 'Medium'
        
        return risks
    
    def _identify_key_performance_indicators(self, rag_analysis: Dict) -> Dict[str, Any]:
        """Identify key performance indicators from analysis"""
        
        stats = rag_analysis.get('statistics', {})
        
        return {
            'revenue_per_transaction': stats.get('income', {}).get('total', 0) / max(stats.get('income', {}).get('count', 1), 1),
            'expense_efficiency': stats.get('expenses', {}).get('total', 0) / max(stats.get('expenses', {}).get('count', 1), 1),
            'cash_flow_ratio': stats.get('net_cash_flow', 0) / max(abs(stats.get('total_amount', 1)), 1),
            'category_diversity': len(stats.get('top_expense_categories', [])),
            'financial_health_score': self._calculate_financial_health_score(stats)
        }
    
    def _calculate_financial_health_score(self, stats: Dict) -> float:
        """Calculate overall financial health score (0-100)"""
        
        score = 50  # Base score
        
        # Cash flow component (30 points)
        net_flow = stats.get('net_cash_flow', 0)
        total_amount = abs(stats.get('total_amount', 1))
        if net_flow > 0:
            score += min(30, (net_flow / total_amount) * 100)
        else:
            score -= min(30, abs(net_flow / total_amount) * 100)
        
        # Diversification component (20 points)
        categories = len(stats.get('top_expense_categories', []))
        if categories > 5:
            score += 20
        elif categories > 3:
            score += 15
        elif categories > 1:
            score += 10
        
        return max(0, min(100, score))
    
    def _get_key_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of key financial metrics"""
        
        ctx = self._financial_context
        return {
            'total_assets': ctx['accounts']['total_balance'],
            'monthly_cash_flow': ctx['recent_activity']['net_cash_flow'],
            'expense_ratio': ctx['recent_activity']['expenses']['total'] / max(ctx['recent_activity']['income']['total'], 1),
            'liquidity_months': ctx['accounts']['total_balance'] / max(ctx['recent_activity']['expenses']['total'], 1),
            'budget_utilization': f"{ctx['budgets']['active_count']} active budgets",
            'goal_achievement': f"{ctx['goals']['achieved_count']}/{ctx['goals']['total_count']} goals achieved"
        }
    
    def _get_basic_financial_summary(self) -> str:
        """Get basic financial summary when RAG is not available"""
        
        ctx = self._financial_context
        return f"""
        Based on the current financial position of {self.company.name}:
        
        • Total Assets: ${ctx['accounts']['total_balance']:,.2f}
        • Recent Cash Flow: ${ctx['recent_activity']['net_cash_flow']:,.2f}
        • Active Financial Management: {ctx['budgets']['active_count']} budgets, {ctx['goals']['total_count']} goals
        
        The company appears to be in {'good' if ctx['recent_activity']['net_cash_flow'] > 0 else 'challenging'} financial health with opportunities for continued optimization and growth.
        """
