# 🏦 Financial Analytics Platform (ProjectV)

[![Django](https://img.shields.io/badge/Django-5.1.6-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![DRF](https://img.shields.io/badge/DRF-3.15.2-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive AI-powered financial analytics platform built with Django REST Framework, featuring fraud detection, open banking integration, and intelligent financial insights.

## 🌟 **Features**

### 🔐 **Authentication & Security**
- JWT-based authentication with refresh tokens
- OAuth2 integration (Google, GitHub)
- Multi-factor authentication support
- Secure password policies
- Token blacklisting for enhanced security

### 💰 **Core Financial Management**
- **Account Management**: Multiple account types support
- **Transaction Processing**: Real-time transaction tracking
- **Category Management**: Intelligent transaction categorization
- **Company Management**: Multi-company support
- **Bulk Operations**: CSV import/export capabilities

### 🤖 **AI-Powered Analytics**
- **Fraud Detection**: Machine learning-based anomaly detection
- **Financial Insights**: AI-driven financial advice and analysis
- **Predictive Analytics**: Spending pattern predictions
- **Risk Assessment**: Automated risk scoring
- **RAG (Retrieval-Augmented Generation)**: Document-based AI insights

### 🏛️ **Open Banking Integration**
- **Bank Connections**: Secure bank account linking
- **Transaction Sync**: Automated transaction synchronization
- **Balance Monitoring**: Real-time balance updates
- **Compliance**: PSD2 and regulatory compliance

### 🔍 **Fraud Detection System**
- **Real-time Monitoring**: Live transaction monitoring
- **Pattern Recognition**: Advanced fraud pattern detection
- **Risk Scoring**: Dynamic risk assessment
- **Alert System**: Configurable fraud alerts
- **Machine Learning**: Adaptive fraud detection models

## 🏗️ **Architecture**

```
ProjectV/
├── projectv/                    # Main Django project
│   ├── h3xa/                   # Project settings
│   ├── authentication/        # User management & OAuth
│   ├── core/                   # Core financial models
│   ├── ai_insights/           # AI analysis & insights
│   ├── open_banking/          # Bank integration
│   ├── fraud_detection/       # Fraud detection engine
│   └── manage.py
├── requirements.txt            # Python dependencies
├── README.md                  # This file
└── .env.example               # Environment variables template
```

## 🚀 **Quick Start**

### Prerequisites
- Python 3.11+
- PostgreSQL (recommended) or SQLite for development
- OpenAI API key (for AI features)
- OAuth credentials (Google/GitHub - optional)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ProjectV
```

### 2. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=your-openai-api-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### 5. Database Setup
```bash
cd projectv
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start Development Server
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## 📚 **API Documentation**

### **Base URLs**
- **Main**: `http://localhost:8000`
- **API Root**: `/api/`
- **Admin**: `/admin/`

### **API Endpoints Overview**

| Module | Base Path | Description |
|--------|-----------|-------------|
| Authentication | `/api/auth/` | User management, login, OAuth |
| Core Financial | `/api/v1/` | Accounts, transactions, companies |
| AI Insights | `/api/ai/` | AI analysis and recommendations |
| Open Banking | `/api/open-banking/` | Bank integrations |
| Fraud Detection | `/api/fraud/` | Fraud monitoring and alerts |

### **Authentication**
```http
POST /api/auth/register/          # Register new user
POST /api/auth/login/             # User login
POST /api/auth/logout/            # User logout
GET  /api/auth/user/              # Get user details
POST /api/auth/token/refresh/     # Refresh JWT token

# OAuth
GET  /api/auth/google/auth-url/   # Google OAuth URL
GET  /api/auth/github/auth-url/   # GitHub OAuth URL
POST /api/auth/google/            # Google login
POST /api/auth/github/            # GitHub login
```

### **Core Financial APIs**
```http
# Companies
GET    /api/v1/companies/         # List companies
POST   /api/v1/companies/         # Create company
GET    /api/v1/companies/{id}/    # Get company details

# Accounts
GET    /api/v1/accounts/          # List accounts
POST   /api/v1/accounts/          # Create account
GET    /api/v1/accounts/{id}/     # Get account details

# Transactions
GET    /api/v1/transactions/      # List transactions
POST   /api/v1/transactions/      # Create transaction
GET    /api/v1/transactions/{id}/ # Get transaction details

# Categories
GET    /api/v1/categories/        # List categories
POST   /api/v1/categories/        # Create category

# Bulk Operations
POST   /api/v1/bulk-import/       # Bulk import CSV data
```

### **AI & Analytics**
```http
POST   /api/ai/analyze/           # Financial analysis
POST   /api/ai/insights/          # Get AI insights
POST   /api/ai/risk-assessment/   # Risk analysis
POST   /api/ai/rag/upload/        # Upload documents for RAG
POST   /api/ai/rag/query/         # Query RAG system
```

### **Fraud Detection**
```http
GET    /api/fraud/alerts/         # Get fraud alerts
POST   /api/fraud/analyze/        # Analyze transaction for fraud
GET    /api/fraud/risk-score/     # Get risk scores
POST   /api/fraud/train-model/    # Train fraud detection model
```

For complete API documentation, see [COMPLETE_API_DOCS_CODEBASE.md](COMPLETE_API_DOCS_CODEBASE.md)

## 🧪 **Testing**

### **Run Tests**
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test authentication
python manage.py test core
python manage.py test ai_insights
python manage.py test fraud_detection
```

### **API Testing with Postman**
Import the Postman collection: `UPDATED_POSTMAN_COLLECTION_CODEBASE.json`

### **Sample Test Data**
```bash
# Load sample data
python manage.py loaddata sample_data.json

# Or use CSV samples
# - sample_accounts.csv
# - sample_categories.csv  
# - sample_transactions.csv
```

## 🛠️ **Development**

### **Code Structure**

#### **Authentication App**
- JWT authentication with refresh tokens
- OAuth2 integration (Google, GitHub)
- Custom user management
- Password policies and security

#### **Core App**
- Company and account management
- Transaction processing
- Category management
- Bulk data operations
- Financial calculations

#### **AI Insights App**
- OpenAI integration
- Financial analysis and advice
- Predictive analytics
- RAG system for document analysis

#### **Fraud Detection App**
- Machine learning models
- Real-time fraud detection
- Risk scoring algorithms
- Alert management system

#### **Open Banking App**
- Bank API integrations
- Transaction synchronization
- Balance monitoring
- Compliance management

### **Key Technologies**
- **Backend**: Django 5.1.6, Django REST Framework
- **Database**: PostgreSQL (recommended), SQLite (development)
- **Authentication**: JWT, OAuth2, Django Allauth
- **AI/ML**: OpenAI API, LangChain, scikit-learn
- **Data Processing**: Pandas, NumPy
- **Security**: Cryptography, secure token handling

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Core Django Settings
SECRET_KEY=your-secret-key
DEBUG=True/False
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:pass@host:port/db

# AI Configuration
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=1500

# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-id
GOOGLE_CLIENT_SECRET=your-google-secret
GITHUB_CLIENT_ID=your-github-id
GITHUB_CLIENT_SECRET=your-github-secret

# Security Settings
JWT_ACCESS_TOKEN_LIFETIME=30  # minutes
JWT_REFRESH_TOKEN_LIFETIME=7  # days
```

### **Database Configuration**
```python
# PostgreSQL (Recommended for production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'financial_analytics',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🚀 **Deployment**

### **Production Checklist**
- [ ] Set `DEBUG=False`
- [ ] Configure production database
- [ ] Set up HTTPS
- [ ] Configure CORS properly
- [ ] Set secure JWT settings
- [ ] Enable logging
- [ ] Set up monitoring
- [ ] Configure backup strategy

### **Docker Deployment** (Optional)
```dockerfile
# Dockerfile example
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Guidelines**
- Follow PEP 8 style guide
- Write comprehensive tests
- Update documentation
- Use meaningful commit messages
- Ensure backward compatibility

## 📝 **API Examples**

### **User Registration**
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password1": "SecurePass123!",
    "password2": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### **User Login**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "SecurePass123!"
  }'
```

### **Create Transaction**
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "account": 1,
    "amount": "-50.00",
    "description": "Coffee shop purchase",
    "category": 1,
    "transaction_type": "expense"
  }'
```

### **AI Financial Analysis**
```bash
curl -X POST http://localhost:8000/api/ai/analyze/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "company_id": 1,
    "analysis_type": "spending_patterns",
    "period": "last_month"
  }'
```

## 🛡️ **Security**

### **Authentication Flow**
1. User registers/logs in with credentials
2. Server returns JWT access token (30 min) and refresh token (7 days)
3. Client includes access token in Authorization header
4. Server validates token for protected endpoints
5. Client refreshes token when expired

### **Security Features**
- Password hashing with Django's PBKDF2
- JWT token blacklisting
- CORS protection
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting (configurable)

## 📊 **Monitoring & Logging**

### **Logging Configuration**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Authentication Error**
```
HTTP 401 Unauthorized: Authentication credentials were not provided
```
**Solution**: Ensure you're using POST method and include JWT token in Authorization header.

#### **Database Connection Error**
**Solution**: Check database settings in `.env` file and ensure database server is running.

#### **OpenAI API Error**
**Solution**: Verify OPENAI_API_KEY is set correctly and has sufficient credits.

#### **Import Error**
**Solution**: Ensure virtual environment is activated and all dependencies are installed.

## 📜 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- Django REST Framework for excellent API framework
- OpenAI for AI capabilities
- LangChain for AI orchestration
- All open source contributors

## 📞 **Support**

For support and questions:
- Create an issue in the repository
- Check the [API Documentation](COMPLETE_API_DOCS_CODEBASE.md)
- Review the Postman collection for examples

---

**Built with ❤️ using Django REST Framework**
