import json
import re
from pathlib import Path

import httpx
import pytest

from .conftest import DALLAS, DENVER

FIXTURES = Path(__file__).resolve().parents[3] / 'docs' / 'api' / 'routes-plan'


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def shape(value):
    """Keys and primitive types, recursively. Lists are described by their first element."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(value[0])] if value else []
    return 'number' if isinstance(value, (int, float)) and not isinstance(value, bool) else type(value).__name__


def assert_same_shape(actual, expected):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and actual.keys() == expected.keys()
        for key in expected:
            assert_same_shape(actual[key], expected[key])
    elif isinstance(expected, list):
        assert isinstance(actual, list)
        if actual and expected:
            assert_same_shape(actual[0], expected[0])
    else:
        assert actual == expected


# --- success -----------------------------------------------------------------------

def test_success_matches_the_contract_fixture(world, post, payload):
    response = post(payload)
    assert response.status_code == 200
    assert_same_shape(shape(response.json()), shape(fixture('response-200.json')))


def test_routes_are_sorted_checkpoints_follow_the_interval_and_end_at_the_destination(world, post, payload):
    body = post(payload).json()
    assert 1 <= len(body['routes']) <= 3
    assert body['recommended_route_id'] == body['routes'][0]['id']
    for route in body['routes']:
        cps = route['checkpoints']
        assert [c['index'] for c in cps] == list(range(1, len(cps) + 1))
        assert [c['mile'] for c in cps[:3]] == [25, 50, 75]
        assert cps[-1]['mile'] == route['distance_mi']
        assert (cps[-1]['lat'], cps[-1]['lng']) == (round(DENVER[0], 5), round(DENVER[1], 5))
        assert route['arrival_time'] == cps[-1]['eta']


def test_eta_uses_local_time_zones_and_reflects_the_duration(world, post, payload):
    body = post(payload).json()
    route = next(r for r in body['routes'] if r['id'] == 'route_1')  # 12 hours long
    first_eta, arrival = route['checkpoints'][0]['eta'], route['arrival_time']
    assert first_eta.endswith(('-06:00', '-05:00'))  # Chicago zone near Dallas
    assert arrival.endswith(('-07:00', '-06:00'))  # Denver zone at the destination
    assert route['duration_min'] == 720


def test_interval_defaults_to_25(world, post, payload):
    del payload['checkpoint_interval_mi']
    cps = post(payload).json()['routes'][0]['checkpoints']
    assert [c['mile'] for c in cps[:2]] == [25, 50]


@pytest.mark.parametrize('interval', [10, 25, 50])
def test_allowed_intervals(world, post, payload, interval):
    payload['checkpoint_interval_mi'] = interval
    cps = post(payload).json()['routes'][0]['checkpoints']
    assert cps[0]['mile'] == interval


def test_coordinates_skip_geocoding(world, post, payload):
    payload['origin'] = {'lat': DALLAS[0], 'lng': DALLAS[1]}
    payload['destination'] = {'lat': DENVER[0], 'lng': DENVER[1]}
    assert post(payload).status_code == 200
    assert world.calls['nominatim'] == 0


def test_weather_is_fetched_in_one_batch_and_geocoding_is_cached(world, post, payload):
    assert post(payload).status_code == 200
    assert world.calls['open-meteo'] == 1
    assert world.calls['nominatim'] == 2
    assert post(payload).status_code == 200
    assert world.calls['nominatim'] == 2  # both addresses served from cache
    assert world.calls['open-meteo'] == 1  # same locations and window


def test_trailing_slash_is_accepted(world, post, payload):
    from rest_framework.test import APIClient
    assert APIClient().post('/api/v1/routes/plan/', payload, format='json').status_code == 200


# --- risk and recommendation ---------------------------------------------------------

def test_heavy_load_in_strong_wind_is_severe_with_reasons(world, post, payload):
    world.weather = lambda lat, lng, ts: (38.0, 0.05, 0.0)
    cp = post(payload).json()['routes'][0]['checkpoints'][0]
    assert cp['weather'] == {'wind_mph': 38.0, 'rain_in_hr': 0.05, 'snow_in_hr': 0.0}
    assert cp['risk'] == {
        'level': 'SEVERE', 'score': 3,
        'reasons': ['Wind 38 mph = HIGH', 'Wind 35-44 mph and load > 40,000 lb -> SEVERE'],
    }
    payload['load_weight_lb'] = 30000
    assert post(payload).json()['routes'][0]['checkpoints'][0]['risk']['level'] == 'HIGH'


def storm_on_route_one(lat, lng, ts):
    """Strong wind everywhere except near the route_2 detour (its middle bends north)."""
    return (50.0, 0.0, 0.0) if lat < 36.0 else (5.0, 0.0, 0.0)


def test_recommended_route_has_the_least_severe_miles_and_a_formatted_reason(world, post, payload):
    # route_2 bends north and so leaves the storm area (lat < 36) sooner than route_1.
    world.weather = storm_on_route_one
    body = post(payload).json()
    severe = {r['id']: r['summary']['severe_miles'] for r in body['routes']}
    assert severe['route_2'] < severe['route_1']
    assert body['recommended_route_id'] == 'route_2'
    assert [r['id'] for r in body['routes']] == ['route_2', 'route_1']
    best = body['routes'][0]
    s = best['summary']
    assert body['recommendation_reason'] == (
        f"Severe {s['severe_miles']:g} mi, High {s['high_miles']:g} mi, "
        f"rata-rata risiko {s['avg_risk_score']:g}, {best['duration_min']} menit"
    )
    assert re.fullmatch(r'Severe [\d.]+ mi, High [\d.]+ mi, rata-rata risiko [\d.]+, \d+ menit', body['recommendation_reason'])


def test_summary_counts_segment_miles_per_level(world, post, payload):
    world.weather = lambda lat, lng, ts: (50.0, 0.0, 0.0)  # SEVERE everywhere
    route = post(payload).json()['routes'][0]
    assert route['summary']['severe_miles'] == pytest.approx(route['distance_mi'], abs=0.2)
    assert route['summary']['high_miles'] == 0
    assert route['summary']['max_risk_level'] == 'SEVERE'
    assert route['summary']['avg_risk_score'] == 3
    assert route['summary']['has_no_travel'] is False


def test_route_with_no_travel_is_not_recommended_when_another_route_is_clear(world, post, payload):
    def north_of_straight_line(lat, lng):
        straight = DALLAS[0] + (DENVER[0] - DALLAS[0]) * (lng - DALLAS[1]) / (DENVER[1] - DALLAS[1])
        return lat > straight + 0.5

    # route_2 is faster, so it would win the tie-break, but only it crosses the NO_TRAVEL area.
    world.routes[1]['duration'] = 10 * 3600
    world.weather = lambda lat, lng, ts: (70.0, 0.0, 0.0) if north_of_straight_line(lat, lng) else (5.0, 0.0, 0.0)
    body = post(payload).json()
    flags = {r['id']: r['summary']['has_no_travel'] for r in body['routes']}
    assert flags == {'route_1': False, 'route_2': True}
    assert body['recommended_route_id'] == 'route_1'
    assert [r['id'] for r in body['routes']] == ['route_1', 'route_2']


def test_when_every_route_has_no_travel_the_usual_order_applies(world, post, payload):
    world.routes[1]['duration'] = 10 * 3600
    world.weather = lambda lat, lng, ts: (70.0, 0.0, 0.0)
    body = post(payload).json()
    assert all(r['summary']['has_no_travel'] for r in body['routes'])
    assert body['recommended_route_id'] == 'route_2'


# --- validation ----------------------------------------------------------------------

def test_validation_error_body_matches_the_fixture(world, post, payload):
    payload['load_weight_lb'] = 90000
    response = post(payload)
    assert response.status_code == 400
    assert response.json() == fixture('error-validation-error.json')


@pytest.mark.parametrize('field', ['origin', 'destination', 'departure_time', 'load_weight_lb'])
def test_required_fields(world, post, payload, field):
    del payload[field]
    response = post(payload)
    assert response.status_code == 400
    body = response.json()['error']
    assert body['code'] == 'VALIDATION_ERROR'
    assert body['details'][field] == ['Wajib diisi.']


@pytest.mark.parametrize('field, value', [
    ('origin', ''), ('origin', '   '), ('origin', 5), ('origin', {'lat': 1}), ('origin', {'lat': 91, 'lng': 0}),
    ('destination', {'lat': 0, 'lng': 181}), ('destination', None),
    ('load_weight_lb', 0), ('load_weight_lb', 80001), ('load_weight_lb', '42000'), ('load_weight_lb', True),
    ('checkpoint_interval_mi', 15), ('checkpoint_interval_mi', '25'), ('checkpoint_interval_mi', 0),
])
def test_invalid_values(world, post, payload, field, value):
    payload[field] = value
    response = post(payload)
    assert response.status_code == 400
    assert field in response.json()['error']['details']


@pytest.mark.parametrize('value', [1, 80000, 0.5 + 0.5, 42000.5])
def test_load_weight_boundaries_and_decimals_are_accepted(world, post, payload, value):
    payload['load_weight_lb'] = value
    assert post(payload).status_code == 200


def test_origin_and_destination_must_differ(world, post, payload):
    payload['destination'] = ' dallas, tx '.upper()
    response = post(payload)
    assert response.status_code == 400
    assert 'destination' in response.json()['error']['details']
    payload['origin'] = payload['destination'] = {'lat': 10, 'lng': 20}
    assert post(payload).status_code == 400


def test_departure_time_rules(world, post, payload):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cases = {
        'no timezone': '2026-12-01T08:00:00',
        'not a date': 'tomorrow',
        'past': (now - timedelta(minutes=5)).isoformat(),
        'too far': (now + timedelta(days=7, minutes=5)).isoformat(),
        'number': 1234,
    }
    for name, value in cases.items():
        payload['departure_time'] = value
        response = post(payload)
        assert response.status_code == 400, name
        assert 'departure_time' in response.json()['error']['details'], name
    payload['departure_time'] = (now + timedelta(days=6, hours=23)).isoformat().replace('+00:00', 'Z')
    assert post(payload).status_code == 200


def test_malformed_json_is_a_validation_error(world):
    from rest_framework.test import APIClient
    response = APIClient().post('/api/v1/routes/plan', '{oops', content_type='application/json')
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_non_object_body_is_a_validation_error(world, post):
    response = post([1, 2])
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


# --- upstream errors -----------------------------------------------------------------

def assert_error(response, status, code, fixture_name):
    assert response.status_code == status
    assert response.json() == fixture(fixture_name)
    assert response.json()['error']['code'] == code


def test_unknown_address_is_location_not_found(world, post, payload):
    payload['origin'] = 'Nowhereville'
    assert_error(post(payload), 422, 'LOCATION_NOT_FOUND', 'error-location-not-found.json')


@pytest.mark.parametrize('body', [{'code': 'NoRoute', 'routes': []}, {'code': 'NoSegment'}, {'code': 'Ok', 'routes': []}])
def test_no_land_route(world, post, payload, body):
    world.osrm_body = body
    assert_error(post(payload), 422, 'NO_ROUTE_FOUND', 'error-no-route-found.json')


def test_eta_beyond_the_forecast_is_forecast_unavailable(world, post, payload):
    world.weather_hours = 3  # the provider only covers the first three hours
    assert_error(post(payload), 422, 'FORECAST_UNAVAILABLE', 'error-forecast-unavailable.json')


def test_provider_rejecting_the_dates_is_forecast_unavailable(world, post, payload):
    world.weather_bad_request = True
    assert_error(post(payload), 422, 'FORECAST_UNAVAILABLE', 'error-forecast-unavailable.json')


@pytest.mark.parametrize('service', ['nominatim', 'osrm', 'open-meteo'])
def test_provider_quota_exhausted_is_rate_limited(world, post, payload, service):
    world.status[service] = 429
    assert_error(post(payload), 429, 'RATE_LIMITED', 'error-rate-limited.json')


@pytest.mark.parametrize('service', ['nominatim', 'osrm', 'open-meteo'])
@pytest.mark.parametrize('failure', ['http500', 'timeout'])
def test_provider_failure_is_upstream_error(world, post, payload, service, failure):
    if failure == 'http500':
        world.status[service] = 500
    else:
        world.error[service] = httpx.ConnectTimeout('timed out')
    assert_error(post(payload), 502, 'UPSTREAM_ERROR', 'error-upstream-error.json')


def test_malformed_provider_payload_is_upstream_error(world, post, payload):
    world.osrm_body = {'code': 'Ok', 'routes': [{'distance': 1}]}
    assert post(payload).status_code == 502
