#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import matplotlib.pyplot as plt
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[2]
ARXIV_PAPER = ROOT / "arxiv-paper"
GENERATED = ARXIV_PAPER / "generated"
GENERATED.mkdir(exist_ok=True)


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
    if "bad" in error or "exception" in error:
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
) -> Dict[str, Any]:
    matched = [bool(check) for check in checks]
    failures = [classify_error(call) for ok, call in zip(matched, calls) if not ok]
    return {
        "task_id": task_id,
        "family": family,
        "description": description,
        "repetition": repetition,
        "task_success": all(matched),
        "tool_calls": len(calls),
        "tool_call_successes": sum(1 for ok in matched if ok),
        "task_latency_ms": round((time.perf_counter() - started_at) * 1000.0, 3),
        "retry_count": sum(extract_retry_count(call) for call in calls),
        "failure_classes": [failure for failure in failures if failure],
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
    for repetition in range(1, 11):
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

        # Cross-protocol tasks
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

    return results


async def recovery_trial(
    family: str,
    description: str,
    stop_process: ManagedProcess,
    restart_process: ManagedProcess,
    failure_call: Callable[[], Any],
    success_call: Callable[[], Any],
) -> Dict[str, Any]:
    started = time.perf_counter()
    failure_result = None
    success_result = None

    await stop_process.stop()
    await asyncio.sleep(0.5)
    failure_result = await failure_call()

    await restart_process.start()
    await asyncio.sleep(1.0)
    success_result = await success_call()

    failure_observed = not bool(failure_result.get("success"))
    post_restart_success = bool(success_result.get("success"))

    return {
        "family": family,
        "description": description,
        "recovery_success": failure_observed and post_restart_success,
        "outage_detected": failure_observed,
        "post_restart_success": post_restart_success,
        "trial_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "failure_result": failure_result,
        "success_result": success_result,
    }


async def run_recovery_tasks(
    modbus_mock: ManagedProcess,
    broker: ManagedProcess,
    opcua_server: ManagedProcess,
) -> Dict[str, List[Dict[str, Any]]]:
    results = {"Modbus": [], "MQTT": [], "OPC UA": []}

    for _ in range(10):
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
                "Stop the Modbus mock, confirm a failed read, restart it, and reopen a healthy session.",
                modbus_mock,
                modbus_mock,
                failure_call=lambda: call_tool_json(session, "read_register", {"address": 1}),
                success_call=lambda: _recovery_success_call(
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

    for _ in range(10):
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
                "Stop the MQTT broker, confirm a failed publish, restart it, and reopen a healthy session.",
                broker,
                broker,
                failure_call=lambda: call_tool_json(
                    session,
                    "publish_message",
                    {"topic": "control/pump", "payload": "{\"pump_speed\": 0}", "qos": 0, "retain": False},
                ),
                success_call=lambda: _recovery_success_call(
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

    for _ in range(10):
        async with mcp_session(
            "uv",
            ["run", "opcua-mcp-server.py"],
            ROOT / "OPCUA-Project/opcua-mcp-server",
            {"OPCUA_SERVER_URL": "opc.tcp://127.0.0.1:4840/freeopcua/server/"},
        ) as session:
            await call_tool_json(session, "read_opcua_node", {"node_id": "ns=2;i=3"})
            trial = await recovery_trial(
                "OPC UA",
                "Stop the OPC UA mock, confirm a failed read, restart it, and reopen a healthy session.",
                opcua_server,
                opcua_server,
                failure_call=lambda: call_tool_json(session, "read_opcua_node", {"node_id": "ns=2;i=3"}),
                success_call=lambda: _recovery_success_call(
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
        family_summary[family] = {
            "tasks": len({row["task_id"] for row in rows}),
            "task_success_rate": round(sum(1 for row in rows if row["task_success"]) / len(rows), 3),
            "tool_call_success_rate": round(sum(row["tool_call_successes"] for row in rows) / total_calls, 3),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": percentile(latencies, 95),
            "total_retries": sum(row["retry_count"] for row in rows),
        }

    task_summary = {}
    for task_id, rows in by_task.items():
        latencies = [row["task_latency_ms"] for row in rows]
        description = rows[0]["description"]
        family = rows[0]["family"]
        task_summary[task_id] = {
            "family": family,
            "description": description,
            "task_success_rate": round(sum(1 for row in rows if row["task_success"]) / len(rows), 3),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": percentile(latencies, 95),
        }

    return {"by_family": family_summary, "by_task": task_summary}


def aggregate_recovery_results(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    summary = {}
    for family, rows in results.items():
        summary[family] = {
            "recovery_success_rate": round(
                sum(1 for row in rows if row["recovery_success"]) / len(rows),
                3,
            ),
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
    values = [summary[label]["recovery_success_rate"] * 100.0 for label in labels]

    fig, ax = plt.subplots(figsize=(5.0, 2.8), constrained_layout=True)
    colors = ["#0F766E", "#1D4ED8", "#B45309"]
    bars = ax.bar(labels, values, color=colors, width=0.58)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Recovery success (%)")
    ax.set_title("Post-restart recovery over 10 trials")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.5)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 2.0,
            f"{value:.0f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

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

        recovery_results = await run_recovery_tasks(modbus_mock, broker, opcua_server)
        normal_summary = aggregate_normal_results(normal_results)
        recovery_summary = aggregate_recovery_results(recovery_results)
        protocol_inventory = build_protocol_inventory()
        recovery_figure = write_recovery_figure(recovery_summary)

        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "normal_tasks": normal_results,
            "normal_summary": normal_summary,
            "recovery_trials": recovery_results,
            "recovery_summary": recovery_summary,
            "protocol_inventory": protocol_inventory,
            "artifacts": {"recovery_figure": str(recovery_figure.relative_to(ROOT))},
        }

        output_path = GENERATED / "flagship_benchmark_results.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote benchmark results to {output_path}")
        print(f"Wrote recovery figure to {recovery_figure}")
    finally:
        await mqtt_mock.stop()
        await broker.stop()
        await modbus_mock.stop()
        await opcua_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
