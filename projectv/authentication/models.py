from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class OAuthToken(models.Model):
    PROVIDER_CHOICES = (
        ('google', 'Google'),
        ('github', 'GitHub'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oauth_tokens')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'provider')
        
    @property
    def is_expired(self):
        if not self.expires_at:
            return True
        return self.expires_at <= timezone.now()