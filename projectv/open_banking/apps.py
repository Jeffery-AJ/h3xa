from django.apps import AppConfig


class OpenBankingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'open_banking'
    
    def ready(self):
        import open_banking.signals
