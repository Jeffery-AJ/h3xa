# 📚 Complete API Documentation - Based on Actual Codebase

## 🚀 **Base URLs & Authentication**

**Main Application URL**: `http://localhost:8000`

### **API Endpoints Structure**:
- **Authentication**: `/api/auth/`
- **Core Financial**: `/api/v1/`
- **AI Insights**: `/api/ai/`
- **Open Banking**: `/api/open-banking/`
- **Fraud Detection**: `/api/fraud/`

---

## 🔐 **Authentication Endpoints** (`/api/auth/`)

### **User Management**
```http
POST /api/auth/register/          # Register new user
POST /api/auth/login/             # Login user
POST /api/auth/logout/            # Logout user
GET  /api/auth/user/              # Get user details
POST /api/auth/token/refresh/     # Refresh JWT token
```

### **OAuth Integration**
```http
POST /api/auth/google/            # Google OAuth login
POST /api/auth/github/            # GitHub OAuth login
GET  /api/auth/google/auth-url/   # Get Google OAuth URL
GET  /api/auth/github/auth-url/   # Get GitHub OAuth URL
POST /api/auth/google/callback/   # Google OAuth callback
POST /api/auth/github/callback/   # GitHub OAuth callback
POST /api/auth/google/refresh-token/  # Refresh Google token
POST /api/auth/github/refresh-token/  # Refresh GitHub token
```

---

## 🏢 **Core Financial API** (`/api/v1/`)

### **Companies** (`/api/v1/companies/`)
```http
GET    /api/v1/companies/                    # List companies
POST   /api/v1/companies/                    # Create company
GET    /api/v1/companies/{id}/               # Get company details
PUT    /api/v1/companies/{id}/               # Update company
DELETE /api/v1/companies/{id}/               # Delete company

# Custom Actions
GET    /api/v1/companies/{id}/dashboard/     # Company dashboard
GET    /api/v1/companies/{id}/analytics/     # Financial analytics
POST   /api/v1/companies/{id}/generate_report/  # Generate financial report
POST   /api/v1/companies/{id}/ai_insights/   # Get AI insights
```

### **Accounts** (`/api/v1/accounts/`)
```http
GET    /api/v1/accounts/                     # List accounts
POST   /api/v1/accounts/                     # Create account
GET    /api/v1/accounts/{id}/                # Get account details
PUT    /api/v1/accounts/{id}/                # Update account
DELETE /api/v1/accounts/{id}/                # Delete account

# Custom Actions
GET    /api/v1/accounts/{id}/balance_history/  # Account balance history
```

### **Transaction Categories** (`/api/v1/categories/`)
```http
GET    /api/v1/categories/                   # List categories
POST   /api/v1/categories/                   # Create category
GET    /api/v1/categories/{id}/              # Get category details
PUT    /api/v1/categories/{id}/              # Update category
DELETE /api/v1/categories/{id}/              # Delete category

# Custom Actions
GET    /api/v1/categories/income_expense_split/  # Income/expense breakdown
```

### **Transactions** (`/api/v1/transactions/`)
```http
GET    /api/v1/transactions/                 # List transactions
POST   /api/v1/transactions/                 # Create transaction
GET    /api/v1/transactions/{id}/            # Get transaction details
PUT    /api/v1/transactions/{id}/            # Update transaction
DELETE /api/v1/transactions/{id}/            # Delete transaction

# Custom Actions
GET    /api/v1/transactions/analytics/       # Transaction analytics
GET    /api/v1/transactions/cashflow_analysis/  # Cash flow analysis
POST   /api/v1/transactions/{id}/categorize/ # Auto-categorize transaction
POST   /api/v1/transactions/{id}/split/      # Split transaction
POST   /api/v1/transactions/bulk_categorize/ # Bulk categorization
```

### **Budgets** (`/api/v1/budgets/`)
```http
GET    /api/v1/budgets/                      # List budgets
POST   /api/v1/budgets/                      # Create budget
GET    /api/v1/budgets/{id}/                 # Get budget details
PUT    /api/v1/budgets/{id}/                 # Update budget
DELETE /api/v1/budgets/{id}/                 # Delete budget

# Custom Actions
POST   /api/v1/budgets/{id}/check_alerts/   # Check budget alerts
```

### **Financial Goals** (`/api/v1/goals/`)
```http
GET    /api/v1/goals/                        # List financial goals
POST   /api/v1/goals/                        # Create goal
GET    /api/v1/goals/{id}/                   # Get goal details
PUT    /api/v1/goals/{id}/                   # Update goal
DELETE /api/v1/goals/{id}/                   # Delete goal
```

### **Bulk Operations** (`/api/v1/bulk-uploads/`)
```http
GET    /api/v1/bulk-uploads/                 # List uploads
POST   /api/v1/bulk-uploads/                 # Create bulk upload
GET    /api/v1/bulk-uploads/{id}/            # Get upload details
DELETE /api/v1/bulk-uploads/{id}/            # Delete upload

# Custom Actions
POST   /api/v1/bulk-uploads/upload/          # Upload CSV file
GET    /api/v1/bulk-uploads/{id}/errors/     # Get upload errors
POST   /api/v1/bulk-uploads/{id}/retry/      # Retry failed uploads
```

