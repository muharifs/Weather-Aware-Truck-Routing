"""Geocoding via Nominatim (1 request/second policy)."""
import hashlib
import threading
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from ..errors import LocationNotFound, UpstreamError
from .http import request_json

CACHE_TTL = 24 * 3600
_lock = threading.Lock()
_last_call = 0.0


@dataclass(frozen=True)
class Place:
    lat: float
    lng: float


class NominatimGeocoder:
    def __init__(self, client, min_interval: float = 1.1):
        self.client = client
        self.min_interval = min_interval

    def _wait_turn(self):
        global _last_call
        with _lock:
            delay = self.min_interval - (time.monotonic() - _last_call)
            if delay > 0:
                time.sleep(delay)
            _last_call = time.monotonic()

    def resolve(self, location: dict) -> Place:
        """location is {'lat','lng'} (used as is) or {'query': 'address text'}."""
        if 'lat' in location:
            return Place(location['lat'], location['lng'])
        query = location['query'].strip()
        key = 'geo:' + hashlib.sha1(query.casefold().encode()).hexdigest()
        cached = cache.get(key)
        if cached:
            return Place(*cached)
        self._wait_turn()
        data = request_json(
            self.client,
            f'{settings.NOMINATIM_BASE_URL}/search',
            {'q': query, 'format': 'json', 'limit': 1},
        )
        if not isinstance(data, list):
            raise UpstreamError()
        if not data:
            raise LocationNotFound()
        try:
            place = Place(float(data[0]['lat']), float(data[0]['lon']))
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamError() from exc
        cache.set(key, (place.lat, place.lng), CACHE_TTL)
        return place
