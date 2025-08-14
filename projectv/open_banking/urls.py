from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'providers', views.BankProviderViewSet)
router.register(r'connections', views.BankConnectionViewSet, basename='bankconnection')
router.register(r'accounts', views.LinkedBankAccountViewSet, basename='linkedbankaccount')
router.register(r'sync-logs', views.SyncLogViewSet, basename='synclog')
router.register(r'payments', views.PaymentInitiationViewSet, basename='paymentinit')
router.register(r'consents', views.ConsentManagementViewSet, basename='consent')

urlpatterns = [
    path('', include(router.urls)),
]
