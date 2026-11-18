"""Shared HTTP helpers. Tests replace build_http_client to inject httpx.MockTransport."""
import httpx
from django.conf import settings

from ..errors import RateLimited, UpstreamError


def build_http_client() -> httpx.Client:
    return httpx.Client(
        timeout=settings.HTTP_TIMEOUT_SECONDS,
        headers={'User-Agent': settings.HTTP_USER_AGENT},
    )


def request_json(client: httpx.Client, url: str, params=None, on_bad_request=None):
    """GET a JSON document, translating transport and HTTP failures to API errors.

    on_bad_request(body) may raise a more specific error for HTTP 400 responses.
    """
    try:
        response = client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise UpstreamError() from exc
    if response.status_code == 429:
        raise RateLimited()
    if response.status_code == 400 and on_bad_request:
        try:
            body = response.json()
        except ValueError:
            body = {}
        on_bad_request(body)
    if response.status_code >= 400:
        raise UpstreamError()
    try:
        return response.json()
    except ValueError as exc:
        raise UpstreamError() from exc
