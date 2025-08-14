from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ai_insights.views import (
    FinancialHealthViewSet,
    AnomalyDetectionViewSet,
    SmartCategorizationViewSet,
    BudgetInsightViewSet,
    FinancialGoalRecommendationViewSet,
    AIDashboardViewSet
)

router = DefaultRouter()
router.register(r'health', FinancialHealthViewSet, basename='health')
router.register(r'anomalies', AnomalyDetectionViewSet, basename='anomalies')
router.register(r'categorization', SmartCategorizationViewSet, basename='categorization')
router.register(r'budget-insights', BudgetInsightViewSet, basename='budget-insights')
router.register(r'goal-recommendations', FinancialGoalRecommendationViewSet, basename='goal-recommendations')
router.register(r'dashboard', AIDashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
