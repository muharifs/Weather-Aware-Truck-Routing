"""Fake external world (Nominatim, OSRM, Open-Meteo) served through httpx.MockTransport."""
from datetime import datetime, timedelta, timezone

import httpx
import polyline
import pytest
from django.core.cache import cache

from routing.clients import geocoding, http

DALLAS = (32.7767, -96.797)
DENVER = (39.7392, -104.9903)
METERS_PER_MILE = 1609.344


def line(a, b, n=60, bend=0.0):
    """n points from a to b; bend shifts the middle so alternative routes differ."""
    points = []
    for i in range(n):
        t = i / (n - 1)
        offset = bend * 4 * t * (1 - t)
        points.append((a[0] + (b[0] - a[0]) * t + offset, a[1] + (b[1] - a[1]) * t))
    return points


def osrm_route(points, miles, hours):
    return {
        'distance': miles * METERS_PER_MILE,
        'duration': hours * 3600,
        'geometry': polyline.encode(points, precision=5),
    }


class FakeWorld:
    def __init__(self):
        self.places = {'dallas, tx': DALLAS, 'denver, co': DENVER}
        self.routes = [
            osrm_route(line(DALLAS, DENVER), 795.0, 12.0),
            osrm_route(line(DALLAS, DENVER, bend=1.5), 880.0, 13.0),
        ]
        self.osrm_body = None  # override the whole OSRM JSON body
        self.weather = lambda lat, lng, ts, route_index=None: (5.0, 0.0, 0.0)  # wind, rain, snow
        self.status = {}  # service name -> forced HTTP status
        self.error = {}  # service name -> exception instance to raise
        self.weather_hours = None  # limit how many hours the forecast covers
        self.weather_bad_request = False
        self.calls = {'nominatim': 0, 'osrm': 0, 'open-meteo': 0}

    # --- handlers -----------------------------------------------------------------
    def handle(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        service = {'nominatim.openstreetmap.org': 'nominatim', 'router.project-osrm.org': 'osrm',
                   'api.open-meteo.com': 'open-meteo'}[host]
        self.calls[service] += 1
        if service in self.error:
            raise self.error[service]
        if service in self.status:
            return httpx.Response(self.status[service], json={'error': True})
        return getattr(self, f'_{service.replace("-", "_")}')(request)

    def _nominatim(self, request):
        place = self.places.get(request.url.params['q'].strip().casefold())
        if not place:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{'lat': str(place[0]), 'lon': str(place[1])}])

    def _osrm(self, request):
        if self.osrm_body is not None:
            return httpx.Response(200, json=self.osrm_body)
        return httpx.Response(200, json={'code': 'Ok', 'routes': self.routes})

    def _open_meteo(self, request):
        if self.weather_bad_request:
            return httpx.Response(400, json={'error': True, 'reason': 'Parameter start_date is out of allowed range'})
        params = request.url.params
        lats = [float(x) for x in params['latitude'].split(',')]
        lngs = [float(x) for x in params['longitude'].split(',')]
        start = datetime.fromisoformat(params['start_date']).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(params['end_date']).replace(tzinfo=timezone.utc) + timedelta(hours=23)
        times = []
        t = start
        while t <= end:
            times.append(int(t.timestamp()))
            t += timedelta(hours=1)
        if self.weather_hours:
            times = times[: self.weather_hours]
        items = []
        for lat, lng in zip(lats, lngs):
            values = [self.weather(lat, lng, ts) for ts in times]
            items.append({
                'timezone': 'America/Chicago' if lng > -100 else 'America/Denver',
                'hourly': {
                    'time': times,
                    'wind_speed_10m': [v[0] for v in values],
                    'rain': [v[1] for v in values],
                    'snowfall': [v[2] for v in values],
                },
            })
        return httpx.Response(200, json=items if len(items) > 1 else items[0])


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def world(monkeypatch):
    fake = FakeWorld()
    monkeypatch.setattr(
        http, 'build_http_client',
        lambda: httpx.Client(transport=httpx.MockTransport(fake.handle)),
    )
    monkeypatch.setattr(geocoding.time, 'sleep', lambda seconds: None)
    return fake


@pytest.fixture
def departure():
    """A valid departure time: two days from now, with an explicit UTC offset."""
    moment = datetime.now(timezone(timedelta(hours=-6))) + timedelta(days=2)
    return moment.replace(microsecond=0).isoformat()


@pytest.fixture
def payload(departure):
    return {
        'origin': 'Dallas, TX',
        'destination': 'Denver, CO',
        'departure_time': departure,
        'load_weight_lb': 42000,
        'checkpoint_interval_mi': 25,
    }


@pytest.fixture
def post():
    from rest_framework.test import APIClient

    def _post(body, **kwargs):
        return APIClient().post('/api/v1/routes/plan', body, format='json', **kwargs)

    return _post
