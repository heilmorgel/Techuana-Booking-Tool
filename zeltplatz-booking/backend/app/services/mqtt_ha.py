"""Publish booking arrival/departure/active state to Home Assistant via MQTT Discovery."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import APP_VERSION
from app.config import Settings, get_settings
from app.database import SessionLocal
from app.services.booking_ha_state import BookingHaItem, BookingHaSnapshot, load_booking_ha_snapshot

logger = logging.getLogger(__name__)

AVAILABILITY_TOPIC = "zeltplatz/status"
EVENT_ARRIVAL_TOPIC = "zeltplatz/event/arrival"
EVENT_DEPARTURE_TOPIC = "zeltplatz/event/departure"

DEVICE = {
    "identifiers": ["zeltplatz_booking"],
    "name": "Zeltplatz Buchung",
    "manufacturer": "Techuana",
    "model": "Zeltplatz Booking Add-on",
    "sw_version": APP_VERSION,
}


def _items_signature(items: list[BookingHaItem]) -> str:
    return json.dumps([i.to_dict() for i in items], sort_keys=True, ensure_ascii=False)


def _attributes_payload(items: list[BookingHaItem]) -> str:
    return json.dumps({"bookings": [i.to_dict() for i in items]}, ensure_ascii=False)


def _event_payload(items: list[BookingHaItem], event: str) -> str:
    return json.dumps(
        {
            "event": event,
            "count": len(items),
            "bookings": [i.to_dict() for i in items],
        },
        ensure_ascii=False,
    )


def seconds_until_local_midnight(timezone_name: str) -> float:
    """Seconds until next local midnight in the given IANA timezone."""
    tz = None
    for candidate in (timezone_name, "UTC"):
        try:
            tz = ZoneInfo(candidate)
            break
        except Exception:
            continue
    if tz is None:
        now = datetime.now().astimezone()
        tomorrow = now.date() + timedelta(days=1)
        midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=now.tzinfo)
        return max((midnight - now).total_seconds(), 1.0)
    now = datetime.now(tz)
    tomorrow = now.date() + timedelta(days=1)
    midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=tz)
    return max((midnight - now).total_seconds(), 1.0)


class HaMqttPublisher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.enabled = self.settings.mqtt_enabled
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client = None
        self._run_task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._publish_requested = asyncio.Event()
        self._lock = asyncio.Lock()
        self._last_arrivals_sig: str | None = None
        self._last_departures_sig: str | None = None

    async def start(self) -> None:
        if not self.enabled:
            logger.info("MQTT disabled (no MQTT_HOST); HA publisher idle")
            return
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        self._publish_requested = asyncio.Event()
        self._run_task = asyncio.create_task(self._run_forever(), name="ha-mqtt-publisher")

    async def stop(self) -> None:
        self._stop.set()
        self._publish_requested.set()
        if self._run_task is not None:
            try:
                await asyncio.wait_for(self._run_task, timeout=10)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._run_task.cancel()
            self._run_task = None
        self._client = None
        self._loop = None

    def schedule_publish(self) -> None:
        """Thread-safe request to republish state (from sync FastAPI routes)."""
        if not self.enabled or self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._publish_requested.set)

    async def publish_state_now(self) -> None:
        if not self.enabled or self._client is None:
            return
        await self._publish_state(self._client)

    async def _run_forever(self) -> None:
        assert self.enabled
        while not self._stop.is_set():
            try:
                await self._session()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("MQTT session failed; retrying in 5s")
                self._client = None
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass

    async def _session(self) -> None:
        import aiomqtt

        settings = self.settings
        will = aiomqtt.Will(topic=AVAILABILITY_TOPIC, payload="offline", qos=1, retain=True)
        client_kwargs: dict = {
            "hostname": settings.mqtt_host,
            "port": settings.mqtt_port,
            "identifier": "zeltplatz_booking",
            "will": will,
        }
        if settings.mqtt_username:
            client_kwargs["username"] = settings.mqtt_username
            client_kwargs["password"] = settings.mqtt_password or None
        if settings.mqtt_ssl:
            import ssl

            client_kwargs["tls_context"] = ssl.create_default_context()

        logger.info(
            "Connecting to MQTT broker %s:%s",
            settings.mqtt_host,
            settings.mqtt_port,
        )
        async with aiomqtt.Client(**client_kwargs) as client:
            self._client = client
            await client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)
            await self._publish_discovery(client)
            await self._publish_state(client)

            while not self._stop.is_set():
                timeout = seconds_until_local_midnight(settings.timezone)
                self._publish_requested.clear()
                try:
                    await asyncio.wait_for(self._publish_requested.wait(), timeout=timeout)
                    reason = "change"
                except asyncio.TimeoutError:
                    reason = "midnight"
                if self._stop.is_set():
                    break
                logger.info("Publishing HA booking state (%s)", reason)
                await self._publish_state(client)

            try:
                await client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
            except Exception:
                logger.debug("Could not publish offline status", exc_info=True)
        self._client = None

    async def _publish_discovery(self, client) -> None:
        sensors = [
            (
                "active",
                "Aktive Buchungen",
                "zeltplatz_aktive_buchungen",
                "mdi:tent",
            ),
            (
                "arrivals",
                "Anreisen heute",
                "zeltplatz_anreisen_heute",
                "mdi:login",
            ),
            (
                "departures",
                "Abreisen heute",
                "zeltplatz_abreisen_heute",
                "mdi:logout",
            ),
        ]
        for key, name, object_id, icon in sensors:
            payload = {
                "name": name,
                "unique_id": f"zeltplatz_booking_{key}",
                "object_id": object_id,
                "state_topic": f"zeltplatz/sensor/{key}/state",
                "json_attributes_topic": f"zeltplatz/sensor/{key}/attributes",
                "availability_topic": AVAILABILITY_TOPIC,
                "payload_available": "online",
                "payload_not_available": "offline",
                "icon": icon,
                "state_class": "measurement",
                "device": DEVICE,
            }
            topic = f"homeassistant/sensor/zeltplatz_booking/{key}/config"
            await client.publish(topic, json.dumps(payload), qos=1, retain=True)

        binaries = [
            (
                "has_arrivals",
                "Hat Anreisen heute",
                "zeltplatz_hat_anreisen_heute",
                "mdi:login",
            ),
            (
                "has_departures",
                "Hat Abreisen heute",
                "zeltplatz_hat_abreisen_heute",
                "mdi:logout",
            ),
        ]
        for key, name, object_id, icon in binaries:
            payload = {
                "name": name,
                "unique_id": f"zeltplatz_booking_{key}",
                "object_id": object_id,
                "state_topic": f"zeltplatz/binary_sensor/{key}/state",
                "json_attributes_topic": f"zeltplatz/binary_sensor/{key}/attributes",
                "availability_topic": AVAILABILITY_TOPIC,
                "payload_available": "online",
                "payload_not_available": "offline",
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": icon,
                "device": DEVICE,
            }
            topic = f"homeassistant/binary_sensor/zeltplatz_booking/{key}/config"
            await client.publish(topic, json.dumps(payload), qos=1, retain=True)

    async def _publish_state(self, client) -> None:
        async with self._lock:
            snapshot = await asyncio.to_thread(self._load_snapshot)
            await self._publish_snapshot(client, snapshot)

    def _load_snapshot(self) -> BookingHaSnapshot:
        db = SessionLocal()
        try:
            return load_booking_ha_snapshot(db)
        finally:
            db.close()

    async def _publish_snapshot(self, client, snapshot: BookingHaSnapshot) -> None:
        pairs = [
            ("active", snapshot.active),
            ("arrivals", snapshot.arrivals),
            ("departures", snapshot.departures),
        ]
        for key, items in pairs:
            await client.publish(
                f"zeltplatz/sensor/{key}/state",
                str(len(items)),
                qos=1,
                retain=True,
            )
            await client.publish(
                f"zeltplatz/sensor/{key}/attributes",
                _attributes_payload(items),
                qos=1,
                retain=True,
            )

        await client.publish(
            "zeltplatz/binary_sensor/has_arrivals/state",
            "ON" if snapshot.arrivals else "OFF",
            qos=1,
            retain=True,
        )
        await client.publish(
            "zeltplatz/binary_sensor/has_arrivals/attributes",
            _attributes_payload(snapshot.arrivals),
            qos=1,
            retain=True,
        )
        await client.publish(
            "zeltplatz/binary_sensor/has_departures/state",
            "ON" if snapshot.departures else "OFF",
            qos=1,
            retain=True,
        )
        await client.publish(
            "zeltplatz/binary_sensor/has_departures/attributes",
            _attributes_payload(snapshot.departures),
            qos=1,
            retain=True,
        )

        arrivals_sig = _items_signature(snapshot.arrivals)
        if arrivals_sig != self._last_arrivals_sig:
            self._last_arrivals_sig = arrivals_sig
            if snapshot.arrivals:
                await client.publish(
                    EVENT_ARRIVAL_TOPIC,
                    _event_payload(snapshot.arrivals, "arrival"),
                    qos=1,
                    retain=False,
                )

        departures_sig = _items_signature(snapshot.departures)
        if departures_sig != self._last_departures_sig:
            self._last_departures_sig = departures_sig
            if snapshot.departures:
                await client.publish(
                    EVENT_DEPARTURE_TOPIC,
                    _event_payload(snapshot.departures, "departure"),
                    qos=1,
                    retain=False,
                )


_publisher: HaMqttPublisher | None = None


def get_ha_mqtt_publisher() -> HaMqttPublisher | None:
    return _publisher


async def start_ha_mqtt_publisher(settings: Settings | None = None) -> HaMqttPublisher:
    global _publisher
    publisher = HaMqttPublisher(settings or get_settings())
    _publisher = publisher
    await publisher.start()
    return publisher


async def stop_ha_mqtt_publisher() -> None:
    global _publisher
    if _publisher is not None:
        await _publisher.stop()
        _publisher = None


def schedule_booking_ha_publish() -> None:
    """Request HA MQTT republish after booking mutations (safe from sync routes)."""
    publisher = _publisher
    if publisher is None:
        return
    publisher.schedule_publish()
