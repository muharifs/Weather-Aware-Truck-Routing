"""Pure geometry helpers: decode a route polyline and place checkpoints along it."""
from bisect import bisect_left
from dataclasses import dataclass

import polyline
from geopy.distance import great_circle

MIN_TAIL_MI = 0.05  # a checkpoint closer than this to the destination is merged into it


@dataclass(frozen=True)
class CheckpointPoint:
    index: int
    mile: float
    lat: float
    lng: float


def decode(encoded: str) -> list[tuple[float, float]]:
    """Decode a precision-5 polyline into [(lat, lng), ...]."""
    return polyline.decode(encoded, precision=5)


def _cumulative_miles(points):
    total = 0.0
    cumulative = [0.0]
    for a, b in zip(points, points[1:]):
        total += great_circle(a, b).miles
        cumulative.append(total)
    return cumulative


def place_checkpoints(points, total_miles: float, interval_mi: int) -> list[CheckpointPoint]:
    """Checkpoints every interval_mi miles (first at mile=interval); the last one is the destination.

    Distances along the line are scaled so the end of the line equals the provider's total_miles.
    """
    if len(points) < 2 or total_miles <= 0:
        raise ValueError('route geometry needs at least two points and a positive length')
    cumulative = _cumulative_miles(points)
    line_total = cumulative[-1]

    targets = []
    k = 1
    while interval_mi * k < total_miles - MIN_TAIL_MI:
        targets.append(interval_mi * k)
        k += 1

    checkpoints = []
    for target in targets:
        d = target * line_total / total_miles
        i = bisect_left(cumulative, d)
        i = min(max(i, 1), len(points) - 1)
        span = cumulative[i] - cumulative[i - 1]
        frac = (d - cumulative[i - 1]) / span if span > 0 else 0.0
        lat = points[i - 1][0] + (points[i][0] - points[i - 1][0]) * frac
        lng = points[i - 1][1] + (points[i][1] - points[i - 1][1]) * frac
        checkpoints.append(CheckpointPoint(len(checkpoints) + 1, float(target), lat, lng))

    last = points[-1]
    checkpoints.append(CheckpointPoint(len(checkpoints) + 1, total_miles, last[0], last[1]))
    return checkpoints
