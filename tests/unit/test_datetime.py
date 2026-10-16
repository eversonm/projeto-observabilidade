from datetime import timezone

from app.observability.router import _parse_datetime


def test_parse_datetime_normalizes_z_suffix_to_utc():
    parsed = _parse_datetime("2026-10-16T12:00:00Z")
    assert parsed.tzinfo == timezone.utc

