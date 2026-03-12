#!/usr/bin/env python3
"""
MQTT + Sparkplug B MCP Server using FastMCP.

This module keeps the original tool surface but normalizes tool outputs into
the suite's shared `{success, data, error, meta}` envelope so benchmarking and
cross-protocol reasoning can use one result contract.
"""

from __future__ import annotations

import asyncio
import os
import struct
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt
from mcp.server.fastmcp import Context, FastMCP


MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtt://127.0.0.1:1883")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "mqtt-mcp-python")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
SPARKPLUG_GROUP_ID = os.getenv("SPARKPLUG_GROUP_ID", "factory")
SPARKPLUG_EDGE_NODE_ID = os.getenv("SPARKPLUG_EDGE_NODE_ID", "edge-node-1")


def _make_result(
    success: bool,
    data: Any = None,
    error: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "data": data,
        "error": error,
        "meta": meta or {},
    }


def _duration_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 3)


def parse_mqtt_url(url: str) -> Tuple[str, int]:
    """Parse mqtt://host:port or mqtts://host:port."""
    if url.startswith("mqtt://"):
        url = url[7:]
    elif url.startswith("mqtts://"):
        url = url[8:]

    if ":" in url:
        host, port = url.split(":", 1)
        return host, int(port)
    return url, 1883


MQTT_HOST, MQTT_PORT = parse_mqtt_url(MQTT_BROKER_URL)


class MQTTClientManager:
    """Manage broker connectivity and Sparkplug bookkeeping."""

    def __init__(self) -> None:
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.subscriptions: set[str] = set()
        self.sparkplug_sequence: Dict[str, int] = {}
        self.birth_certificates: Dict[str, Dict[str, Any]] = {}

    async def connect(self) -> None:
        """Connect to the broker and wait briefly for the session to establish."""
        if self.connected and self.client:
            return

        def on_connect(client, userdata, flags, rc):  # noqa: ANN001
            self.connected = rc == 0

        def on_disconnect(client, userdata, rc):  # noqa: ANN001
            if rc != 0:
                self.connected = False

        def on_message(client, userdata, msg):  # noqa: ANN001
            return None

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=MQTT_CLIENT_ID,
        )
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=8)

        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        self.client.loop_start()

        deadline = time.monotonic() + 3.0
        while not self.connected and time.monotonic() < deadline:
            await asyncio.sleep(0.1)

    async def disconnect(self) -> None:
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.connected = False

    async def publish(
        self, topic: str, payload: bytes, qos: int = 0, retain: bool = False
    ) -> None:
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to MQTT broker")

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: self.client.publish(topic, payload, qos=qos, retain=retain),
        )
        info.wait_for_publish()
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Publish failed with rc={info.rc}")

    async def subscribe(self, topic: str, qos: int = 0) -> None:
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to MQTT broker")

        loop = asyncio.get_event_loop()
        result, _mid = await loop.run_in_executor(
            None,
            lambda: self.client.subscribe(topic, qos=qos),
        )
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Subscribe failed with rc={result}")
        self.subscriptions.add(topic)

    async def unsubscribe(self, topic: str) -> None:
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to MQTT broker")

        loop = asyncio.get_event_loop()
        result, _mid = await loop.run_in_executor(
            None,
            lambda: self.client.unsubscribe(topic),
        )
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Unsubscribe failed with rc={result}")
        self.subscriptions.discard(topic)

    def next_sequence(self, key: str) -> int:
        self.sparkplug_sequence[key] = (self.sparkplug_sequence.get(key, 0) + 1) % 256
        return self.sparkplug_sequence[key]

    @staticmethod
    def encode_varint(value: int) -> bytes:
        buf = bytearray()
        while (value & 0xFFFFFF80) != 0:
            buf.append((value & 0xFF) | 0x80)
            value >>= 7
        buf.append(value & 0xFF)
        return bytes(buf)

    def encode_metric_protobuf(self, name: str, value: Any, metric_type: str) -> bytes:
        parts = []
        name_bytes = name.encode("utf-8")
        parts.extend((bytes([0x0A]), self.encode_varint(len(name_bytes)), name_bytes))

        parts.extend((bytes([0x10]), self.encode_varint(int(time.time() * 1000))))

        metric_type = str(metric_type).lower()
        if metric_type in {"int", "int32"}:
            parts.extend((bytes([0x28]), self.encode_varint(int(value))))
        elif metric_type == "float":
            parts.extend((bytes([0x4D]), struct.pack("<f", float(value))))
        elif metric_type in {"bool", "boolean"}:
            parts.extend((bytes([0x58]), bytes([1 if value else 0])))
        else:
            value_bytes = str(value).encode("utf-8")
            parts.extend((bytes([0x62]), self.encode_varint(len(value_bytes)), value_bytes))

        return b"".join(parts)

    def encode_payload_protobuf(self, metrics: List[Dict[str, Any]], seq: int) -> bytes:
        parts = []
        parts.extend((bytes([0x08]), self.encode_varint(int(time.time() * 1000))))

        for metric in metrics:
            metric_bytes = self.encode_metric_protobuf(
                metric["name"],
                metric["value"],
                metric.get("type", "string"),
            )
            parts.extend((bytes([0x12]), self.encode_varint(len(metric_bytes)), metric_bytes))

        parts.extend((bytes([0x18]), self.encode_varint(seq)))
        return b"".join(parts)


