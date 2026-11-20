import pytest

from routing import geometry, risk


@pytest.mark.parametrize('wind, level', [
    (0, 'LOW'), (19.9, 'LOW'), (20, 'MODERATE'), (34.9, 'MODERATE'),
    (35, 'HIGH'), (44.9, 'HIGH'), (45, 'SEVERE'), (59.9, 'SEVERE'), (60, 'NO_TRAVEL'),
])
def test_wind_levels(wind, level):
    assert risk.evaluate(wind, 0, 0, load_weight_lb=1000).level == level


@pytest.mark.parametrize('rain, level', [(0.09, 'LOW'), (0.10, 'MODERATE'), (0.30, 'HIGH'), (0.50, 'SEVERE'), (3, 'SEVERE')])
def test_rain_levels(rain, level):
    assert risk.evaluate(0, rain, 0, 1000).level == level


@pytest.mark.parametrize('snow, level', [
    (0, 'LOW'), (0.1, 'MODERATE'), (0.25, 'HIGH'), (0.50, 'SEVERE'), (1.0, 'NO_TRAVEL'),
])
def test_snow_levels(snow, level):
    assert risk.evaluate(0, 0, snow, 1000).level == level


def test_heavy_load_escalates_wind_band_to_severe():
    result = risk.evaluate(38, 0, 0, load_weight_lb=42000)
    assert (result.level, result.score) == ('SEVERE', 3)
    assert result.reasons == ['Wind 38 mph = HIGH', 'Wind 35-44 mph and load > 40,000 lb -> SEVERE']


def test_heavy_load_rule_needs_more_than_40000_lb_and_the_wind_band():
    assert risk.evaluate(38, 0, 0, load_weight_lb=40000).level == 'HIGH'
    assert risk.evaluate(30, 0, 0, load_weight_lb=80000).level == 'MODERATE'
    assert risk.evaluate(45, 0, 0, load_weight_lb=80000).reasons == ['Wind 45 mph = SEVERE']


def test_level_is_highest_across_factors_and_calm_weather_has_no_reasons():
    result = risk.evaluate(25, 0.6, 0.3, 1000)
    assert result.level == 'SEVERE'
    assert result.reasons == ['Wind 25 mph = MODERATE', 'Rain 0.6 in/hr = SEVERE', 'Snow 0.3 in/hr = HIGH']
    calm = risk.evaluate(3, 0, 0, 1000)
    assert (calm.level, calm.score, calm.reasons) == ('LOW', 0, [])


def meridian(degrees):
    """Points along a meridian, one per degree of latitude (about 69.1 miles each)."""
    return [(float(i), 0.0) for i in range(degrees + 1)]


def test_checkpoints_start_at_the_interval_and_end_at_the_destination():
    points = meridian(2)
    total = geometry._cumulative_miles(points)[-1]
    cps = geometry.place_checkpoints(points, total, 50)
    assert [c.index for c in cps] == [1, 2, 3]
    assert [c.mile for c in cps[:2]] == [50, 100]
    assert cps[-1].mile == pytest.approx(total)
    assert (cps[-1].lat, cps[-1].lng) == (2.0, 0.0)
    assert cps[0].lat == pytest.approx(50 / total * 2, rel=1e-6)


def test_checkpoint_near_the_destination_is_merged_into_it():
    cps = geometry.place_checkpoints(meridian(1), 50.0, 25)
    assert [c.mile for c in cps] == [25, 50.0]
    cps = geometry.place_checkpoints(meridian(1), 50.01, 25)
    assert [c.mile for c in cps] == [25, 50.01]


def test_short_route_has_only_the_destination_checkpoint():
    cps = geometry.place_checkpoints(meridian(1), 12.0, 25)
    assert [(c.index, c.mile) for c in cps] == [(1, 12.0)]
