"""Route planning: routes -> checkpoints -> ETA -> weather -> risk -> summary -> recommendation."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import geometry, risk
from .errors import NoRouteFound
from .serializers import PlanRequest


def _round_to_minute(moment: datetime) -> datetime:
    return datetime.fromtimestamp(round(moment.timestamp() / 60) * 60, tz=timezone.utc)


def _summarize(checkpoints: list[dict]) -> dict:
    severe = high = 0.0
    previous_mile = 0.0
    for cp in checkpoints:
        segment = cp['mile'] - previous_mile
        previous_mile = cp['mile']
        if cp['risk']['level'] == 'SEVERE':
            severe += segment
        elif cp['risk']['level'] == 'HIGH':
            high += segment
    scores = [cp['risk']['score'] for cp in checkpoints]
    max_level = max((cp['risk']['level'] for cp in checkpoints), key=risk.SCORES.__getitem__)
    return {
        'severe_miles': round(severe, 1),
        'high_miles': round(high, 1),
        'avg_risk_score': round(sum(scores) / len(scores), 1),
        'max_risk_level': max_level,
        'has_no_travel': any(cp['risk']['level'] == 'NO_TRAVEL' for cp in checkpoints),
    }


def _sort_key(route: dict):
    s = route['summary']
    return (s['has_no_travel'], s['severe_miles'], s['high_miles'], s['avg_risk_score'], route['duration_min'])


def _reason(route: dict) -> str:
    s = route['summary']
    return (
        f"Severe {s['severe_miles']:g} mi, High {s['high_miles']:g} mi, "
        f"rata-rata risiko {s['avg_risk_score']:g}, {route['duration_min']} menit"
    )


def plan_routes(req: PlanRequest, geocoder, router, weather) -> dict:
    origin = geocoder.resolve(req.origin)
    destination = geocoder.resolve(req.destination)
    provider_routes = router.routes(origin, destination)

    departure = req.departure_time.astimezone(timezone.utc)
    drafts = []  # (route id, provider route, checkpoint points, eta per checkpoint)
    for n, pr in enumerate(provider_routes, start=1):
        points = geometry.decode(pr.geometry)
        if len(points) < 2 or pr.distance_mi <= 0:
            raise NoRouteFound()
        cps = geometry.place_checkpoints(points, pr.distance_mi, req.checkpoint_interval_mi)
        etas = [
            _round_to_minute(departure + timedelta(seconds=pr.duration_s * cp.mile / pr.distance_mi))
            for cp in cps
        ]
        drafts.append((f'route_{n}', pr, cps, etas))

    # One batched weather lookup for every checkpoint of every route.
    flat = [(cp.lat, cp.lng, eta) for _, _, cps, etas in drafts for cp, eta in zip(cps, etas)]
    readings = iter(weather.readings(flat))

    routes = []
    for route_id, pr, cps, etas in drafts:
        checkpoints = []
        zone = None
        for cp, eta in zip(cps, etas):
            reading = next(readings)
            zone = ZoneInfo(reading.timezone)
            result = risk.evaluate(reading.wind_mph, reading.rain_in_hr, reading.snow_in_hr, req.load_weight_lb)
            checkpoints.append({
                'index': cp.index,
                'mile': round(cp.mile, 1),
                'lat': round(cp.lat, 5),
                'lng': round(cp.lng, 5),
                'eta': eta.astimezone(zone).isoformat(),
                'weather': {
                    'wind_mph': round(reading.wind_mph, 1),
                    'rain_in_hr': round(reading.rain_in_hr, 2),
                    'snow_in_hr': round(reading.snow_in_hr, 2),
                },
                'risk': {'level': result.level, 'score': result.score, 'reasons': result.reasons},
            })
        routes.append({
            'id': route_id,
            'distance_mi': round(pr.distance_mi, 1),
            'duration_min': round(pr.duration_s / 60),
            'arrival_time': checkpoints[-1]['eta'],
            'geometry': pr.geometry,
            'summary': _summarize(checkpoints),
            'checkpoints': checkpoints,
        })

    routes.sort(key=_sort_key)
    return {
        'recommended_route_id': routes[0]['id'],
        'recommendation_reason': _reason(routes[0]),
        'routes': routes,
    }
