from django.urls import path
from .views import (RegisterView,LoginView,LoginVerifyOTPView,
GoogleAuthView,TokenRefreshView,LogoutView,ForgotPasswordView,VerifyOTPView,
ResetPasswordView,ChangePasswordView,Setup2FAView,Enable2FAView,Disable2FAView,
)

urlpatterns = [
    
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("login/verify-otp/", LoginVerifyOTPView.as_view(), name="login-verify-otp"),
    path("google/", GoogleAuthView.as_view(), name="google-auth"),

    
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),

    
    path("password/forgot/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("password/verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("password/reset/", ResetPasswordView.as_view(), name="reset-password"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),

    
    path("2fasetup/", Setup2FAView.as_view(), name="2fa-setup"),
    path("2faenable/", Enable2FAView.as_view(), name="2fa-enable"),
    path("2fadisable/", Disable2FAView.as_view(), name="2fa-disable"),
]