"""Request validation for POST /api/v1/routes/plan."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

ALLOWED_INTERVALS = (10, 25, 50)
DEFAULT_INTERVAL = 25
MAX_LOAD_LB = 80_000
MAX_DAYS_AHEAD = 7

REQUIRED = {'required': 'Wajib diisi.', 'null': 'Wajib diisi.'}


@dataclass(frozen=True)
class PlanRequest:
    origin: dict  # {'query': str} or {'lat': float, 'lng': float}
    destination: dict
    departure_time: datetime  # timezone-aware
    load_weight_lb: float
    checkpoint_interval_mi: int


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_location(value):
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise serializers.ValidationError('Wajib diisi.')
        return {'query': text}
    if isinstance(value, dict):
        lat, lng = value.get('lat'), value.get('lng')
        if not (_is_number(lat) and _is_number(lng)):
            raise serializers.ValidationError('Koordinat harus berupa {"lat": angka, "lng": angka}.')
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise serializers.ValidationError('Koordinat di luar jangkauan (lat -90 s/d 90, lng -180 s/d 180).')
        return {'lat': float(lat), 'lng': float(lng)}
    raise serializers.ValidationError('Harus berupa alamat (teks) atau {"lat", "lng"}.')


def _same_location(a, b):
    if 'query' in a and 'query' in b:
        return a['query'].casefold() == b['query'].casefold()
    if 'lat' in a and 'lat' in b:
        return round(a['lat'], 5) == round(b['lat'], 5) and round(a['lng'], 5) == round(b['lng'], 5)
    return False


class PlanRequestSerializer(serializers.Serializer):
    origin = serializers.JSONField(error_messages=REQUIRED)
    destination = serializers.JSONField(error_messages=REQUIRED)
    departure_time = serializers.JSONField(error_messages=REQUIRED)
    load_weight_lb = serializers.JSONField(error_messages=REQUIRED)
    checkpoint_interval_mi = serializers.JSONField(required=False)

    def validate_origin(self, value):
        return _parse_location(value)

    def validate_destination(self, value):
        return _parse_location(value)

    def validate_departure_time(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError('Harus berupa teks ISO 8601 dengan zona waktu.')
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            raise serializers.ValidationError('Format harus ISO 8601, contoh 2026-11-20T08:00:00-06:00.')
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise serializers.ValidationError('Harus menyertakan zona waktu, contoh -06:00 atau Z.')
        now = timezone.now()
        if parsed < now:
            raise serializers.ValidationError('Tidak boleh di masa lalu.')
        if parsed > now + timedelta(days=MAX_DAYS_AHEAD):
            raise serializers.ValidationError(f'Maksimal {MAX_DAYS_AHEAD} hari ke depan.')
        return parsed

    def validate_load_weight_lb(self, value):
        if not _is_number(value) or not 1 <= value <= MAX_LOAD_LB:
            raise serializers.ValidationError(f'Harus antara 1 dan {MAX_LOAD_LB}.')
        return value

    def validate_checkpoint_interval_mi(self, value):
        if not _is_number(value) or value not in ALLOWED_INTERVALS:
            raise serializers.ValidationError('Harus salah satu dari 10, 25, atau 50.')
        return int(value)

    def validate(self, attrs):
        if _same_location(attrs['origin'], attrs['destination']):
            raise serializers.ValidationError({'destination': ['Tidak boleh sama dengan origin.']})
        attrs.setdefault('checkpoint_interval_mi', DEFAULT_INTERVAL)
        return attrs

    def to_request(self) -> PlanRequest:
        data = self.validated_data
        return PlanRequest(
            origin=data['origin'],
            destination=data['destination'],
            departure_time=data['departure_time'],
            load_weight_lb=data['load_weight_lb'],
            checkpoint_interval_mi=data['checkpoint_interval_mi'],
        )
