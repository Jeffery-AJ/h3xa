# Financial Analytics Platform API Documentation

## Overview
Comprehensive API for managing financial data, bulk uploads, and AI-powered analytics.

**Base URL:** `http://localhost:8000/api/financial/api/v1/`

## Authentication
All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Core Endpoints

### Companies
- `GET /companies/` - List all companies
- `POST /companies/` - Create new company
- `GET /companies/{id}/` - Get company details
- `PUT /companies/{id}/` - Update company
- `DELETE /companies/{id}/` - Delete company
- `GET /companies/{id}/financial_summary/` - Get financial summary

### Accounts
- `GET /accounts/` - List all accounts
- `POST /accounts/` - Create new account
- `GET /accounts/{id}/` - Get account details
- `PUT /accounts/{id}/` - Update account
- `DELETE /accounts/{id}/` - Delete account
- `GET /accounts/{id}/balance_history/` - Get balance history
- `GET /accounts/{id}/transactions/` - Get account transactions

### Transactions
- `GET /transactions/` - List all transactions
- `POST /transactions/` - Create new transaction
- `GET /transactions/{id}/` - Get transaction details
- `PUT /transactions/{id}/` - Update transaction
- `DELETE /transactions/{id}/` - Delete transaction
- `GET /transactions/analytics/` - Get transaction analytics
- `GET /transactions/cash_flow/` - Get cash flow analytics

### Categories
- `GET /categories/` - List all categories
- `POST /categories/` - Create new category
- `GET /categories/{id}/` - Get category details
- `PUT /categories/{id}/` - Update category
- `DELETE /categories/{id}/` - Delete category

### Budgets
- `GET /budgets/` - List all budgets
- `POST /budgets/` - Create new budget
- `GET /budgets/{id}/` - Get budget details
- `PUT /budgets/{id}/` - Update budget
- `DELETE /budgets/{id}/` - Delete budget

### Financial Goals
- `GET /goals/` - List all goals
- `POST /goals/` - Create new goal
- `GET /goals/{id}/` - Get goal details
- `PUT /goals/{id}/` - Update goal
- `DELETE /goals/{id}/` - Delete goal

## Bulk Upload Endpoints

### Bulk Upload Management
- `GET /bulk-uploads/` - List all bulk uploads
- `GET /bulk-uploads/{id}/` - Get bulk upload details
- `GET /bulk-uploads/{id}/errors/` - Get upload errors
- `GET /bulk-uploads/{id}/download_error_report/` - Download error report CSV
- `GET /bulk-uploads/csv_templates/` - Get CSV template information

### CSV Upload Endpoints

#### Upload Accounts
**Endpoint:** `POST /bulk-uploads/upload_accounts/`

**Request:**
```
Content-Type: multipart/form-data

company_id: <uuid>
file: <csv_file>
```

**CSV Format:**
```csv
name,account_type,balance,account_number,bank_name,currency,is_active
Main Checking Account,checking,5000.00,1234567890,First National Bank,USD,true
Savings Account,savings,15000.00,1234567891,First National Bank,USD,true
Business Credit Card,credit_card,-2500.00,4532123456789012,Business Bank,USD,true
```

**Required Fields:**
- `name` - Account name
- `account_type` - One of: checking, savings, credit_card, loan, investment, cash, paypal, stripe, other
- `balance` - Account balance (decimal)

**Optional Fields:**
- `account_number` - Account number
- `bank_name` - Bank name
- `currency` - Currency code (default: USD)
- `is_active` - Boolean (default: true)

#### Upload Transactions
**Endpoint:** `POST /bulk-uploads/upload_transactions/`

**Request:**
```
Content-Type: multipart/form-data

company_id: <uuid>
file: <csv_file>
```

**CSV Format:**
```csv
account_name,amount,description,date,transaction_type,category,reference_number,tags
Main Checking Account,-50.00,Grocery shopping,2023-12-01,expense,Food & Dining,TXN123456,groceries;weekly
Main Checking Account,2500.00,Salary deposit,2023-12-01,income,Salary,DEP789012,salary;monthly
```

**Required Fields:**
- `account_name` - Name of existing account
- `amount` - Transaction amount (negative for expenses, positive for income)
- `description` - Transaction description
- `date` - Transaction date (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)

