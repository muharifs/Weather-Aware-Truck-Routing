"""API error classes and the DRF exception handler producing the contract's error body."""
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler


class ApiError(Exception):
    status_code = 500
    code = 'INTERNAL_ERROR'
    message = 'Terjadi kesalahan.'

    def __init__(self, details=None):
        super().__init__(self.message)
        self.details = details or {}


class ValidationApiError(ApiError):
    status_code = 400
    code = 'VALIDATION_ERROR'
    message = 'Input tidak valid'


class LocationNotFound(ApiError):
    status_code = 422
    code = 'LOCATION_NOT_FOUND'
    message = 'Alamat tidak ditemukan'


class NoRouteFound(ApiError):
    status_code = 422
    code = 'NO_ROUTE_FOUND'
    message = 'Tidak ada rute darat'


class ForecastUnavailable(ApiError):
    status_code = 422
    code = 'FORECAST_UNAVAILABLE'
    message = 'ETA di luar jangkauan prakiraan'


class RateLimited(ApiError):
    status_code = 429
    code = 'RATE_LIMITED'
    message = 'Kuota API eksternal habis'


class UpstreamError(ApiError):
    status_code = 502
    code = 'UPSTREAM_ERROR'
    message = 'API routing atau cuaca gagal'


def error_response(error: ApiError):
    body = {'error': {'code': error.code, 'message': error.message, 'details': error.details}}
    return Response(body, status=error.status_code)


def _normalize_details(detail):
    """Turn DRF error detail into {field: [message, ...]}."""
    if isinstance(detail, dict):
        return {
            str(field): [str(m) for m in (msgs if isinstance(msgs, list) else [msgs])]
            for field, msgs in detail.items()
        }
    msgs = detail if isinstance(detail, list) else [detail]
    return {'non_field_errors': [str(m) for m in msgs]}


def exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return error_response(exc)
    if isinstance(exc, drf_exceptions.ValidationError):
        return error_response(ValidationApiError(_normalize_details(exc.detail)))
    if isinstance(exc, drf_exceptions.ParseError):
        return error_response(ValidationApiError({'non_field_errors': ['Body harus berupa JSON yang valid.']}))
    response = drf_default_handler(exc, context)
    if response is not None:
        code = getattr(exc, 'default_code', 'error')
        response.data = {'error': {'code': str(code).upper(), 'message': str(exc.detail), 'details': {}}}
    return response
