from django.apps import AppConfig


class AiInsightsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_insights'
    
    def ready(self):
        import ai_insights.signals
