from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rules', views.FraudDetectionRuleViewSet, basename='fraudrule')
router.register(r'alerts', views.FraudAlertViewSet, basename='fraudalert')
router.register(r'investigations', views.FraudInvestigationViewSet, basename='investigation')
router.register(r'whitelist', views.WhitelistEntryViewSet, basename='whitelist')
router.register(r'metrics', views.FraudMetricsViewSet, basename='fraudmetrics')

urlpatterns = [
    path('', include(router.urls)),
]