def _read_varint(data: bytes, index: int) -> Tuple[int, int]:
    shift = 0
    value = 0
    while index < len(data):
        byte = data[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, index
        shift += 7
    raise ValueError("Truncated varint")


def _decode_metric(metric_bytes: bytes) -> Dict[str, Any]:
    index = 0
    metric: Dict[str, Any] = {}
    while index < len(metric_bytes):
        key = metric_bytes[index]
        index += 1
        field_number = key >> 3
        wire_type = key & 0x07

        if field_number in {1, 12} and wire_type == 2:
            length, index = _read_varint(metric_bytes, index)
            raw = metric_bytes[index : index + length]
            index += length
            if field_number == 1:
                metric["name"] = raw.decode("utf-8")
            else:
                metric["value"] = raw.decode("utf-8")
                metric["type"] = "string"
        elif field_number in {2, 5} and wire_type == 0:
            value, index = _read_varint(metric_bytes, index)
            if field_number == 2:
                metric["timestamp"] = value
            else:
                metric["value"] = value
                metric["type"] = "int32"
        elif field_number == 9 and wire_type == 5:
            metric["value"] = round(struct.unpack("<f", metric_bytes[index : index + 4])[0], 6)
            metric["type"] = "float"
            index += 4
        elif field_number == 11 and wire_type == 0:
            value, index = _read_varint(metric_bytes, index)
            metric["value"] = bool(value)
            metric["type"] = "boolean"
        else:
            raise ValueError(f"Unsupported metric field {field_number}/{wire_type}")
    return metric


def decode_sparkplug_payload_bytes(payload: bytes) -> Dict[str, Any]:
    index = 0
    result: Dict[str, Any] = {"metrics": []}

    while index < len(payload):
        key = payload[index]
        index += 1
        field_number = key >> 3
        wire_type = key & 0x07

        if field_number in {1, 3} and wire_type == 0:
            value, index = _read_varint(payload, index)
            if field_number == 1:
                result["timestamp"] = value
            else:
                result["seq"] = value
        elif field_number == 2 and wire_type == 2:
            length, index = _read_varint(payload, index)
            metric_bytes = payload[index : index + length]
            index += length
            result["metrics"].append(_decode_metric(metric_bytes))
        else:
            raise ValueError(f"Unsupported payload field {field_number}/{wire_type}")

    return result


@asynccontextmanager
async def mqtt_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    manager = MQTTClientManager()
    try:
        await manager.connect()
        yield {"mqtt_manager": manager}
    finally:
        await manager.disconnect()


def _topic_meta(manager: MQTTClientManager, start: float, **extra: Any) -> Dict[str, Any]:
    meta = {
        "duration_ms": _duration_ms(start),
        "connected": manager.connected,
        "attempts": 1,
    }
    meta.update(extra)
    return meta


mcp = FastMCP("MQTT-Control", lifespan=mqtt_lifespan)


@mcp.tool()
async def publish_message(
    topic: str, payload: str, qos: int = 0, retain: bool = False, ctx: Context = None
) -> Dict[str, Any]:
    """Publish a message to an MQTT topic."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    try:
        payload_bytes = payload.encode("utf-8")
        await manager.publish(topic, payload_bytes, qos=qos, retain=retain)
        return _make_result(
            True,
            data={
                "topic": topic,
                "qos": qos,
                "retain": retain,
                "payload_bytes": len(payload_bytes),
            },
            meta=_topic_meta(manager, start),
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Publish failed for {topic}: {exc}",
            meta=_topic_meta(manager, start, topic=topic, qos=qos),
        )


@mcp.tool()
async def subscribe_topic(topic: str, qos: int = 0, ctx: Context = None) -> Dict[str, Any]:
    """Subscribe to an MQTT topic pattern."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    try:
        await manager.subscribe(topic, qos=qos)
        return _make_result(
            True,
            data={"topic": topic, "qos": qos, "subscription_count": len(manager.subscriptions)},
            meta=_topic_meta(manager, start),
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Subscribe failed for {topic}: {exc}",
            meta=_topic_meta(manager, start, topic=topic, qos=qos),
        )


@mcp.tool()
async def unsubscribe_topic(topic: str, ctx: Context = None) -> Dict[str, Any]:
    """Unsubscribe from an MQTT topic."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    try:
        await manager.unsubscribe(topic)
        return _make_result(
            True,
            data={"topic": topic, "subscription_count": len(manager.subscriptions)},
            meta=_topic_meta(manager, start),
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Unsubscribe failed for {topic}: {exc}",
            meta=_topic_meta(manager, start, topic=topic),
        )


@mcp.tool()
def list_subscriptions(ctx: Context) -> Dict[str, Any]:
    """List active MQTT subscriptions."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    subscriptions = sorted(manager.subscriptions)
    return _make_result(
        True,
        data={"subscriptions": subscriptions, "count": len(subscriptions)},
        meta=_topic_meta(manager, start),
    )


@mcp.tool()
def get_broker_info(ctx: Context) -> Dict[str, Any]:
    """Get MQTT broker connection info and status."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    return _make_result(
        True,
        data={
            "broker_host": MQTT_HOST,
            "broker_port": MQTT_PORT,
            "connected": manager.connected,
            "subscriptions": len(manager.subscriptions),
            "client_id": MQTT_CLIENT_ID,
        },
        meta=_topic_meta(manager, start),
    )


def _sparkplug_publish_result(
    manager: MQTTClientManager,
    start: float,
    topic: str,
    seq: int,
    metrics: List[Dict[str, Any]],
    certificate_key: Optional[str] = None,
    certificate_value: Optional[Dict[str, Any]] = None,
    delete_certificate: bool = False,
) -> Dict[str, Any]:
    if certificate_key:
        if delete_certificate:
            manager.birth_certificates.pop(certificate_key, None)
        elif certificate_value is not None:
            manager.birth_certificates[certificate_key] = certificate_value

    return _make_result(
        True,
        data={"topic": topic, "seq": seq, "metric_count": len(metrics)},
        meta=_topic_meta(manager, start),
    )


@mcp.tool()
async def publish_node_birth(
    metrics: Optional[List[Dict[str, Any]]] = None, ctx: Context = None
) -> Dict[str, Any]:
    """Publish a Sparkplug B NBIRTH certificate."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}"
    payload_metrics = metrics or []
    try:
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/NBIRTH/{SPARKPLUG_EDGE_NODE_ID}"
        payload = manager.encode_payload_protobuf(payload_metrics, seq)
        await manager.publish(topic, payload, qos=1)
        return _sparkplug_publish_result(
            manager,
            start,
            topic,
            seq,
            payload_metrics,
            certificate_key=key,
            certificate_value={"type": "NBIRTH", "timestamp": int(time.time() * 1000)},
        )
    except Exception as exc:
        return _make_result(False, error=f"NBIRTH failed: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_node_death(ctx: Context = None) -> Dict[str, Any]:
    """Publish a Sparkplug B NDEATH certificate."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}"
    try:
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/NDEATH/{SPARKPLUG_EDGE_NODE_ID}"
        payload = manager.encode_payload_protobuf([], seq)
        await manager.publish(topic, payload, qos=1)
        return _sparkplug_publish_result(
            manager,
            start,
            topic,
            seq,
            [],
            certificate_key=key,
            delete_certificate=True,
        )
    except Exception as exc:
        return _make_result(False, error=f"NDEATH failed: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_device_birth(
    device_id: str, metrics: List[Dict[str, Any]], ctx: Context = None
) -> Dict[str, Any]:
    """Publish a Sparkplug B DBIRTH certificate."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
    try:
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/DBIRTH/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
        payload = manager.encode_payload_protobuf(metrics, seq)
        await manager.publish(topic, payload, qos=1)
        return _sparkplug_publish_result(
            manager,
            start,
            topic,
            seq,
            metrics,
            certificate_key=key,
            certificate_value={
                "type": "DBIRTH",
                "device_id": device_id,
                "timestamp": int(time.time() * 1000),
            },
        )
    except Exception as exc:
        return _make_result(False, error=f"DBIRTH failed for {device_id}: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_device_death(device_id: str, ctx: Context = None) -> Dict[str, Any]:
    """Publish a Sparkplug B DDEATH certificate."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
    try:
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/DDEATH/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
        payload = manager.encode_payload_protobuf([], seq)
        await manager.publish(topic, payload, qos=1)
        return _sparkplug_publish_result(
            manager,
            start,
            topic,
            seq,
            [],
            certificate_key=key,
            delete_certificate=True,
        )
    except Exception as exc:
        return _make_result(False, error=f"DDEATH failed for {device_id}: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_node_data(metrics: List[Dict[str, Any]], ctx: Context = None) -> Dict[str, Any]:
    """Publish a Sparkplug B NDATA update."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    if not metrics:
        return _make_result(False, error="At least one metric is required", meta=_topic_meta(manager, start))
    try:
        key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}"
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/NDATA/{SPARKPLUG_EDGE_NODE_ID}"
        payload = manager.encode_payload_protobuf(metrics, seq)
        await manager.publish(topic, payload, qos=0)
        return _sparkplug_publish_result(manager, start, topic, seq, metrics)
    except Exception as exc:
        return _make_result(False, error=f"NDATA failed: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_device_data(
    device_id: str, metrics: List[Dict[str, Any]], ctx: Context = None
) -> Dict[str, Any]:
    """Publish a Sparkplug B DDATA update."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    if not metrics:
        return _make_result(False, error="At least one metric is required", meta=_topic_meta(manager, start))
    try:
        key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/DDATA/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
        payload = manager.encode_payload_protobuf(metrics, seq)
        await manager.publish(topic, payload, qos=0)
        return _sparkplug_publish_result(manager, start, topic, seq, metrics)
    except Exception as exc:
        return _make_result(False, error=f"DDATA failed for {device_id}: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_node_command(metrics: List[Dict[str, Any]], ctx: Context = None) -> Dict[str, Any]:
    """Publish a Sparkplug B NCMD message."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    if not metrics:
        return _make_result(False, error="At least one metric is required", meta=_topic_meta(manager, start))
    try:
        key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}"
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/NCMD/{SPARKPLUG_EDGE_NODE_ID}"
        payload = manager.encode_payload_protobuf(metrics, seq)
        await manager.publish(topic, payload, qos=0)
        return _sparkplug_publish_result(manager, start, topic, seq, metrics)
    except Exception as exc:
        return _make_result(False, error=f"NCMD failed: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
async def publish_device_command(
    device_id: str, metrics: List[Dict[str, Any]], ctx: Context = None
) -> Dict[str, Any]:
    """Publish a Sparkplug B DCMD message."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    if not metrics:
        return _make_result(False, error="At least one metric is required", meta=_topic_meta(manager, start))
    try:
        key = f"{SPARKPLUG_GROUP_ID}/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
        seq = manager.next_sequence(key)
        topic = f"spBv1.0/{SPARKPLUG_GROUP_ID}/DCMD/{SPARKPLUG_EDGE_NODE_ID}/{device_id}"
        payload = manager.encode_payload_protobuf(metrics, seq)
        await manager.publish(topic, payload, qos=0)
        return _sparkplug_publish_result(manager, start, topic, seq, metrics)
    except Exception as exc:
        return _make_result(False, error=f"DCMD failed for {device_id}: {exc}", meta=_topic_meta(manager, start))


@mcp.tool()
def list_sparkplug_nodes(ctx: Context) -> Dict[str, Any]:
    """List published Sparkplug birth certificates tracked by the adapter."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    nodes = [{"key": key, **value} for key, value in sorted(manager.birth_certificates.items())]
    return _make_result(
        True,
        data={"nodes": nodes, "count": len(nodes)},
        meta=_topic_meta(manager, start),
    )


@mcp.tool()
def decode_sparkplug_payload(payload_hex: str, ctx: Context = None) -> Dict[str, Any]:
    """Decode a Sparkplug payload produced by the adapter's protobuf helpers."""
    manager = ctx.request_context.lifespan_context["mqtt_manager"]
    start = time.perf_counter()
    try:
        decoded = decode_sparkplug_payload_bytes(bytes.fromhex(payload_hex))
        return _make_result(True, data=decoded, meta=_topic_meta(manager, start))
    except Exception as exc:
        return _make_result(
            False,
            error=f"Payload decode failed: {exc}",
            meta=_topic_meta(manager, start),
        )


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
