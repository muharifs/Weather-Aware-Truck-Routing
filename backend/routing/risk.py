"""Risk rules. All thresholds live here so they can be tuned without touching the logic."""
from dataclasses import dataclass

LEVELS = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL']
SCORES = {level: i for i, level in enumerate(LEVELS)}

# (exclusive upper bound, level); values at or above the last bound get the "top" level.
WIND_MPH = ([(20, 'LOW'), (35, 'MODERATE'), (45, 'HIGH'), (60, 'SEVERE')], 'NO_TRAVEL')
RAIN_IN_HR = ([(0.10, 'LOW'), (0.30, 'MODERATE'), (0.50, 'HIGH')], 'SEVERE')
SNOW_IN_HR = ([(1e-9, 'LOW'), (0.25, 'MODERATE'), (0.50, 'HIGH'), (1.00, 'SEVERE')], 'NO_TRAVEL')

# Heavy load rule: strong wind band + heavy load escalates wind to SEVERE.
HEAVY_LOAD_LB = 40_000
HEAVY_LOAD_WIND_MIN_MPH = 35
HEAVY_LOAD_WIND_MAX_MPH = 45  # exclusive
HEAVY_LOAD_REASON = 'Wind 35-44 mph and load > 40,000 lb -> SEVERE'


@dataclass(frozen=True)
class Risk:
    level: str
    score: int
    reasons: list


def _level(value, rule):
    bounds, top = rule
    for bound, level in bounds:
        if value < bound:
            return level
    return top


def evaluate(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_weight_lb: float) -> Risk:
    """Return the checkpoint risk: the highest level across factors, with reasons."""
    wind_level = _level(wind_mph, WIND_MPH)
    reasons = []
    if wind_level != 'LOW':
        reasons.append(f'Wind {wind_mph:g} mph = {wind_level}')
    if (
        load_weight_lb > HEAVY_LOAD_LB
        and HEAVY_LOAD_WIND_MIN_MPH <= wind_mph < HEAVY_LOAD_WIND_MAX_MPH
    ):
        wind_level = 'SEVERE'
        reasons.append(HEAVY_LOAD_REASON)

    levels = [wind_level]
    for name, value, rule, unit in (
        ('Rain', rain_in_hr, RAIN_IN_HR, 'in/hr'),
        ('Snow', snow_in_hr, SNOW_IN_HR, 'in/hr'),
    ):
        level = _level(value, rule)
        levels.append(level)
        if level != 'LOW':
            reasons.append(f'{name} {value:g} {unit} = {level}')

    top = max(levels, key=SCORES.__getitem__)
    return Risk(top, SCORES[top], reasons)
