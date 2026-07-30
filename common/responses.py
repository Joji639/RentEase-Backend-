from rest_framework.response import Response
from rest_framework import status as http_status
from django.conf import settings


class APIResponse:

    @staticmethod
    def success(data=None, message="Success", status=http_status.HTTP_200_OK):
        return Response(
            {
                "success": True,
                "message": message,
                "errors": None,
                "data": data,
            },
            status=status,
        )

    @staticmethod
    def error(message="Something went wrong", errors=None, status=http_status.HTTP_400_BAD_REQUEST):
        return Response(
            {
                "success": False,
                "message": message,
                "errors": errors,
                "data": None,
            },
            status=status,
        )

    @staticmethod
    def set_refresh_cookie(response: Response, refresh_token: str) -> Response:
        """Attach the refresh token as an httpOnly cookie on the given response."""
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
            secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )
        return response

    @staticmethod
    def clear_refresh_cookie(response: Response) -> Response:
        """Remove the refresh token cookie — used on logout."""
        response.delete_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
        )
        return response