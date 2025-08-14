# 🧠 AI-Powered Financial Analysis API - RAG Endpoints

## **Base URL:** `http://localhost:8000/api/financial/api/v1/`

## **Authentication Required**
```
Headers:
Authorization: Bearer <your_jwt_token>
```

---

## 🔍 **RAG Analysis Endpoints**

### **1. Analyze Bulk Upload with AI Insights**
**POST** `/rag-analysis/analyze_upload/`

**Purpose:** Get comprehensive AI-powered analysis of uploaded CSV data

**Request Body:**
```json
{
    "bulk_upload_id": "your-bulk-upload-uuid-here"
}
```

**Response Example:**
```json
{
    "upload_info": {
        "upload_id": "uuid-here",
        "upload_type": "transactions",
        "total_rows": 150,
        "successful_rows": 145,
        "analysis_period": "2023-11-01 to 2023-12-01"
    },
    "statistics": {
        "total_transactions": 145,
        "total_amount": 25000.00,
        "average_transaction": 172.41,
        "net_cash_flow": 3500.00,
        "income": {
            "total": 15000.00,
            "count": 25,
            "average": 600.00
        },
        "expenses": {
            "total": 11500.00,
            "count": 120,
            "average": 95.83
        },
        "top_expense_categories": [
            {
                "category": "Food & Dining",
                "amount": 2400.00,
                "percentage": 20.9
            },
            {
                "category": "Transportation",
                "amount": 1800.00,
                "percentage": 15.7
            }
        ]
    },
    "insights": [
        "Positive cash flow of $3,500 indicates healthy financial position",
        "Food & Dining represents 20.9% of total expenses - largest category",
        "Average transaction frequency suggests active financial management"
    ],
    "recommendations": [
        "Consider setting budgets for Food & Dining to control largest expense",
        "Review Transportation costs for optimization opportunities",
        "Implement automated savings for positive cash flow periods"
    ],
    "improvement_areas": [
        {
            "area": "Expense Optimization",
            "category": "Food & Dining",
            "current_spending": 2400.00,
            "suggestion": "Reduce Food & Dining spending by 15%",
            "potential_savings": 360.00,
            "priority": "High"
        }
    ],
    "summary": "Financial analysis shows strong cash flow management with opportunities for expense optimization in dining and transportation categories."
}
```

---

### **2. Natural Language Query on Financial Data**
**POST** `/rag-analysis/query_data/`

**Purpose:** Ask questions about your financial data in natural language

**Request Body:**
```json
{
    "query": "What are my top 3 expense categories this month and how much did I spend?",
    "company_id": "your-company-uuid-here"
}
```

**Sample Queries:**
- "What are my biggest expenses this month?"
- "How is my cash flow trending?"
- "Which accounts have the most activity?"
- "What categories am I overspending in?"
- "Show me unusual transactions"
- "How does this month compare to last month?"

**Response Example:**
```json
{
    "query": "What are my top 3 expense categories this month?",
    "response": "Based on your financial data, your top 3 expense categories this month are: 1) Food & Dining with $2,400 (20.9% of expenses), 2) Transportation with $1,800 (15.7% of expenses), and 3) Utilities with $1,200 (10.4% of expenses). These three categories represent 47% of your total monthly expenses.",
    "timestamp": "2025-08-13T10:30:00Z"
}
```

---

### **3. Direct CSV Analysis (No Upload Required)**
**POST** `/rag-analysis/analyze_csv_content/`

**Purpose:** Get instant AI insights from any CSV file without saving to database

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: `<your_financial_data.csv>`

**Response Example:**
```json
{
    "csv_info": {
        "rows": 150,
        "columns": ["Date", "Description", "Amount", "Category", "Account"],
        "sample_data": [
            {
                "Date": "2023-12-01",
                "Description": "Grocery Store",
                "Amount": -45.67,
                "Category": "Food",
                "Account": "Checking"
            },
            {
                "Date": "2023-12-01", 
                "Description": "Salary Deposit",
                "Amount": 3000.00,
                "Category": "Income",
                "Account": "Checking"
            }
        ]
    },
    "ai_insights": "This financial dataset shows a healthy mix of income and expenses. The data appears well-categorized with clear transaction descriptions. Key observations: 1) Regular income patterns suggest steady employment, 2) Expense categories are diverse indicating varied spending habits, 3) Transaction amounts range from small daily purchases to larger periodic expenses. The negative amounts for expenses and positive for income follow standard accounting conventions.",
    "suggestions": [
        "Consider categorizing transactions by type for better analysis",
        "Review data for any missing or inconsistent entries", 
        "Identify patterns in spending or income",
        "Look for opportunities to optimize recurring expenses",
        "Set up budgets based on historical spending patterns"
    ],
    "timestamp": "2025-08-13T10:30:00Z"
}
```

---

## 🧪 **Postman Testing Examples**

### **Test 1: Upload and Analyze Workflow**
```javascript
// 1. First upload a CSV
POST /bulk-uploads/upload_transactions/
Body: form-data
- company_id: your-uuid
- file: transactions.csv

// 2. Get the bulk_upload_id from response, then analyze
POST /rag-analysis/analyze_upload/
Body: raw JSON
{
    "bulk_upload_id": "uuid-from-step-1"
}
```

### **Test 2: Natural Language Queries**
```javascript
POST /rag-analysis/query_data/
Body: raw JSON
{
    "query": "What's my spending pattern for food?",
    "company_id": "your-company-uuid"
}

// Try different queries:
// "How much did I spend on transportation last month?"
// "Which account has the highest activity?"
// "Show me my top income sources"
// "What are some unusual transactions?"
```

### **Test 3: Quick CSV Analysis**
```javascript
POST /rag-analysis/analyze_csv_content/
Body: form-data
- file: any_financial_csv_file.csv

// This works without needing company_id or pre-upload
```

---

## 📊 **Sample CSV for Testing**

Create a test file called `sample_transactions.csv`:

```csv
Date,Description,Amount,Category,Account
2023-12-01,Grocery Store,-125.50,Food & Dining,Main Checking
2023-12-01,Gas Station,-45.00,Transportation,Main Checking  
2023-12-02,Salary Deposit,3000.00,Income,Main Checking
2023-12-02,Rent Payment,-1200.00,Housing,Main Checking
2023-12-03,Coffee Shop,-8.50,Food & Dining,Main Checking
2023-12-03,Online Purchase,-89.99,Shopping,Credit Card
2023-12-04,Utility Bill,-150.00,Utilities,Main Checking
2023-12-04,Freelance Payment,500.00,Income,PayPal
2023-12-05,Restaurant,-65.00,Food & Dining,Credit Card
2023-12-05,Parking Fee,-12.00,Transportation,Main Checking
```

---

## 🎯 **Key Features**

### **Smart Analysis**
- **Automatic categorization** of financial patterns
- **Trend identification** across time periods  
- **Anomaly detection** for unusual transactions
- **Cash flow analysis** with projections

### **Natural Language Processing**
- **Ask questions** in plain English
- **Context-aware responses** based on your data
- **Intelligent insights** tailored to your financial situation

### **Real-time Insights**
- **Instant analysis** of CSV uploads
- **No storage required** for quick insights
- **Comprehensive reporting** with actionable recommendations

---

## 🚀 **Getting Started**

1. **Ensure you have financial data** (transactions, accounts, etc.)
2. **Get your JWT token** from authentication
3. **Start with CSV analysis** using `/analyze_csv_content/`  
4. **Upload data** for persistent analysis
5. **Ask natural language questions** about your finances

**The RAG system is now ready to provide intelligent financial insights from your CSV data!** 🎉
