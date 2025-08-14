from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import bulk_views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet, basename='company')
router.register(r'accounts', views.AccountViewSet, basename='account')
router.register(r'categories', views.TransactionCategoryViewSet, basename='category')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'budgets', views.BudgetViewSet, basename='budget')
router.register(r'goals', views.FinancialGoalViewSet, basename='goal')
router.register(r'bulk-uploads', bulk_views.BulkUploadViewSet, basename='bulk-upload')
router.register(r'rag-analysis', views.FinancialRAGViewSet, basename='rag-analysis')
router.register(r'ai-cfo', views.AICFOViewSet, basename='ai-cfo')

app_name = 'core'

urlpatterns = [
    path('', include(router.urls)),
]
