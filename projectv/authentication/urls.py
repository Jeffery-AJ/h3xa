from dj_rest_auth.registration.views import RegisterView
from authentication.views import (
    GoogleLogin, GithubLogin,
    GoogleAuthURL, GitHubAuthURL,
    google_callback, github_callback,
    refresh_google_token, refresh_github_token,
    custom_login, refresh_token, CustomRegisterView,
    CustomLogoutView, CustomUserDetailsView
)
from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView
from django.urls import path, re_path

urlpatterns = [
    path("register/", CustomRegisterView.as_view(), name="rest_register"),
    path("login/", custom_login, name="rest_login"),
    path("logout/", CustomLogoutView.as_view(), name="rest_logout"),
    path("user/", CustomUserDetailsView.as_view(), name="rest_user_details"),
    path("token/refresh/", refresh_token, name="token_refresh"),
    path('google/', GoogleLogin.as_view(), name="google_login"),
    path('github/', GithubLogin.as_view(), name='github_login'),
    path('google/auth-url/', GoogleAuthURL.as_view(), name="google_auth_url"),
    path('github/auth-url/', GitHubAuthURL.as_view(), name="github_auth_url"),
    path('google/callback/', google_callback, name='google_callback'),
    path('github/callback/', github_callback, name='github_callback'),
    path('google/refresh-token/', refresh_google_token, name='refresh_google_token'),
    path('github/refresh-token/', refresh_github_token, name='refresh_github_token'),
]