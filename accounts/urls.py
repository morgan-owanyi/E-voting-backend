# accounts/urls.py
from django.urls import path
from .views import RegisterView, RequestOTPView, VerifyOTPView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("register/", RegisterView.as_view(), name="account-register"),
    path("request-otp/", RequestOTPView.as_view(), name="request-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("token/", obtain_auth_token, name="api-token-auth"),  # optional token auth
]