**Optional Fields:**
- `transaction_type` - One of: income, expense, transfer (auto-detected if not provided)
- `category` - Category name (will be created if doesn't exist)
- `reference_number` - Reference number
- `tags` - Comma or semicolon separated tags

#### Upload Categories
**Endpoint:** `POST /bulk-uploads/upload_categories/`

**Request:**
```
Content-Type: multipart/form-data

company_id: <uuid>
file: <csv_file>
```

**CSV Format:**
```csv
name,category_type,description,is_active
Food & Dining,expense,Restaurant meals and groceries,true
Salary,income,Monthly salary income,true
Office Supplies,expense,Business office supplies,true
```

**Required Fields:**
- `name` - Category name
- `category_type` - One of: income, expense

**Optional Fields:**
- `description` - Category description
- `is_active` - Boolean (default: true)

### Upload Response Format
```json
{
    "bulk_upload_id": "uuid",
    "status": "completed|partial|failed",
    "total_rows": 100,
    "successful_rows": 95,
    "failed_rows": 5,
    "success_rate": 95.0,
    "message": "Upload completed. 95 rows processed successfully, 5 rows failed."
}
```

### Error Response Format
```json
{
    "bulk_upload_id": "uuid",
    "errors": [
        {
            "row_number": 3,
            "field_name": "account_type",
            "error_type": "invalid_choice",
            "error_message": "Invalid account type: checkings. Valid choices: ['checking', 'savings', ...]",
            "row_data": {"name": "Test Account", "account_type": "checkings", "balance": "1000"}
        }
    ]
}
```

## AI-Powered Features

### RAG Analysis Endpoints

#### Analyze Bulk Upload
**Endpoint:** `POST /rag-analysis/analyze_upload/`

**Request:**
```json
{
    "bulk_upload_id": "uuid"
}
```

**Response:**
```json
{
    "upload_info": {
        "upload_id": "uuid",
        "upload_type": "transactions",
        "total_rows": 100,
        "successful_rows": 95,
        "analysis_period": "2023-11-01 to 2023-12-01"
    },
    "statistics": {
        "total_transactions": 95,
        "total_amount": 15000.00,
        "net_cash_flow": 2000.00,
        "income": {"total": 8500.00, "count": 15},
        "expenses": {"total": 6500.00, "count": 80},
        "top_expense_categories": [
            {"category": "Food & Dining", "amount": 1200.00, "percentage": 18.5}
        ]
    },
    "insights": [
        "Positive cash flow indicates healthy financial position",
        "Food & Dining is the largest expense category"
    ],
    "recommendations": [
        "Consider setting up budgets for top expense categories",
        "Review Food & Dining expenses for optimization opportunities"
    ],
    "improvement_areas": [
        {
            "area": "Expense Optimization",
            "category": "Food & Dining",
            "current_spending": 1200.00,
            "suggestion": "Reduce Food & Dining spending by 10-20%",
            "potential_savings": 180.00,
            "priority": "Medium"
        }
    ]
}
```

#### Query Financial Data
**Endpoint:** `POST /rag-analysis/query_data/`

**Request:**
```json
{
    "query": "What are my top expense categories this month?",
    "company_id": "uuid"
}
```

**Response:**
```json
{
    "query": "What are my top expense categories this month?",
    "response": "Based on your financial data, your top expense categories are: 1) Food & Dining ($1,200), 2) Transportation ($800), 3) Utilities ($500)...",
    "timestamp": "2023-12-01T10:30:00Z"
}
```

### AI CFO Agent Endpoints

#### Chat with AI CFO
**Endpoint:** `POST /ai-cfo/chat/`

**Request:**
```json
{
    "message": "How can we improve our cash flow?",
    "company_id": "uuid"
}
```

**Response:**
```json
{
    "response": "Based on your current financial position with $2,000 positive cash flow, here are my recommendations for improvement: 1) Optimize payment terms with suppliers...",
    "financial_data": {
        "accounts": [...],
        "recent_transactions": [...]
    },
    "timestamp": "2023-12-01T10:30:00Z",
    "context_used": true
}
```

#### Get Financial Advice
**Endpoint:** `POST /ai-cfo/financial_advice/`

**Request:**
```json
{
    "topic": "cash_flow",
    "company_id": "uuid"
}
```

**Available Topics:**
- `cash_flow` - Cash Flow Management
- `cost_reduction` - Cost Reduction Strategies
- `investment` - Investment Opportunities
- `budgeting` - Budgeting Process Improvement
- `risk_management` - Financial Risk Management
- `growth` - Business Growth Financing
- `tax_optimization` - Tax Optimization Strategies
- `debt_management` - Debt Management

#### Analyze CSV Upload with CFO Perspective
**Endpoint:** `POST /ai-cfo/analyze_csv_upload/`

**Request:**
```json
{
    "bulk_upload_id": "uuid",
    "company_id": "uuid"
}
```

**Response:**
```json
{
    "rag_analysis": {
        // RAG analysis results
    },
    "cfo_perspective": {
        "response": "From a strategic perspective, this transaction data reveals several opportunities...",
        "timestamp": "2023-12-01T10:30:00Z"
    },
    "combined_recommendations": [
        "Implement automated expense categorization",
        "Set up monthly budget reviews",
        "Consider consolidating vendor payments"
    ]
}
```

#### Session Management
- `POST /ai-cfo/session_summary/` - Get conversation session summary
- `POST /ai-cfo/clear_session/` - Clear conversation history
- `GET /ai-cfo/available_topics/` - Get available advice topics

## Error Handling

### Standard Error Response
```json
{
    "error": "Error message",
    "detail": "Detailed error information",
    "timestamp": "2023-12-01T10:30:00Z"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting
- Standard endpoints: 1000 requests per hour
- AI endpoints: 100 requests per hour
- Bulk upload endpoints: 10 requests per hour

## Data Validation

### CSV Upload Validation
- Maximum file size: 10MB
- Maximum rows: 10,000 per upload
- Supported formats: CSV with UTF-8 encoding
- Required headers must match exactly (case-sensitive)

### Field Validation
- UUIDs must be valid UUID4 format
- Dates accept multiple formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY
- Decimal amounts support up to 15 digits with 2 decimal places
- Boolean fields accept: true/false, 1/0, yes/no (case-insensitive)

## Best Practices

### CSV Upload Best Practices
1. Always validate data before uploading
2. Use the template endpoint to get correct format
3. Upload in smaller batches (< 1000 rows) for better performance
4. Check error reports for failed uploads
5. Ensure account names exactly match existing accounts for transactions

### API Usage Best Practices
1. Implement proper error handling
2. Use pagination for large datasets
3. Cache frequently accessed data
4. Monitor rate limits
5. Validate input data client-side

### AI Features Best Practices
1. Be specific in queries for better responses
2. Provide context when asking questions
3. Use session management for longer conversations
4. Combine RAG analysis with CFO insights for comprehensive analysis
5. Regularly clear sessions to maintain performance

## Examples

### Complete Bulk Upload Workflow
```python
import requests

# 1. Upload CSV file
response = requests.post(
    'http://localhost:8000/api/financial/api/v1/bulk-uploads/upload_transactions/',
    files={'file': open('transactions.csv', 'rb')},
    data={'company_id': 'your-company-uuid'},
    headers={'Authorization': 'Bearer your-jwt-token'}
)

bulk_upload = response.json()
print(f"Upload ID: {bulk_upload['bulk_upload_id']}")

# 2. Get RAG analysis
analysis_response = requests.post(
    'http://localhost:8000/api/financial/api/v1/rag-analysis/analyze_upload/',
    json={'bulk_upload_id': bulk_upload['bulk_upload_id']},
    headers={'Authorization': 'Bearer your-jwt-token'}
)

analysis = analysis_response.json()
print(f"Insights: {analysis['insights']}")

# 3. Get CFO perspective
cfo_response = requests.post(
    'http://localhost:8000/api/financial/api/v1/ai-cfo/analyze_csv_upload/',
    json={
        'bulk_upload_id': bulk_upload['bulk_upload_id'],
        'company_id': 'your-company-uuid'
    },
    headers={'Authorization': 'Bearer your-jwt-token'}
)

cfo_analysis = cfo_response.json()
print(f"CFO Recommendations: {cfo_analysis['combined_recommendations']}")
```

### Interactive AI CFO Chat
```python
# Start conversation
chat_response = requests.post(
    'http://localhost:8000/api/financial/api/v1/ai-cfo/chat/',
    json={
        'message': 'What are our biggest financial risks right now?',
        'company_id': 'your-company-uuid'
    },
    headers={'Authorization': 'Bearer your-jwt-token'}
)

print(f"CFO: {chat_response.json()['response']}")

# Continue conversation
follow_up = requests.post(
    'http://localhost:8000/api/financial/api/v1/ai-cfo/chat/',
    json={
        'message': 'How can we mitigate these risks?',
        'company_id': 'your-company-uuid'
    },
    headers={'Authorization': 'Bearer your-jwt-token'}
)

print(f"CFO: {follow_up.json()['response']}")
```

This comprehensive API documentation covers all the new CSV upload functionality, RAG-based insights, and AI CFO Agent features you requested. The system now provides:

1. **Complete CSV Upload System** with validation and error tracking
2. **RAG-based Analysis** for intelligent insights from uploaded data
3. **AI CFO Agent** for interactive financial advisory
4. **Comprehensive Error Handling** and validation
5. **Detailed Documentation** with examples and best practices
