# Enhanced Settings for ProjectV AI CFO
# Add these configurations to your settings.py

# Open Banking Configuration
OPEN_BANKING_REDIRECT_URI = 'https://your-domain.com/api/open-banking/callback/'
FAPI_FINANCIAL_ID = 'your-fapi-financial-id'

# UK Open Banking
UK_OPEN_BANKING_CLIENT_ID = os.getenv('UK_OPEN_BANKING_CLIENT_ID')
UK_OPEN_BANKING_CLIENT_SECRET = os.getenv('UK_OPEN_BANKING_CLIENT_SECRET')

# Plaid (US)
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_CLIENT_SECRET = os.getenv('PLAID_CLIENT_SECRET')
PLAID_ENVIRONMENT = os.getenv('PLAID_ENVIRONMENT', 'sandbox')  # sandbox, development, production

# TrueLayer
TRUELAYER_CLIENT_ID = os.getenv('TRUELAYER_CLIENT_ID')
TRUELAYER_CLIENT_SECRET = os.getenv('TRUELAYER_CLIENT_SECRET')

# Yapily
YAPILY_APPLICATION_ID = os.getenv('YAPILY_APPLICATION_ID')
YAPILY_APPLICATION_SECRET = os.getenv('YAPILY_APPLICATION_SECRET')

# AI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')

# Fraud Detection Settings
FRAUD_DETECTION_ENABLED = True
FRAUD_AUTO_BLOCK_THRESHOLD = 90  # Risk score threshold for auto-blocking
FRAUD_ALERT_THRESHOLD = 70       # Risk score threshold for alerts

# Machine Learning Model Storage
ML_MODEL_STORAGE_PATH = os.path.join(BASE_DIR, 'ml_models')
os.makedirs(ML_MODEL_STORAGE_PATH, exist_ok=True)

# Celery Configuration (for background tasks)
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'app.log'),
            'formatter': 'verbose',
        },
        'fraud_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'fraud.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'fraud_detection': {
            'handlers': ['fraud_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'open_banking': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'ai_insights': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Ensure log directory exists
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Cache Configuration (Redis recommended for production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Security Settings for Production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
