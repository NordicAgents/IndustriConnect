#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import statistics
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[2]
ARXIV_PAPER = ROOT / "arxiv-paper"
GENERATED = ARXIV_PAPER / "generated"
GENERATED.mkdir(exist_ok=True)

# --- Repetition counts ---
NORMAL_REPS = 30
FAULT_REPS = 30
RECOVERY_REPS = 20
STRESS_REPS = 10

FLAGSHIPS = {"Modbus", "MQTT + Sparkplug B", "OPC UA"}
TOOL_FILES = {
    "Modbus": ROOT / "MODBUS-Project/modbus-python/src/modbus_mcp/cli.py",
    "MQTT + Sparkplug B": ROOT / "MQTT-Project/mqtt-python/src/mqtt_mcp/mqtt_server.py",
    "OPC UA": ROOT / "OPCUA-Project/opcua-mcp-server/opcua-mcp-server.py",
    "BACnet/IP": ROOT / "BACnet-Project/bacnet-python/src/bacnet_mcp/tools.py",
    "DNP3": ROOT / "DNP3-Project/dnp3-python/src/dnp3_mcp/tools.py",
    "EtherCAT": ROOT / "EtherCAT-Project/ethercat-python/src/ethercat_mcp/tools.py",
    "EtherNet/IP": ROOT / "EtherNetIP-Project/ethernetip-python/src/ethernetip_mcp/tools.py",
    "PROFIBUS DP/PA": ROOT / "PROFIBUS-Project/profibus-python/src/profibus_mcp/tools.py",
    "PROFINET": ROOT / "PROFINET-Project/profinet-python/src/profinet_mcp/tools.py",
    "Siemens S7comm": ROOT / "S7comm-Project/s7comm-python/src/s7comm_mcp/tools.py",
}
README_FILES = {
    "Modbus": ROOT / "MODBUS-Project/README.md",
    "MQTT + Sparkplug B": ROOT / "MQTT-Project/README.md",
    "OPC UA": ROOT / "OPCUA-Project/README.md",
    "BACnet/IP": ROOT / "BACnet-Project/README.md",
    "DNP3": ROOT / "DNP3-Project/README.md",
    "EtherCAT": ROOT / "EtherCAT-Project/README.md",
    "EtherNet/IP": ROOT / "EtherNetIP-Project/README.md",
    "PROFIBUS DP/PA": ROOT / "PROFIBUS-Project/README.md",
    "PROFINET": ROOT / "PROFINET-Project/README.md",
    "Siemens S7comm": ROOT / "S7comm-Project/README.md",
}


