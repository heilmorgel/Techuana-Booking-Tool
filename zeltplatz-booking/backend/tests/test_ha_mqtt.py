"""Tests for Home Assistant booking classification and MQTT publisher helpers."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.services.booking_ha_state import (
    BookingHaItem,
    classify_bookings,
    is_active,
    is_arrival_today,
    is_departure_today,
    pitch_names_as_of,
)
from app.services.mqtt_ha import (
    HaMqttPublisher,
    schedule_booking_ha_publish,
    seconds_until_local_midnight,
)


def _booking(
    *,
    id: int,
    group_name: str,
    start: date,
    end: date,
    pitch_name: str = "Platz A",
) -> SimpleNamespace:
    pitch = SimpleNamespace(name=pitch_name)
    seg = SimpleNamespace(
        pitch_id=1,
        pitch=pitch,
        start_date=start,
        end_date=end,
    )
    return SimpleNamespace(
        id=id,
        group_name=group_name,
        start_date=start,
        end_date=end,
        booking_pitches=[seg],
    )


def test_active_half_open_interval():
    today = date(2026, 8, 15)
    b = _booking(id=1, group_name="G", start=date(2026, 8, 10), end=date(2026, 8, 15))
    assert is_active(b, today) is False  # departure day
    assert is_active(b, date(2026, 8, 14)) is True
    assert is_active(b, date(2026, 8, 10)) is True
    assert is_active(b, date(2026, 8, 9)) is False


def test_arrival_and_departure_today():
    today = date(2026, 8, 15)
    arrival = _booking(id=1, group_name="A", start=today, end=date(2026, 8, 20))
    departure = _booking(id=2, group_name="B", start=date(2026, 8, 10), end=today)
    other = _booking(id=3, group_name="C", start=date(2026, 8, 16), end=date(2026, 8, 18))

    assert is_arrival_today(arrival, today)
    assert not is_departure_today(arrival, today)
    assert is_departure_today(departure, today)
    assert not is_arrival_today(departure, today)
    assert not is_arrival_today(other, today)
    assert not is_departure_today(other, today)


def test_classify_bookings_groups():
    today = date(2026, 8, 15)
    bookings = [
        _booking(id=1, group_name="Aktiv", start=date(2026, 8, 14), end=date(2026, 8, 18)),
        _booking(id=2, group_name="Anreise", start=today, end=date(2026, 8, 20)),
        _booking(id=3, group_name="Abreise", start=date(2026, 8, 10), end=today),
        _booking(id=4, group_name="Zukunft", start=date(2026, 8, 20), end=date(2026, 8, 22)),
    ]
    snap = classify_bookings(bookings, today)
    assert [b.group_name for b in snap.active] == ["Aktiv", "Anreise"]
    assert [b.group_name for b in snap.arrivals] == ["Anreise"]
    assert [b.group_name for b in snap.departures] == ["Abreise"]
    assert snap.active_count == 2
    assert snap.arrivals_count == 1
    assert snap.departures_count == 1
    assert snap.active[0].pitch_names == ["Platz A"]
    assert snap.departures[0].pitch_names == ["Platz A"]


def test_pitch_names_as_of_filters_segments():
    today = date(2026, 8, 15)
    pitch_a = SimpleNamespace(name="A")
    pitch_b = SimpleNamespace(name="B")
    booking = SimpleNamespace(
        id=1,
        group_name="G",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 20),
        booking_pitches=[
            SimpleNamespace(pitch_id=1, pitch=pitch_a, start_date=date(2026, 8, 10), end_date=today),
            SimpleNamespace(pitch_id=2, pitch=pitch_b, start_date=today, end_date=date(2026, 8, 20)),
        ],
    )
    assert pitch_names_as_of(booking, today) == ["B"]
    assert pitch_names_as_of(booking, date(2026, 8, 14)) == ["A"]


def test_seconds_until_local_midnight_positive():
    secs = seconds_until_local_midnight("Europe/Vienna")
    assert 1.0 <= secs <= 24 * 3600 + 1


@pytest.mark.asyncio
async def test_publisher_disabled_is_noop():
    settings = Settings(mqtt_host="", data_dir=".")
    publisher = HaMqttPublisher(settings)
    assert publisher.enabled is False
    await publisher.start()
    publisher.schedule_publish()
    await publisher.publish_state_now()
    await publisher.stop()


@pytest.mark.asyncio
async def test_publish_snapshot_emits_sensors_and_events():
    settings = Settings(mqtt_host="localhost", data_dir=".")
    publisher = HaMqttPublisher(settings)
    client = AsyncMock()
    snapshot_items = [
        BookingHaItem(
            id=1,
            group_name="Pfadfinder",
            start_date="2026-08-15",
            end_date="2026-08-20",
            pitch_names=["Nord"],
        )
    ]
    snap = MagicMock()
    snap.active = snapshot_items
    snap.arrivals = snapshot_items
    snap.departures = []

    await publisher._publish_snapshot(client, snap)

    topics = [call.args[0] for call in client.publish.await_args_list]
    assert "zeltplatz/sensor/active/state" in topics
    assert "zeltplatz/sensor/arrivals/state" in topics
    assert "zeltplatz/binary_sensor/has_arrivals/state" in topics
    assert "zeltplatz/event/arrival" in topics
    assert "zeltplatz/event/departure" not in topics

    # Second publish with same arrivals must not re-fire event
    client.publish.reset_mock()
    await publisher._publish_snapshot(client, snap)
    topics2 = [call.args[0] for call in client.publish.await_args_list]
    assert "zeltplatz/event/arrival" not in topics2


def test_schedule_booking_ha_publish_without_publisher():
    with patch("app.services.mqtt_ha._publisher", None):
        schedule_booking_ha_publish()  # no-op