---

## 🤖 **AI CFO Agent** (`/api/v1/ai-cfo/`)
```http
POST   /api/v1/ai-cfo/chat/                 # Chat with AI CFO
POST   /api/v1/ai-cfo/get_financial_advice/ # Get specialized advice
POST   /api/v1/ai-cfo/analyze_upload/       # Comprehensive CSV analysis
GET    /api/v1/ai-cfo/expertise_areas/      # Available expertise areas
GET    /api/v1/ai-cfo/session_summary/      # Conversation summary
```

**Example AI CFO Chat Request**:
```json
POST /api/v1/ai-cfo/chat/
{
    "message": "What's our current financial health?",
    "company_id": "company-uuid-here"
}
```

**Example Financial Advice Request**:
```json
POST /api/v1/ai-cfo/get_financial_advice/
{
    "topic": "cash_flow",
    "company_id": "company-uuid-here"
}
```

---

## 📊 **RAG Analysis** (`/api/v1/rag-analysis/`)
```http
POST   /api/v1/rag-analysis/analyze_upload/     # Analyze bulk upload
POST   /api/v1/rag-analysis/query_data/         # Natural language queries
POST   /api/v1/rag-analysis/analyze_csv_content/ # Direct CSV analysis
```

---

## 🧠 **AI Insights** (`/api/ai/`)

### **Financial Health** (`/api/ai/health/`)
```http
GET    /api/ai/health/                       # List health assessments
POST   /api/ai/health/                       # Create health assessment
GET    /api/ai/health/{id}/                  # Get specific assessment
```

### **Anomaly Detection** (`/api/ai/anomalies/`)
```http
GET    /api/ai/anomalies/                    # List detected anomalies
POST   /api/ai/anomalies/                    # Create anomaly detection
GET    /api/ai/anomalies/{id}/               # Get anomaly details
```

### **Smart Categorization** (`/api/ai/categorization/`)
```http
GET    /api/ai/categorization/               # List categorization rules
POST   /api/ai/categorization/               # Create categorization
GET    /api/ai/categorization/{id}/          # Get categorization details
```

### **Budget Insights** (`/api/ai/budget-insights/`)
```http
GET    /api/ai/budget-insights/              # List budget insights
POST   /api/ai/budget-insights/              # Generate insights
GET    /api/ai/budget-insights/{id}/         # Get specific insight
```

### **Goal Recommendations** (`/api/ai/goal-recommendations/`)
```http
GET    /api/ai/goal-recommendations/         # List recommendations
POST   /api/ai/goal-recommendations/         # Generate recommendations
GET    /api/ai/goal-recommendations/{id}/    # Get specific recommendation
```

### **AI Dashboard** (`/api/ai/dashboard/`)
```http
GET    /api/ai/dashboard/                    # AI-powered dashboard data
```

---

## 🏦 **Open Banking** (`/api/open-banking/`)

### **Bank Providers** (`/api/open-banking/providers/`)
```http
GET    /api/open-banking/providers/          # List bank providers
GET    /api/open-banking/providers/{id}/     # Get provider details

# Custom Actions
GET    /api/open-banking/providers/countries/      # Supported countries
GET    /api/open-banking/providers/provider_types/ # Provider types
```

### **Bank Connections** (`/api/open-banking/connections/`)
```http
GET    /api/open-banking/connections/        # List connections
POST   /api/open-banking/connections/        # Create connection
GET    /api/open-banking/connections/{id}/   # Get connection details
PUT    /api/open-banking/connections/{id}/   # Update connection
DELETE /api/open-banking/connections/{id}/   # Delete connection

# Custom Actions
POST   /api/open-banking/connections/initiate_connection/  # Start connection
POST   /api/open-banking/connections/{id}/complete_auth/   # Complete OAuth
POST   /api/open-banking/connections/{id}/sync_accounts/   # Sync accounts
POST   /api/open-banking/connections/{id}/sync_transactions/ # Sync transactions
POST   /api/open-banking/connections/{id}/disconnect/      # Disconnect bank
GET    /api/open-banking/connections/{id}/status/          # Connection status
```

### **Linked Bank Accounts** (`/api/open-banking/accounts/`)
```http
GET    /api/open-banking/accounts/           # List linked accounts
POST   /api/open-banking/accounts/           # Create linked account
GET    /api/open-banking/accounts/{id}/      # Get account details
PUT    /api/open-banking/accounts/{id}/      # Update account
DELETE /api/open-banking/accounts/{id}/      # Delete account

# Custom Actions
POST   /api/open-banking/accounts/{id}/create_local_account/  # Create local account
POST   /api/open-banking/accounts/{id}/sync_balance/          # Sync balance
```