class ManagedProcess:
    def __init__(
        self,
        name: str,
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.env = env or {}
        self.host = host
        self.port = port
        self.proc: Optional[asyncio.subprocess.Process] = None

    async def start(self) -> None:
        if self.proc and self.proc.returncode is None:
            return

        merged_env = os.environ.copy()
        merged_env.update(self.env)
        self.proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            cwd=str(self.cwd),
            env=merged_env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if self.host and self.port:
            await wait_for_port(self.host, self.port)

    async def stop(self) -> None:
        if not self.proc or self.proc.returncode is not None:
            self.proc = None
            return

        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.proc.kill()
            await asyncio.wait_for(self.proc.wait(), timeout=5)

        if self.host and self.port:
            await wait_for_port_closed(self.host, self.port)
        self.proc = None

    async def restart(self) -> None:
        await self.stop()
        await self.start()


async def wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except Exception as exc:  # pragma: no cover - best effort probe
            last_error = exc
            await asyncio.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for {host}:{port}: {last_error}")


async def wait_for_port_closed(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(0.1)
        except Exception:
            return
    raise TimeoutError(f"Timed out waiting for {host}:{port} to close")


@asynccontextmanager
async def mcp_session(command: str, args: List[str], cwd: Path, env: Dict[str, str]):
    server = StdioServerParameters(command=command, args=args, cwd=cwd, env=env)
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        async with stdio_client(server, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


def parse_mcp_response(raw: Any, wall_clock_ms: float) -> Dict[str, Any]:
    text_parts = [getattr(item, "text", "") for item in getattr(raw, "content", [])]
    text = "\n".join(part for part in text_parts if part)

    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {
            "success": False,
            "data": None,
            "error": text or "Non-JSON MCP response",
            "meta": {},
        }

    parsed.setdefault("meta", {})
    parsed["meta"]["wall_clock_ms"] = round(wall_clock_ms, 3)
    return parsed


async def call_tool_json(session: ClientSession, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        raw = await session.call_tool(tool, arguments)
    except Exception as exc:
        return {
            "success": False,
            "data": None,
            "error": str(exc),
            "meta": {"wall_clock_ms": round((time.perf_counter() - start) * 1000.0, 3)},
        }
    return parse_mcp_response(raw, (time.perf_counter() - start) * 1000.0)


def call_correct(result: Dict[str, Any], expect_success: bool, matcher: Optional[Callable[[Dict[str, Any]], bool]] = None) -> bool:
    if bool(result.get("success")) != expect_success:
        return False
    if matcher is None:
        return True
    return bool(matcher(result))


def extract_retry_count(result: Dict[str, Any]) -> int:
    meta = result.get("meta") or {}
    if "attempts" in meta:
        return max(int(meta["attempts"]) - 1, 0)
    if "chunks" in meta:
        retries = 0
        for chunk in meta["chunks"]:
            retries += max(int(chunk.get("attempts", 1)) - 1, 0)
        return retries
    return 0


def classify_error(result: Dict[str, Any]) -> Optional[str]:
    error = (result.get("error") or "").lower()
    if not error:
        return None
    if "disabled" in error:
        return "guarded_write"
    if "not connected" in error or "client is not connected" in error:
        return "endpoint_unavailable"
    if "timeout" in error:
        return "timeout"
    if "out of uint16 range" in error:
        return "range_overflow"
    if "illegal" in error or "invalid address" in error or "address" in error and "9999" in error:
        return "illegal_address"
    if "type" in error and ("mismatch" in error or "float" in error or "not_a_number" in error):
        return "type_mismatch"
    if "invalid" in error or "empty" in error or "qos" in error:
        return "invalid_input"
    if "bad" in error or "exception" in error:
        return "protocol_error"
    if "read failed" in error or "write failed" in error:
        return "protocol_error"
    return "other"


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = (len(ordered) - 1) * (pct / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    value = ordered[lower] * (1.0 - weight) + ordered[upper] * weight
    return round(value, 3)


def confidence_interval_95(values: List[float]) -> Tuple[float, float]:
    """Compute 95% CI using t-distribution."""
    n = len(values)
    if n < 2:
        mean = values[0] if values else 0.0
        return (mean, mean)
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    # t-value for 95% CI, two-tailed, approximate for common df
    # Use scipy if available, otherwise approximate
    try:
        from scipy.stats import t as t_dist
        t_val = t_dist.ppf(0.975, n - 1)
    except ImportError:
        # Approximation for df >= 2
        if n >= 120:
            t_val = 1.96
        elif n >= 30:
            t_val = 2.042
        elif n >= 20:
            t_val = 2.093
        else:
            t_val = 2.262  # df=9
    margin = t_val * std / math.sqrt(n)
    return (round(mean - margin, 3), round(mean + margin, 3))


async def discover_opcua_nodes(opcua: ClientSession) -> Dict[str, str]:
    variables = await call_tool_json(opcua, "get_all_variables", {})
    if not variables.get("success"):
        raise RuntimeError(f"Failed to discover OPC UA variables: {variables.get('error')}")
    mapping = {
        entry["name"]: entry["node_id"]
        for entry in variables["data"]["variables"]
        if "name" in entry and "node_id" in entry
    }
    mapping["IndustrialControlSystem"] = "ns=2;i=1"
    mapping["SensorsFolder"] = "ns=2;i=2"
    mapping["ActuatorsFolder"] = "ns=2;i=11"
    mapping["SystemStatusFolder"] = "ns=2;i=18"
    return mapping


def finalize_task(
    task_id: str,
    family: str,
    description: str,
    repetition: int,
    calls: List[Dict[str, Any]],
    checks: List[bool],
    started_at: float,
    task_type: str = "normal",
) -> Dict[str, Any]:
    matched = [bool(check) for check in checks]
    failures = [classify_error(call) for ok, call in zip(matched, calls) if not ok]
    return {
        "task_id": task_id,
        "family": family,
        "description": description,
        "repetition": repetition,
        "task_type": task_type,
        "task_success": all(matched),
        "tool_calls": len(calls),
        "tool_call_successes": sum(1 for ok in matched if ok),
        "task_latency_ms": round((time.perf_counter() - started_at) * 1000.0, 3),
        "retry_count": sum(extract_retry_count(call) for call in calls),
        "failure_classes": [failure for failure in failures if failure],
        "error_classes": [classify_error(call) for call in calls if classify_error(call)],
        "calls": calls,
    }


async def run_normal_tasks(
    modbus_rw: ClientSession,
    modbus_ro: ClientSession,
    mqtt: ClientSession,
    opcua: ClientSession,
    opcua_nodes: Dict[str, str],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for repetition in range(1, NORMAL_REPS + 1):
        # Modbus
        started = time.perf_counter()
        call = await call_tool_json(modbus_rw, "ping", {})
        results.append(
            finalize_task(
                "M1",
                "Modbus",
                "Ping the adapter and confirm the TCP mock is reachable.",
                repetition,
                [call],
                [call_correct(call, True, lambda item: item["data"]["connected"] is True)],
                started,
            )
        )

        started = time.perf_counter()
        call = await call_tool_json(modbus_rw, "read_input_registers", {"address": 0, "count": 4})
        results.append(
            finalize_task(
                "M2",
                "Modbus",
                "Read a four-register sensor block from the Modbus mock.",
                repetition,
                [call],
                [call_correct(call, True, lambda item: len(item["data"]["registers"]) == 4)],
                started,
            )
        )

        write_value = 40 + repetition
        started = time.perf_counter()
        write_call = await call_tool_json(
            modbus_rw,
            "write_register",
            {"address": 1, "value": write_value},
        )
        read_call = await call_tool_json(modbus_rw, "read_register", {"address": 1})
        results.append(
            finalize_task(
                "M3",
                "Modbus",
                "Write a holding register and read it back for verification.",
                repetition,
                [write_call, read_call],
                [
                    call_correct(write_call, True, lambda item: item["data"]["written"] == write_value),
                    call_correct(read_call, True, lambda item: item["data"]["value"] == write_value),
                ],
                started,
            )
        )

        started = time.perf_counter()
        guard_call = await call_tool_json(
            modbus_ro,
            "write_register",
            {"address": 1, "value": 999},
        )
        results.append(
            finalize_task(
                "M4",
                "Modbus",
                "Attempt a write with writes disabled and expect a guarded rejection.",
                repetition,
                [guard_call],
                [call_correct(guard_call, False, lambda item: "disabled" in (item["error"] or "").lower())],
                started,
            )
        )

        # MQTT
        started = time.perf_counter()
        broker_call = await call_tool_json(mqtt, "get_broker_info", {})
        results.append(
            finalize_task(
                "Q1",
                "MQTT",
                "Inspect broker connectivity through the MCP adapter.",
                repetition,
                [broker_call],
                [call_correct(broker_call, True, lambda item: item["data"]["connected"] is True)],
                started,
            )
        )

        started = time.perf_counter()
        subscribe_call = await call_tool_json(
            mqtt,
            "subscribe_topic",
            {"topic": "sensors/#", "qos": 0},
        )
        results.append(
            finalize_task(
                "Q2",
                "MQTT",
                "Subscribe to the mock sensor topic namespace.",
                repetition,
                [subscribe_call],
                [call_correct(subscribe_call, True, lambda item: item["data"]["subscription_count"] >= 1)],
                started,
            )
        )

        started = time.perf_counter()
        publish_call = await call_tool_json(
            mqtt,
            "publish_message",
            {
                "topic": "control/pump",
                "payload": json.dumps({"pump_speed": 50 + repetition}),
                "qos": 0,
                "retain": False,
            },
        )
        results.append(
            finalize_task(
                "Q3",
                "MQTT",
                "Publish a standard MQTT control payload.",
                repetition,
                [publish_call],
                [call_correct(publish_call, True, lambda item: item["data"]["topic"] == "control/pump")],
                started,
            )
        )

        started = time.perf_counter()
        sparkplug_call = await call_tool_json(
            mqtt,
            "publish_device_data",
            {
                "device_id": "device-1",
                "metrics": [{"name": "temperature", "value": 20.0 + repetition, "type": "float"}],
            },
        )
        results.append(
            finalize_task(
                "Q4",
                "MQTT",
                "Publish a Sparkplug B DDATA update for the mock device.",
                repetition,
                [sparkplug_call],
                [call_correct(sparkplug_call, True, lambda item: item["data"]["metric_count"] == 1)],
                started,
            )
        )

        # OPC UA
        started = time.perf_counter()
        read_temp = await call_tool_json(opcua, "read_opcua_node", {"node_id": opcua_nodes["Temperature"]})
        results.append(
            finalize_task(
                "O1",
                "OPC UA",
                "Read the temperature sensor variable from the OPC UA mock plant.",
                repetition,
                [read_temp],
                [call_correct(read_temp, True, lambda item: isinstance(item["data"]["value"], (int, float)))],
                started,
            )
        )

        started = time.perf_counter()
        browse_call = await call_tool_json(
            opcua,
            "browse_opcua_node_children",
            {"node_id": opcua_nodes["ActuatorsFolder"]},
        )
        results.append(
            finalize_task(
                "O2",
                "OPC UA",
                "Browse the actuator subtree in the mock plant.",
                repetition,
                [browse_call],
                [call_correct(browse_call, True, lambda item: len(item["data"]["children"]) >= 6)],
                started,
            )
        )

        opcua_write_value = 25.0 + repetition
        started = time.perf_counter()
        write_node = await call_tool_json(
            opcua,
            "write_opcua_node",
            {"node_id": opcua_nodes["ValvePosition"], "value": opcua_write_value},
        )
        read_node = await call_tool_json(
            opcua,
            "read_opcua_node",
            {"node_id": opcua_nodes["ValvePosition"]},
        )
        results.append(
            finalize_task(
                "O3",
                "OPC UA",
                "Write the valve-position variable and confirm the new value.",
                repetition,
                [write_node, read_node],
                [
                    call_correct(write_node, True, lambda item: float(item["data"]["written_value"]) == float(opcua_write_value)),
                    call_correct(read_node, True, lambda item: float(item["data"]["value"]) == float(opcua_write_value)),
                ],
                started,
            )
        )

        started = time.perf_counter()
        discover_call = await call_tool_json(opcua, "get_all_variables", {})
        results.append(
            finalize_task(
                "O4",
                "OPC UA",
                "Enumerate the mock plant variables through the adapter.",
                repetition,
                [discover_call],
                [call_correct(discover_call, True, lambda item: item["data"]["count"] >= 20)],
                started,
            )
        )

        # Cross-protocol tasks (sequential)
        started = time.perf_counter()
        cross_calls = [
            await call_tool_json(modbus_rw, "read_input_registers", {"address": 0, "count": 4}),
            await call_tool_json(
                opcua,
                "read_multiple_opcua_nodes",
                {"node_ids": [opcua_nodes["Temperature"], opcua_nodes["Pressure"]]},
            ),
            await call_tool_json(mqtt, "get_broker_info", {}),
        ]
        results.append(
            finalize_task(
                "X1",
                "Cross-protocol",
                "Collect a multi-adapter state snapshot across Modbus, OPC UA, and MQTT.",
                repetition,
                cross_calls,
                [
                    call_correct(cross_calls[0], True, lambda item: len(item["data"]["registers"]) == 4),
                    call_correct(cross_calls[1], True, lambda item: len(item["data"]["results"]) == 2),
                    call_correct(cross_calls[2], True, lambda item: item["data"]["connected"] is True),
                ],
                started,
            )
        )

        started = time.perf_counter()
        control_calls = [
            await call_tool_json(modbus_rw, "write_register", {"address": 3, "value": 60}),
            await call_tool_json(opcua, "write_opcua_node", {"node_id": opcua_nodes["PumpEnabled"], "value": True}),
            await call_tool_json(
                mqtt,
                "publish_message",
                {
                    "topic": "control/line",
                    "payload": json.dumps({"mode": "auto", "rep": repetition}),
                    "qos": 0,
                    "retain": False,
                },
            ),
        ]
        results.append(
            finalize_task(
                "X2",
                "Cross-protocol",
                "Execute a coordinated multi-adapter control sequence.",
                repetition,
                control_calls,
                [
                    call_correct(control_calls[0], True, lambda item: item["data"]["written"] == 60),
                    call_correct(control_calls[1], True, lambda item: item["data"]["written_value"] is True),
                    call_correct(control_calls[2], True, lambda item: item["data"]["topic"] == "control/line"),
                ],
                started,
            )
        )

        # X1p/X2p: Parallel cross-protocol variants (2F)
        started = time.perf_counter()
        parallel_reads = await asyncio.gather(
            call_tool_json(modbus_rw, "read_input_registers", {"address": 0, "count": 4}),
            call_tool_json(opcua, "read_multiple_opcua_nodes", {"node_ids": [opcua_nodes["Temperature"], opcua_nodes["Pressure"]]}),
            call_tool_json(mqtt, "get_broker_info", {}),
        )
        results.append(
            finalize_task(
                "X1p",
                "Cross-protocol",
                "Parallel multi-adapter state snapshot across Modbus, OPC UA, and MQTT.",
                repetition,
                list(parallel_reads),
                [
                    call_correct(parallel_reads[0], True, lambda item: len(item["data"]["registers"]) == 4),
                    call_correct(parallel_reads[1], True, lambda item: len(item["data"]["results"]) == 2),
                    call_correct(parallel_reads[2], True, lambda item: item["data"]["connected"] is True),
                ],
                started,
            )
        )

        started = time.perf_counter()
        parallel_writes = await asyncio.gather(
            call_tool_json(modbus_rw, "write_register", {"address": 3, "value": 60}),
            call_tool_json(opcua, "write_opcua_node", {"node_id": opcua_nodes["PumpEnabled"], "value": True}),
            call_tool_json(mqtt, "publish_message", {"topic": "control/line", "payload": json.dumps({"mode": "auto", "rep": repetition}), "qos": 0, "retain": False}),
        )
        results.append(
            finalize_task(
                "X2p",
                "Cross-protocol",
                "Parallel coordinated multi-adapter control sequence.",
                repetition,
                list(parallel_writes),
                [
                    call_correct(parallel_writes[0], True, lambda item: item["data"]["written"] == 60),
                    call_correct(parallel_writes[1], True, lambda item: item["data"]["written_value"] is True),
                    call_correct(parallel_writes[2], True, lambda item: item["data"]["topic"] == "control/line"),
                ],
                started,
            )
        )

    return results


async def run_fault_injection_tasks(
    modbus_rw: ClientSession,
    mqtt: ClientSession,
    opcua: ClientSession,
    opcua_nodes: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Run fault-injected tasks that exercise error handling paths."""
    results: List[Dict[str, Any]] = []
    for repetition in range(1, FAULT_REPS + 1):
        # FM1: Modbus — read invalid register address (9999)
        started = time.perf_counter()
        call = await call_tool_json(modbus_rw, "read_register", {"address": 9999})
        results.append(
            finalize_task(
                "FM1",
                "Modbus",
                "Read invalid register address (9999) and expect a structured protocol error.",
                repetition,
                [call],
                [call_correct(call, False)],
                started,
                task_type="fault",
            )
        )

        # FM2: Modbus — write overflow value (70000 > uint16 max)
        # Adapter MUST reject with success=false (falsifiable check)
        started = time.perf_counter()
        call = await call_tool_json(modbus_rw, "write_register", {"address": 1, "value": 70000})
        results.append(
            finalize_task(
                "FM2",
                "Modbus",
                "Write overflow value (70000 > uint16 max) and expect adapter rejection.",
                repetition,
                [call],
                [call_correct(call, False)],
                started,
                task_type="fault",
            )
        )

        # FQ1: MQTT — publish to empty topic ""
        started = time.perf_counter()
        call = await call_tool_json(
            mqtt,
            "publish_message",
            {"topic": "", "payload": "{\"test\": true}", "qos": 0, "retain": False},
        )
        results.append(
            finalize_task(
                "FQ1",
                "MQTT",
                "Publish to empty topic string and expect a structured invalid-input error.",
                repetition,
                [call],
                [call_correct(call, False)],
                started,
                task_type="fault",
            )
        )

        # FQ2: MQTT — subscribe with invalid QoS (5)
        started = time.perf_counter()
        call = await call_tool_json(
            mqtt,
            "subscribe_topic",
            {"topic": "sensors/#", "qos": 5},
        )
        results.append(
            finalize_task(
                "FQ2",
                "MQTT",
                "Subscribe with invalid QoS (5) and expect a structured invalid-input error.",
                repetition,
                [call],
                [call_correct(call, False)],
                started,
                task_type="fault",
            )
        )

        # FO1: OPC UA — read non-existent node ns=2;i=99999
        started = time.perf_counter()
        call = await call_tool_json(opcua, "read_opcua_node", {"node_id": "ns=2;i=99999"})
        results.append(
            finalize_task(
                "FO1",
                "OPC UA",
                "Read non-existent node (ns=2;i=99999) and expect a structured read-failed error.",
                repetition,
                [call],
                [call_correct(call, False)],
                started,
                task_type="fault",
            )
        )

        # FO2: OPC UA — write wrong type ("not_a_number" to float node)
        started = time.perf_counter()
        call = await call_tool_json(
            opcua,
            "write_opcua_node",
            {"node_id": opcua_nodes["ValvePosition"], "value": "not_a_number"},
        )
        results.append(
            finalize_task(
                "FO2",
                "OPC UA",
                "Write wrong type (string to float node) and expect a structured write-failed error.",
                repetition,
                [call],
                [call_correct(call, False)],
                started,
                task_type="fault",
            )
        )

        # FX1: Cross-protocol — 3-step sequence with one deliberate bad input
        started = time.perf_counter()
        step1 = await call_tool_json(modbus_rw, "read_input_registers", {"address": 0, "count": 4})
        step2 = await call_tool_json(opcua, "read_opcua_node", {"node_id": "ns=2;i=99999"})
        step3 = await call_tool_json(
            mqtt,
            "publish_message",
            {
                "topic": "control/pump",
                "payload": json.dumps({"pump_speed": 50}),
                "qos": 0,
                "retain": False,
            },
        )
        results.append(
            finalize_task(
                "FX1",
                "Cross-protocol",
                "3-step cross-protocol sequence with one deliberate bad OPC UA read; expect 2/3 succeed.",
                repetition,
                [step1, step2, step3],
                [
                    call_correct(step1, True, lambda item: len(item["data"]["registers"]) == 4),
                    call_correct(step2, False),
                    call_correct(step3, True, lambda item: item["data"]["topic"] == "control/pump"),
                ],
                started,
                task_type="fault",
            )
        )

    return results


async def run_stress_tasks(
    modbus_rw: ClientSession,
    mqtt: ClientSession,
    opcua: ClientSession,
    opcua_nodes: Dict[str, str],
    modbus_mock: ManagedProcess,
    broker: ManagedProcess,
    opcua_server: ManagedProcess,
) -> List[Dict[str, Any]]:
    """Run stress tests: concurrency, rapid fire, and mid-operation restart."""
    results: List[Dict[str, Any]] = []

    for repetition in range(1, STRESS_REPS + 1):
        # S1-S3: Concurrent reads (4 parallel per adapter)
        for task_id, family, coro_factory in [
            ("S1", "Modbus", lambda: [call_tool_json(modbus_rw, "read_register", {"address": i}) for i in range(4)]),
            ("S2", "MQTT", lambda: [call_tool_json(mqtt, "get_broker_info", {}) for _ in range(4)]),
            ("S3", "OPC UA", lambda: [call_tool_json(opcua, "read_opcua_node", {"node_id": opcua_nodes["Temperature"]}) for _ in range(4)]),
        ]:
            started = time.perf_counter()
            calls = await asyncio.gather(*coro_factory())
            call_list = list(calls)
            checks = [call_correct(c, True) for c in call_list]
            results.append(
                finalize_task(task_id, family, f"4 concurrent reads via {family} adapter.", repetition, call_list, checks, started, task_type="stress")
            )

        # S4-S6: Concurrent read + write (per adapter)
        started = time.perf_counter()
        s4_calls = await asyncio.gather(
            call_tool_json(modbus_rw, "read_register", {"address": 0}),
            call_tool_json(modbus_rw, "write_register", {"address": 2, "value": 100 + repetition}),
        )
        results.append(
            finalize_task("S4", "Modbus", "Concurrent read + write via Modbus.", repetition, list(s4_calls), [call_correct(c, True) for c in s4_calls], started, task_type="stress")
        )

        started = time.perf_counter()
        s5_calls = await asyncio.gather(
            call_tool_json(mqtt, "get_broker_info", {}),
            call_tool_json(mqtt, "publish_message", {"topic": "stress/test", "payload": "{}", "qos": 0, "retain": False}),
        )
        results.append(
            finalize_task("S5", "MQTT", "Concurrent read + publish via MQTT.", repetition, list(s5_calls), [call_correct(c, True) for c in s5_calls], started, task_type="stress")
        )

        started = time.perf_counter()
        s6_calls = await asyncio.gather(
            call_tool_json(opcua, "read_opcua_node", {"node_id": opcua_nodes["Temperature"]}),
            call_tool_json(opcua, "write_opcua_node", {"node_id": opcua_nodes["ValvePosition"], "value": 30.0 + repetition}),
        )
        results.append(
            finalize_task("S6", "OPC UA", "Concurrent read + write via OPC UA.", repetition, list(s6_calls), [call_correct(c, True) for c in s6_calls], started, task_type="stress")
        )

        # S7-S9: Rapid fire — 50 sequential calls in tight loop
        for task_id, family, call_factory in [
            ("S7", "Modbus", lambda: call_tool_json(modbus_rw, "read_register", {"address": 0})),
            ("S8", "MQTT", lambda: call_tool_json(mqtt, "get_broker_info", {})),
            ("S9", "OPC UA", lambda: call_tool_json(opcua, "read_opcua_node", {"node_id": opcua_nodes["Temperature"]})),
        ]:
            started = time.perf_counter()
            rapid_calls = []
            for _ in range(50):
                rapid_calls.append(await call_factory())
            checks = [call_correct(c, True) for c in rapid_calls]
            results.append(
                finalize_task(task_id, family, f"50 sequential rapid-fire reads via {family}.", repetition, rapid_calls, checks, started, task_type="stress")
            )

        # S10-S12: Mid-operation mock restart during concurrent operations
        for task_id, family, mock_proc, read_coro in [
            ("S10", "Modbus", modbus_mock, lambda: call_tool_json(modbus_rw, "read_register", {"address": 0})),
            ("S11", "MQTT", broker, lambda: call_tool_json(mqtt, "get_broker_info", {})),
            ("S12", "OPC UA", opcua_server, lambda: call_tool_json(opcua, "read_opcua_node", {"node_id": opcua_nodes["Temperature"]})),
        ]:
            started = time.perf_counter()
            # Fire off reads while restarting the mock
            pre_call = await read_coro()
            await mock_proc.stop()
            during_call = await read_coro()
            await mock_proc.start()
            await asyncio.sleep(1.0)
            post_call = await read_coro()
            all_calls = [pre_call, during_call, post_call]
            # pre should succeed, during should fail, post should succeed
            checks = [
                call_correct(pre_call, True),
                call_correct(during_call, False),
                call_correct(post_call, True),
            ]
            results.append(
                finalize_task(task_id, family, f"Mid-operation mock restart during {family} reads.", repetition, all_calls, checks, started, task_type="stress")
            )

    return results


def aggregate_fault_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute per-task fault-injection summaries."""
    by_task: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        by_task.setdefault(result["task_id"], []).append(result)

    task_summary = {}
    for task_id, rows in by_task.items():
        latencies = [row["task_latency_ms"] for row in rows]
        error_classes: Dict[str, int] = {}
        for row in rows:
            for ec in row.get("error_classes", []):
                error_classes[ec] = error_classes.get(ec, 0) + 1
        mean_lat = round(statistics.mean(latencies), 3)
        std_lat = round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0.0
        ci_low, ci_high = confidence_interval_95(latencies)
        task_summary[task_id] = {
            "family": rows[0]["family"],
            "description": rows[0]["description"],
            "error_handling_rate": round(
                sum(1 for row in rows if row["task_success"]) / len(rows), 3
            ),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": percentile(latencies, 95),
            "mean_latency_ms": mean_lat,
            "std_latency_ms": std_lat,
            "ci95_latency_ms": [ci_low, ci_high],
            "error_class_distribution": error_classes,
        }

    overall_error_handling_rate = round(
        sum(1 for r in results if r["task_success"]) / len(results), 3
    ) if results else 0.0

    return {
        "by_task": task_summary,
        "overall_error_handling_rate": overall_error_handling_rate,
        "total_runs": len(results),
        "total_tool_calls": sum(r["tool_calls"] for r in results),
    }


async def recovery_trial(
    family: str,
    description: str,
    stop_process: ManagedProcess,
    restart_process: ManagedProcess,
    failure_call: Callable[[], Any],
    same_session_call: Callable[[], Any],
    fresh_session_call: Callable[[], Any],
) -> Dict[str, Any]:
    """Run a single recovery trial with dual-mode reporting."""
    started = time.perf_counter()

    await stop_process.stop()
    await asyncio.sleep(0.5)
    failure_result = await failure_call()

    await restart_process.start()
    await asyncio.sleep(3.0)  # increased from 1s for reconnection time

    # Attempt same-session recovery first
    same_session_result = await same_session_call()
    same_session_ok = bool(same_session_result.get("success"))

    # Then fresh-session as fallback
    fresh_session_result = await fresh_session_call()
    fresh_session_ok = bool(fresh_session_result.get("success"))

    failure_observed = not bool(failure_result.get("success"))

    return {
        "family": family,
        "description": description,
        "recovery_success": failure_observed and (same_session_ok or fresh_session_ok),
        "same_session_recovery": same_session_ok,
        "fresh_session_recovery": fresh_session_ok,
        "recovery_mode": "same_session" if same_session_ok else ("fresh_session" if fresh_session_ok else "failed"),
        "outage_detected": failure_observed,
        "post_restart_success": same_session_ok or fresh_session_ok,
        "trial_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "failure_result": failure_result,
        "same_session_result": same_session_result,
        "fresh_session_result": fresh_session_result,
        "success_result": same_session_result if same_session_ok else fresh_session_result,
    }


async def run_recovery_tasks(
    modbus_mock: ManagedProcess,
    broker: ManagedProcess,
    opcua_server: ManagedProcess,
) -> Dict[str, List[Dict[str, Any]]]:
    results = {"Modbus": [], "MQTT": [], "OPC UA": []}

    for _ in range(RECOVERY_REPS):
        async with mcp_session(
            "uv",
            ["run", "modbus-mcp"],
            ROOT / "MODBUS-Project/modbus-python",
            {
                "MODBUS_TYPE": "tcp",
                "MODBUS_HOST": "127.0.0.1",
                "MODBUS_PORT": "1502",
                "MODBUS_DEFAULT_SLAVE_ID": "1",
            },
        ) as session:
            await call_tool_json(session, "ping", {})
            trial = await recovery_trial(
                "Modbus",
                "Stop the Modbus mock, confirm a failed read, restart, and attempt same-session then fresh-session recovery.",
                modbus_mock,
                modbus_mock,
                failure_call=lambda: call_tool_json(session, "read_register", {"address": 1}),
                same_session_call=lambda: call_tool_json(session, "read_register", {"address": 1}),
                fresh_session_call=lambda: _recovery_success_call(
                    "uv",
                    ["run", "modbus-mcp"],
                    ROOT / "MODBUS-Project/modbus-python",
                    {
                        "MODBUS_TYPE": "tcp",
                        "MODBUS_HOST": "127.0.0.1",
                        "MODBUS_PORT": "1502",
                        "MODBUS_DEFAULT_SLAVE_ID": "1",
                    },
                    "read_register",
                    {"address": 1},
                ),
            )
            results["Modbus"].append(trial)

    for _ in range(RECOVERY_REPS):
        async with mcp_session(
            "uv",
            ["run", "mqtt-mcp"],
            ROOT / "MQTT-Project/mqtt-python",
            {
                "MQTT_BROKER_URL": "mqtt://127.0.0.1:1883",
                "MQTT_CLIENT_ID": "mqtt-mcp-recovery",
                "SPARKPLUG_GROUP_ID": "factory",
                "SPARKPLUG_EDGE_NODE_ID": "edge-node-1",
            },
        ) as session:
            await call_tool_json(session, "get_broker_info", {})
            trial = await recovery_trial(
                "MQTT",
                "Stop the MQTT broker, confirm a failed publish, restart, and attempt same-session then fresh-session recovery.",
                broker,
                broker,
                failure_call=lambda: call_tool_json(
                    session,
                    "publish_message",
                    {"topic": "control/pump", "payload": "{\"pump_speed\": 0}", "qos": 0, "retain": False},
                ),
                same_session_call=lambda: call_tool_json(
                    session,
                    "publish_message",
                    {"topic": "control/pump", "payload": "{\"pump_speed\": 1}", "qos": 0, "retain": False},
                ),
                fresh_session_call=lambda: _recovery_success_call(
                    "uv",
                    ["run", "mqtt-mcp"],
                    ROOT / "MQTT-Project/mqtt-python",
                    {
                        "MQTT_BROKER_URL": "mqtt://127.0.0.1:1883",
                        "MQTT_CLIENT_ID": "mqtt-mcp-recovery-after",
                        "SPARKPLUG_GROUP_ID": "factory",
                        "SPARKPLUG_EDGE_NODE_ID": "edge-node-1",
                    },
                    "publish_message",
                    {"topic": "control/pump", "payload": "{\"pump_speed\": 1}", "qos": 0, "retain": False},
                ),
            )
            results["MQTT"].append(trial)

    for _ in range(RECOVERY_REPS):
        async with mcp_session(
            "uv",
            ["run", "opcua-mcp-server.py"],
            ROOT / "OPCUA-Project/opcua-mcp-server",
            {"OPCUA_SERVER_URL": "opc.tcp://127.0.0.1:4840/freeopcua/server/"},
        ) as session:
            await call_tool_json(session, "read_opcua_node", {"node_id": "ns=2;i=3"})
            trial = await recovery_trial(
                "OPC UA",
                "Stop the OPC UA mock, confirm a failed read, restart, and attempt same-session then fresh-session recovery.",
                opcua_server,
                opcua_server,
                failure_call=lambda: call_tool_json(session, "read_opcua_node", {"node_id": "ns=2;i=3"}),
                same_session_call=lambda: call_tool_json(session, "read_opcua_node", {"node_id": "ns=2;i=3"}),
                fresh_session_call=lambda: _recovery_success_call(
                    "uv",
                    ["run", "opcua-mcp-server.py"],
                    ROOT / "OPCUA-Project/opcua-mcp-server",
                    {"OPCUA_SERVER_URL": "opc.tcp://127.0.0.1:4840/freeopcua/server/"},
                    "read_opcua_node",
                    {"node_id": "ns=2;i=3"},
                ),
            )
            results["OPC UA"].append(trial)

    return results


async def _recovery_success_call(
    command: str,
    args: List[str],
    cwd: Path,
    env: Dict[str, str],
    tool: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    async with mcp_session(command, args, cwd, env) as session:
        return await call_tool_json(session, tool, arguments)


def aggregate_normal_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    by_task: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        by_family.setdefault(result["family"], []).append(result)
        by_task.setdefault(result["task_id"], []).append(result)

    family_summary = {}
    for family, rows in by_family.items():
        latencies = [row["task_latency_ms"] for row in rows]
        total_calls = sum(row["tool_calls"] for row in rows)
        mean_lat = round(statistics.mean(latencies), 3)
        std_lat = round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0.0
        ci_low, ci_high = confidence_interval_95(latencies)
        family_summary[family] = {
            "tasks": len({row["task_id"] for row in rows}),
            "task_success_rate": round(sum(1 for row in rows if row["task_success"]) / len(rows), 3),
            "tool_call_success_rate": round(sum(row["tool_call_successes"] for row in rows) / total_calls, 3),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": percentile(latencies, 95),
            "mean_latency_ms": mean_lat,
            "std_latency_ms": std_lat,
            "ci95_latency_ms": [ci_low, ci_high],
            "total_retries": sum(row["retry_count"] for row in rows),
        }

    task_summary = {}
    for task_id, rows in by_task.items():
        latencies = [row["task_latency_ms"] for row in rows]
        description = rows[0]["description"]
        family = rows[0]["family"]
        mean_lat = round(statistics.mean(latencies), 3)
        std_lat = round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0.0
        ci_low, ci_high = confidence_interval_95(latencies)
        task_summary[task_id] = {
            "family": family,
            "description": description,
            "task_success_rate": round(sum(1 for row in rows if row["task_success"]) / len(rows), 3),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": percentile(latencies, 95),
            "mean_latency_ms": mean_lat,
            "std_latency_ms": std_lat,
            "ci95_latency_ms": [ci_low, ci_high],
        }

    return {"by_family": family_summary, "by_task": task_summary}


def aggregate_stress_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute per-task stress-suite summaries."""
    by_task: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        by_task.setdefault(result["task_id"], []).append(result)

    task_summary = {}
    for task_id, rows in by_task.items():
        latencies = [row["task_latency_ms"] for row in rows]
        success_count = sum(1 for row in rows if row["task_success"])
        failure_count = len(rows) - success_count
        mean_lat = round(statistics.mean(latencies), 3)
        std_lat = round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0.0
        ci_low, ci_high = confidence_interval_95(latencies)
        task_summary[task_id] = {
            "family": rows[0]["family"],
            "description": rows[0]["description"],
            "success_rate": round(success_count / len(rows), 3),
            "failure_count": failure_count,
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": percentile(latencies, 95),
            "mean_latency_ms": mean_lat,
            "std_latency_ms": std_lat,
            "ci95_latency_ms": [ci_low, ci_high],
        }

    overall_success = sum(1 for r in results if r["task_success"])
    return {
        "by_task": task_summary,
        "overall_success_rate": round(overall_success / len(results), 3) if results else 0.0,
        "total_runs": len(results),
        "total_tool_calls": sum(r["tool_calls"] for r in results),
    }


def aggregate_recovery_results(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    summary = {}
    for family, rows in results.items():
        same_session_count = sum(1 for row in rows if row.get("same_session_recovery"))
        fresh_session_count = sum(1 for row in rows if row.get("fresh_session_recovery"))
        summary[family] = {
            "recovery_success_rate": round(
                sum(1 for row in rows if row["recovery_success"]) / len(rows),
                3,
            ),
            "same_session_recovery_rate": round(same_session_count / len(rows), 3),
            "fresh_session_recovery_rate": round(fresh_session_count / len(rows), 3),
            "outage_detection_rate": round(
                sum(1 for row in rows if row["outage_detected"]) / len(rows),
                3,
            ),
            "median_trial_latency_ms": round(
                statistics.median([row["trial_latency_ms"] for row in rows]),
                3,
            ),
        }
    return summary


def build_protocol_inventory() -> List[Dict[str, Any]]:
    inventory = []
    pattern = re.compile(r"@(?:mcp|server)\.tool\(")
    for protocol, tool_file in TOOL_FILES.items():
        content = tool_file.read_text(encoding="utf-8")
        readme = README_FILES[protocol].read_text(encoding="utf-8").lower()
        if protocol in FLAGSHIPS:
            maturity = "evaluated flagship"
        elif "scaffold" in readme or "roadmap" in readme or "placeholder" in readme:
            maturity = "roadmap/scaffold"
        else:
            maturity = "implemented prototype"
        inventory.append(
            {
                "protocol": protocol,
                "tool_count": len(pattern.findall(content)),
                "maturity": maturity,
            }
        )
    return inventory


def write_recovery_figure(summary: Dict[str, Any]) -> Path:
    output_path = GENERATED / "flagship_recovery.png"
    labels = ["Modbus", "MQTT", "OPC UA"]

    same_session = [summary[label].get("same_session_recovery_rate", 0.0) * 100.0 for label in labels]
    fresh_session = [summary[label].get("fresh_session_recovery_rate", 0.0) * 100.0 for label in labels]

    fig, ax = plt.subplots(figsize=(6.0, 3.2), constrained_layout=True)
    x = range(len(labels))
    width = 0.32
    colors_same = ["#0F766E", "#1D4ED8", "#B45309"]
    colors_fresh = ["#5EEAD4", "#93C5FD", "#FCD34D"]

    bars_same = ax.bar([i - width / 2 for i in x], same_session, width, color=colors_same, label="Same session")
    bars_fresh = ax.bar([i + width / 2 for i in x], fresh_session, width, color=colors_fresh, label="Fresh session")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Recovery success (%)")
    ax.set_title(f"Post-restart recovery over {RECOVERY_REPS} trials (same-session vs fresh-session)")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8)

    for bars in [bars_same, bars_fresh]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 1.5,
                    f"{height:.0f}%",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def write_latency_boxplot(normal_results: List[Dict[str, Any]]) -> Path:
    """Generate per-task latency distribution box plot (Phase 6B)."""
    output_path = GENERATED.parent / "figures" / "fig7_latency_boxplot.png"
    output_path.parent.mkdir(exist_ok=True)

    task_order = ["M1", "M2", "M3", "M4", "Q1", "Q2", "Q3", "Q4", "O1", "O2", "O3", "O4", "X1", "X2", "X1p", "X2p"]
    by_task: Dict[str, List[float]] = {}
    for r in normal_results:
        by_task.setdefault(r["task_id"], []).append(r["task_latency_ms"])

    present_tasks = [t for t in task_order if t in by_task]
    data = [by_task[t] for t in present_tasks]

    fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
    bp = ax.boxplot(data, labels=present_tasks, patch_artist=True)

    family_colors = {"M": "#0F766E", "Q": "#1D4ED8", "O": "#B45309", "X": "#6B7280"}
    for i, task_id in enumerate(present_tasks):
        color = family_colors.get(task_id[0], "#9CA3AF")
        bp["boxes"][i].set_facecolor(color)
        bp["boxes"][i].set_alpha(0.6)

    ax.set_ylabel("Latency (ms)")
    ax.set_title(f"Per-task latency distributions ({NORMAL_REPS} repetitions)")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


async def main() -> None:
    modbus_mock = ManagedProcess(
        "modbus-mock",
        ["uv", "run", "modbus-mock-server"],
        ROOT / "MODBUS-Project/modbus-mock-server",
        host="127.0.0.1",
        port=1502,
    )
    broker = ManagedProcess(
        "mqtt-broker",
        ["npx", "-y", "aedes-cli", "start", "--host", "127.0.0.1", "--port", "1883"],
        ROOT,
        host="127.0.0.1",
        port=1883,
    )
    mqtt_mock = ManagedProcess(
        "mqtt-mock",
        ["uv", "run", "mqtt-mock-server"],
        ROOT / "MQTT-Project/mqtt-mock-server",
    )
    opcua_server = ManagedProcess(
        "opcua-local-server",
        ["uv", "run", "main.py"],
        ROOT / "OPCUA-Project/opcua-local-server",
        host="127.0.0.1",
        port=4840,
    )

    try:
        await modbus_mock.start()
        await broker.start()
        await mqtt_mock.start()
        await opcua_server.start()
        await asyncio.sleep(1.0)

        async with mcp_session(
            "uv",
            ["run", "modbus-mcp"],
            ROOT / "MODBUS-Project/modbus-python",
            {
                "MODBUS_TYPE": "tcp",
                "MODBUS_HOST": "127.0.0.1",
                "MODBUS_PORT": "1502",
                "MODBUS_DEFAULT_SLAVE_ID": "1",
            },
        ) as modbus_rw, mcp_session(
            "uv",
            ["run", "modbus-mcp"],
            ROOT / "MODBUS-Project/modbus-python",
            {
                "MODBUS_TYPE": "tcp",
                "MODBUS_HOST": "127.0.0.1",
                "MODBUS_PORT": "1502",
                "MODBUS_DEFAULT_SLAVE_ID": "1",
                "MODBUS_WRITES_ENABLED": "false",
            },
        ) as modbus_ro, mcp_session(
            "uv",
            ["run", "mqtt-mcp"],
            ROOT / "MQTT-Project/mqtt-python",
            {
                "MQTT_BROKER_URL": "mqtt://127.0.0.1:1883",
                "MQTT_CLIENT_ID": "mqtt-mcp-benchmark",
                "SPARKPLUG_GROUP_ID": "factory",
                "SPARKPLUG_EDGE_NODE_ID": "edge-node-1",
            },
        ) as mqtt, mcp_session(
            "uv",
            ["run", "opcua-mcp-server.py"],
            ROOT / "OPCUA-Project/opcua-mcp-server",
            {"OPCUA_SERVER_URL": "opc.tcp://127.0.0.1:4840/freeopcua/server/"},
        ) as opcua:
            opcua_nodes = await discover_opcua_nodes(opcua)
            normal_results = await run_normal_tasks(modbus_rw, modbus_ro, mqtt, opcua, opcua_nodes)
            fault_results = await run_fault_injection_tasks(modbus_rw, mqtt, opcua, opcua_nodes)
            stress_results = await run_stress_tasks(modbus_rw, mqtt, opcua, opcua_nodes, modbus_mock, broker, opcua_server)

        recovery_results = await run_recovery_tasks(modbus_mock, broker, opcua_server)
        normal_summary = aggregate_normal_results(normal_results)
        fault_summary = aggregate_fault_results(fault_results)
        stress_summary = aggregate_stress_results(stress_results)
        recovery_summary = aggregate_recovery_results(recovery_results)
        protocol_inventory = build_protocol_inventory()
        recovery_figure = write_recovery_figure(recovery_summary)
        latency_boxplot = write_latency_boxplot(normal_results)

        # Compute exact tool call counts (2E)
        normal_tool_calls = sum(r["tool_calls"] for r in normal_results)
        fault_tool_calls = sum(r["tool_calls"] for r in fault_results)
        stress_tool_calls = sum(r["tool_calls"] for r in stress_results)
        exact_tool_call_counts = {
            "normal": normal_tool_calls,
            "fault": fault_tool_calls,
            "stress": stress_tool_calls,
            "total": normal_tool_calls + fault_tool_calls + stress_tool_calls,
        }

        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repetition_counts": {
                "normal": NORMAL_REPS,
                "fault": FAULT_REPS,
                "recovery": RECOVERY_REPS,
                "stress": STRESS_REPS,
            },
            "normal_tasks": normal_results,
            "normal_summary": normal_summary,
            "fault_injection_tasks": fault_results,
            "fault_injection_summary": fault_summary,
            "stress_tasks": stress_results,
            "stress_summary": stress_summary,
            "recovery_trials": recovery_results,
            "recovery_summary": recovery_summary,
            "exact_tool_call_counts": exact_tool_call_counts,
            "protocol_inventory": protocol_inventory,
            "artifacts": {
                "recovery_figure": str(recovery_figure.relative_to(ROOT)),
                "latency_boxplot": str(latency_boxplot.relative_to(ROOT)),
            },
        }

        output_path = GENERATED / "flagship_benchmark_results.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote benchmark results to {output_path}")
        print(f"Wrote recovery figure to {recovery_figure}")
        print(f"Wrote latency boxplot to {latency_boxplot}")
        print(f"Exact tool call counts: {exact_tool_call_counts}")
    finally:
        await mqtt_mock.stop()
        await broker.stop()
        await modbus_mock.stop()
        await opcua_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
