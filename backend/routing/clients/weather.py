"""Hourly weather via Open-Meteo, fetched in batches and cached per location."""
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.cache import cache

from ..errors import ForecastUnavailable, UpstreamError
from .http import request_json

CACHE_TTL = 30 * 60
BATCH_SIZE = 100
HOURLY_VARS = ('wind_speed_10m', 'rain', 'snowfall')


@dataclass(frozen=True)
class WeatherReading:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float
    timezone: str  # IANA name of the location


class OpenMeteoWeather:
    def __init__(self, client):
        self.client = client

    def readings(self, points: list[tuple[float, float, datetime]]) -> list[WeatherReading]:
        """points: (lat, lng, eta aware datetime). Returns one reading per point, same order."""
        if not points:
            return []
        etas = [p[2].astimezone(timezone.utc) for p in points]
        start = (min(etas) - timedelta(days=1)).date().isoformat()
        end = (max(etas) + timedelta(days=1)).date().isoformat()

        series = {}
        missing = []
        for lat, lng, _ in points:
            key = (round(lat, 2), round(lng, 2))
            if key in series or key in missing:
                continue
            cached = cache.get(self._cache_key(key, start, end))
            if cached:
                series[key] = cached
            else:
                missing.append(key)
        for i in range(0, len(missing), BATCH_SIZE):
            batch = missing[i:i + BATCH_SIZE]
            for key, data in zip(batch, self._fetch(batch, start, end)):
                series[key] = data
                cache.set(self._cache_key(key, start, end), data, CACHE_TTL)

        return [
            self._pick(series[(round(lat, 2), round(lng, 2))], eta)
            for (lat, lng, _), eta in zip(points, etas)
        ]

    @staticmethod
    def _cache_key(key, start, end):
        return f'wx:{key[0]}:{key[1]}:{start}:{end}'

    def _fetch(self, keys, start, end):
        data = request_json(
            self.client,
            f'{settings.OPEN_METEO_BASE_URL}/v1/forecast',
            {
                'latitude': ','.join(str(k[0]) for k in keys),
                'longitude': ','.join(str(k[1]) for k in keys),
                'hourly': ','.join(HOURLY_VARS),
                'wind_speed_unit': 'mph',
                'precipitation_unit': 'inch',
                'timezone': 'auto',
                'timeformat': 'unixtime',
                'start_date': start,
                'end_date': end,
            },
            on_bad_request=self._raise_for_bad_request,
        )
        items = data if isinstance(data, list) else [data]
        if len(items) != len(keys) or any(not isinstance(i, dict) for i in items):
            raise UpstreamError()
        result = []
        for item in items:
            try:
                hourly = item['hourly']
                result.append({
                    'times': hourly['time'],
                    'wind': hourly['wind_speed_10m'],
                    'rain': hourly['rain'],
                    'snow': hourly['snowfall'],
                    'tz': item['timezone'],
                })
            except (KeyError, TypeError) as exc:
                raise UpstreamError() from exc
        return result

    @staticmethod
    def _raise_for_bad_request(body):
        # Dates outside the provider's forecast window come back as HTTP 400 with a reason.
        reason = str(body.get('reason', '')) if isinstance(body, dict) else ''
        if 'range' in reason or 'date' in reason:
            raise ForecastUnavailable()

    @staticmethod
    def _pick(data, eta: datetime) -> WeatherReading:
        times = data['times']
        if not times:
            raise ForecastUnavailable()
        ts = eta.timestamp()
        i = bisect_left(times, ts)
        if i > 0 and (i == len(times) or ts - times[i - 1] <= times[i] - ts):
            i -= 1
        # The ETA must fall inside the covered hours (allow half an hour at the edges).
        if abs(times[i] - ts) > 1800:
            raise ForecastUnavailable()
        values = (data['wind'][i], data['rain'][i], data['snow'][i])
        if any(v is None for v in values):
            raise ForecastUnavailable()
        return WeatherReading(float(values[0]), float(values[1]), float(values[2]), data['tz'])
