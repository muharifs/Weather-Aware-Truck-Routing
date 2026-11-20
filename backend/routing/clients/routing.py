"""Road routing with alternatives via OSRM (car profile; swap this class for a truck provider)."""
from dataclasses import dataclass

from django.conf import settings

from ..errors import NoRouteFound, UpstreamError
from .geocoding import Place
from .http import request_json

METERS_PER_MILE = 1609.344
MAX_ROUTES = 3


@dataclass(frozen=True)
class ProviderRoute:
    distance_mi: float
    duration_s: float
    geometry: str  # encoded polyline, precision 5


class OsrmRouter:
    def __init__(self, client):
        self.client = client

    def routes(self, origin: Place, destination: Place) -> list[ProviderRoute]:
        coords = f'{origin.lng:.6f},{origin.lat:.6f};{destination.lng:.6f},{destination.lat:.6f}'
        data = request_json(
            self.client,
            f'{settings.OSRM_BASE_URL}/route/v1/driving/{coords}',
            {'alternatives': str(MAX_ROUTES), 'overview': 'full', 'geometries': 'polyline'},
        )
        if not isinstance(data, dict):
            raise UpstreamError()
        code = data.get('code')
        if code in ('NoRoute', 'NoSegment'):
            raise NoRouteFound()
        if code != 'Ok':
            raise UpstreamError()
        try:
            routes = [
                ProviderRoute(r['distance'] / METERS_PER_MILE, float(r['duration']), r['geometry'])
                for r in data['routes'][:MAX_ROUTES]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamError() from exc
        if not routes:
            raise NoRouteFound()
        return routes
