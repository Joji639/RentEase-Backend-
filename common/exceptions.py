from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


class BaseAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"


class ValidationException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"


class ConflictException(BaseAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


class NotFoundException(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"


class PermissionDeniedException(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"


class AuthenticationFailedException(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "authentication_failed"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data

        if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
            message = detail["detail"]
            errors = None
        else:
            message = "Validation failed."
            errors = detail

        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
            "data": None,
        }
    return response