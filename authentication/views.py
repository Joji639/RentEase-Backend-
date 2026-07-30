from django.shortcuts import render
from django.conf import settings

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from common.responses import APIResponse
from common.exceptions import AuthenticationFailedException, ValidationException
from common.permissions import HasCustom2FAPermission

from .serializers import RegisterSerializer, LoginSerializer
from .services import AuthService
from .serializers import (
    ForgotPasswordSerializer, VerifyOTPSerializer,
    ResetPasswordSerializer, ChangePasswordSerializer, Enable2FAVerifySerializer, Disable2FASerializer,
    LoginVerifyOTPSerializer, GoogleAuthSerializer
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = AuthService.register_user(serializer.validated_data)
            refresh_token = result["tokens"].pop("refresh")

            response = APIResponse.success(
                data=result,
                message="User registered successfully.",
                status=status.HTTP_201_CREATED,
            )
            return APIResponse.set_refresh_cookie(response, refresh_token)
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Registration failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = AuthService.login_user(serializer.validated_data)
            message = "Two-factor authentication code required." if result["requires_2fa"] else "Login successful."

            refresh_token = None
            if not result["requires_2fa"]:
                refresh_token = result["tokens"].pop("refresh")

            response = APIResponse.success(data=result, message=message, status=status.HTTP_200_OK)

            if refresh_token:
                response = APIResponse.set_refresh_cookie(response, refresh_token)

            return response
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Login failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoginVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginVerifyOTPSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = AuthService.verify_login_otp(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
            )
            refresh_token = result["tokens"].pop("refresh")

            response = APIResponse.success(data=result, message="Login successful.", status=status.HTTP_200_OK)
            return APIResponse.set_refresh_cookie(response, refresh_token)
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="OTP verification failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = GoogleAuthSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = AuthService.google_login(serializer.validated_data["id_token"])
            message = "Account created and logged in via Google." if result.pop("created") else "Login successful."
            refresh_token = result["tokens"].pop("refresh")

            response = APIResponse.success(
                data=result,
                message=message,
                status=status.HTTP_200_OK,
            )
            return APIResponse.set_refresh_cookie(response, refresh_token)
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Google login failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TokenRefreshView(APIView):

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)

            if not refresh_token:
                raise AuthenticationFailedException("Refresh token missing. Please log in again.")

            serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
            try:
                serializer.is_valid(raise_exception=True)
            except TokenError:
                raise AuthenticationFailedException("Invalid or expired refresh token. Please log in again.")

            access_token = serializer.validated_data["access"]
            new_refresh_token = serializer.validated_data.get("refresh")  # present since ROTATE_REFRESH_TOKENS=True

            response = APIResponse.success(
                data={"access": access_token},
                message="Token refreshed successfully.",
                status=status.HTTP_200_OK,
            )

            if new_refresh_token:
                response = APIResponse.set_refresh_cookie(response, new_refresh_token)

            return response
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Token refresh failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    pass

            response = APIResponse.success(message="Logged out successfully.", status=status.HTTP_200_OK)
            return APIResponse.clear_refresh_cookie(response)
        except Exception as e:
            return APIResponse.error(
                message="Logout failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ForgotPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            AuthService.forgot_password(serializer.validated_data["email"])

            return APIResponse.success(
                message="If an account with this email exists, an OTP has been sent.",
                status=status.HTTP_200_OK,
            )
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Request failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = VerifyOTPSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            AuthService.verify_otp(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
            )

            return APIResponse.success(
                message="OTP verified successfully.",
                status=status.HTTP_200_OK,
            )
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="OTP verification failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ResetPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            AuthService.reset_password(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
                new_password=serializer.validated_data["new_password"],
            )

            return APIResponse.success(
                message="Password has been reset successfully.",
                status=status.HTTP_200_OK,
            )
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Password reset failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = ChangePasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            AuthService.change_password(
                user=request.user,
                old_password=serializer.validated_data["old_password"],
                new_password=serializer.validated_data["new_password"],
            )

            return APIResponse.success(
                message="Password changed successfully.",
                status=status.HTTP_200_OK,
            )
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Password change failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class Setup2FAView(APIView):
    permission_classes = [IsAuthenticated, HasCustom2FAPermission]

    def post(self, request):
        try:
            result = AuthService.setup_2fa(request.user)
            return APIResponse.success(
                data=result,
                message="Scan the QR code with your authenticator app, then verify to enable 2FA.",
                status=status.HTTP_200_OK,
            )
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="2FA setup failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class Enable2FAView(APIView):
    permission_classes = [IsAuthenticated, HasCustom2FAPermission]

    def post(self, request):
        try:
            serializer = Enable2FAVerifySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            AuthService.enable_2fa(request.user, serializer.validated_data["code"])
            return APIResponse.success(message="Two-factor authentication enabled.", status=status.HTTP_200_OK)
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Enabling 2FA failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class Disable2FAView(APIView):
    permission_classes = [IsAuthenticated, HasCustom2FAPermission]

    def post(self, request):
        try:
            serializer = Disable2FASerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            AuthService.disable_2fa(request.user, serializer.validated_data["password"])
            return APIResponse.success(message="Two-factor authentication disabled.", status=status.HTTP_200_OK)
        except (ValidationError, ValidationException, AuthenticationFailedException):
            raise
        except Exception as e:
            return APIResponse.error(
                message="Disabling 2FA failed.", errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )