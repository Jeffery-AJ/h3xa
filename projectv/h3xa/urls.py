from django.contrib import admin
from django.urls import include,path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/v1/', include('core.urls')),
    path('api/ai/', include('ai_insights.urls')),
    path('api/open-banking/', include('open_banking.urls')),
    path('api/fraud/', include('fraud_detection.urls')),
]