### **Sync Logs** (`/api/open-banking/sync-logs/`)
```http
GET    /api/open-banking/sync-logs/          # List sync logs
GET    /api/open-banking/sync-logs/{id}/     # Get log details

# Custom Actions
GET    /api/open-banking/sync-logs/summary/  # Sync summary stats
```

### **Payments** (`/api/open-banking/payments/`)
```http
GET    /api/open-banking/payments/           # List payments
POST   /api/open-banking/payments/           # Create payment
GET    /api/open-banking/payments/{id}/      # Get payment details

# Custom Actions
POST   /api/open-banking/payments/initiate_payment/  # Initiate payment
GET    /api/open-banking/payments/{id}/check_status/ # Check payment status
```

### **Consents** (`/api/open-banking/consents/`)
```http
GET    /api/open-banking/consents/           # List consents
GET    /api/open-banking/consents/{id}/      # Get consent details

# Custom Actions
POST   /api/open-banking/consents/{id}/revoke/  # Revoke consent
```

---

## 🛡️ **Fraud Detection** (`/api/fraud/`)

### **Fraud Rules** (`/api/fraud/rules/`)
```http
GET    /api/fraud/rules/                     # List fraud rules
POST   /api/fraud/rules/                     # Create fraud rule
GET    /api/fraud/rules/{id}/                # Get rule details
PUT    /api/fraud/rules/{id}/                # Update rule
DELETE /api/fraud/rules/{id}/                # Delete rule

# Custom Actions
POST   /api/fraud/rules/{id}/test_rule/      # Test rule against transactions
GET    /api/fraud/rules/performance_metrics/ # Rule performance metrics
```

### **Fraud Alerts** (`/api/fraud/alerts/`)
```http
GET    /api/fraud/alerts/                    # List fraud alerts
POST   /api/fraud/alerts/                    # Create fraud alert
GET    /api/fraud/alerts/{id}/               # Get alert details
PUT    /api/fraud/alerts/{id}/               # Update alert
DELETE /api/fraud/alerts/{id}/               # Delete alert

# Custom Actions
POST   /api/fraud/alerts/{id}/resolve/       # Resolve alert
POST   /api/fraud/alerts/{id}/escalate/      # Escalate alert
GET    /api/fraud/alerts/dashboard/          # Fraud dashboard
POST   /api/fraud/alerts/analyze_transaction/ # Analyze transaction
```

### **Fraud Investigations** (`/api/fraud/investigations/`)
```http
GET    /api/fraud/investigations/            # List investigations
POST   /api/fraud/investigations/            # Create investigation
GET    /api/fraud/investigations/{id}/       # Get investigation details
PUT    /api/fraud/investigations/{id}/       # Update investigation
DELETE /api/fraud/investigations/{id}/       # Delete investigation

# Custom Actions
POST   /api/fraud/investigations/{id}/assign_investigator/  # Assign investigator
POST   /api/fraud/investigations/{id}/close_case/           # Close case
```

### **Whitelist** (`/api/fraud/whitelist/`)
```http
GET    /api/fraud/whitelist/                 # List whitelist entries
POST   /api/fraud/whitelist/                 # Create whitelist entry
GET    /api/fraud/whitelist/{id}/            # Get whitelist details
PUT    /api/fraud/whitelist/{id}/            # Update whitelist
DELETE /api/fraud/whitelist/{id}/            # Delete whitelist
```

### **Fraud Metrics** (`/api/fraud/metrics/`)
```http
GET    /api/fraud/metrics/                   # List fraud metrics
GET    /api/fraud/metrics/{id}/              # Get metric details

# Custom Actions
GET    /api/fraud/metrics/trends/            # Fraud detection trends
GET    /api/fraud/metrics/real_time_stats/   # Real-time statistics
```

---

## 🔒 **Authentication Requirements**

### **JWT Token Authentication**
All endpoints require authentication via JWT tokens:

```http
Authorization: Bearer <your-jwt-token>
```

### **Getting Authentication Token**
```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "your-username",
    "password": "your-password"
}
```

**Response**:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "your-username",
        "email": "user@example.com"
    }
}
```

---

## 📊 **Query Parameters & Filtering**

Most list endpoints support:
- **Filtering**: `?field=value`
- **Search**: `?search=query`
- **Ordering**: `?ordering=field` or `?ordering=-field` (descending)
- **Pagination**: `?page=1&page_size=20`

**Example**:
```http
GET /api/v1/transactions/?category=income&ordering=-date&page=1&page_size=50
```

---

## 📱 **Standard HTTP Response Codes**

- **200 OK** - Successful GET, PUT, PATCH
- **201 Created** - Successful POST
- **204 No Content** - Successful DELETE
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Authentication required
- **403 Forbidden** - Permission denied
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

---

## 🎯 **Error Response Format**

```json
{
    "error": "Error message",
    "code": "ERROR_CODE",
    "details": {
        "field": "Specific field error"
    }
}
```

This documentation is based on the actual codebase and reflects all available endpoints, actions, and functionality.
