#!/usr/bin/env python3
"""Quantitative LLM assessment for IndustriConnect MCP tool schemas.

Feeds MCP tool schemas to the Claude API (NOT live MCP connections) and
evaluates structured tool-use responses against ground truth across four
assessment categories:

  1. Tool discovery recall
  2. Tool selection accuracy
  3. Parameter correctness (per-field accuracy)
  4. Error interpretation accuracy

Models evaluated: Claude Sonnet 4 and Claude Haiku 4 -- two size points
from the same family. Multi-family evaluation is noted as future work.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
ARXIV_PAPER = ROOT / "arxiv-paper"
GENERATED = ARXIV_PAPER / "generated"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

MODELS: List[str] = [
    "claude-sonnet-4-20250514",
    "claude-haiku-4-5-20251001",
]

# ---------------------------------------------------------------------------
# MCP tool schemas (JSON tool definitions for the Claude API)
# ---------------------------------------------------------------------------
# These capture tool names, descriptions, and parameter schemas faithfully
# but are defined inline for benchmark portability -- they do not import from
# the live MCP servers.
# ---------------------------------------------------------------------------


def _prop(
    name: str,
    typ: str,
    description: str,
    *,
    required: bool = True,
    default: Any = None,
    enum: Optional[List[Any]] = None,
    items: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any], bool]:
    """Helper to build a JSON-Schema property triple."""
    schema: Dict[str, Any] = {"type": typ, "description": description}
    if default is not None:
        schema["default"] = default
    if enum is not None:
        schema["enum"] = enum
    if items is not None:
        schema["items"] = items
    return name, schema, required


def _tool(
    name: str,
    description: str,
    props: List[Tuple[str, Dict[str, Any], bool]],
) -> Dict[str, Any]:
    """Build a Claude-API-compatible tool definition."""
    properties = {}
    required = []
    for pname, pschema, preq in props:
        properties[pname] = pschema
        if preq:
            required.append(pname)
    schema: Dict[str, Any] = {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }
    return schema


def _build_modbus_tools() -> List[Dict[str, Any]]:
    """20 Modbus MCP tool definitions."""
    slave = _prop("slave_id", "integer", "Modbus slave/device ID.", required=False, default=1)
    addr = _prop("address", "integer", "Register/coil starting address (0-65535).")
    count = _prop("count", "integer", "Number of registers/coils to read.")
    val_int = _prop("value", "integer", "Value to write (0-65535).")
    val_bool = _prop("value", "boolean", "Coil state (true=ON, false=OFF).")

    return [
        _tool("read_register", "Read a single Modbus holding register.", [addr, slave]),
        _tool("write_register", "Write a value to a Modbus holding register.", [addr, val_int, slave]),
        _tool("read_coils", "Read the status of multiple Modbus coils.", [addr, count, slave]),
        _tool("write_coil", "Write a value to a single Modbus coil.", [addr, val_bool, slave]),
        _tool("read_input_registers", "Read multiple Modbus input registers.", [addr, count, slave]),
        _tool("read_multiple_holding_registers", "Read multiple Modbus holding registers.", [addr, count, slave]),
        _tool("read_discrete_inputs", "Read multiple Modbus discrete inputs (function code 2).", [addr, count, slave]),
        _tool("write_registers", "Write multiple holding registers (function code 16).", [
            addr,
            _prop("values", "array", "List of register values to write.", items={"type": "integer"}),
            slave,
        ]),
        _tool("write_coils_bulk", "Write multiple coils at once (function code 15).", [
            addr,
            _prop("values", "array", "List of coil states to write.", items={"type": "boolean"}),
            slave,
        ]),
        _tool("mask_write_register", "Mask write register (function 22): result = (reg AND and_mask) OR (or_mask AND NOT and_mask).", [
            addr,
            _prop("and_mask", "integer", "AND mask (0-65535)."),
            _prop("or_mask", "integer", "OR mask (0-65535)."),
            slave,
        ]),
        _tool("read_device_information", "Read device identification / information (MEI type 0x2B/0x0E).", [
            slave,
            _prop("read_code", "integer", "Read code: 1=basic, 2=regular, 3=extended.", required=False, default=3),
            _prop("object_id", "integer", "Starting object ID.", required=False, default=0),
        ]),
        _tool("read_holding_typed", "Read holding registers and decode as typed values (int16, uint16, float32, etc.).", [
            addr,
            _prop("dtype", "string", "Data type to decode.", enum=["int16", "uint16", "int32", "uint32", "float32", "int64", "uint64", "float64"]),
            _prop("count", "integer", "Number of typed values to decode.", required=False, default=1),
            _prop("byteorder", "string", "Byte order (big/little).", required=False, default="big"),
            _prop("wordorder", "string", "Word order (big/little).", required=False, default="big"),
            _prop("scale", "number", "Scale factor applied after decode.", required=False, default=1.0),
            _prop("offset", "number", "Offset applied after decode.", required=False, default=0.0),
            slave,
        ]),
        _tool("read_input_typed", "Read input registers and decode as typed values.", [
            addr,
            _prop("dtype", "string", "Data type to decode.", enum=["int16", "uint16", "int32", "uint32", "float32", "int64", "uint64", "float64"]),
            _prop("count", "integer", "Number of typed values to decode.", required=False, default=1),
            _prop("byteorder", "string", "Byte order (big/little).", required=False, default="big"),
            _prop("wordorder", "string", "Word order (big/little).", required=False, default="big"),
            _prop("scale", "number", "Scale factor applied after decode.", required=False, default=1.0),
            _prop("offset", "number", "Offset applied after decode.", required=False, default=0.0),
            slave,
        ]),
        _tool("write_holding_typed", "Write typed values to holding registers (int16, uint16, float32, etc.).", [
            addr,
            _prop("dtype", "string", "Data type to encode.", enum=["int16", "uint16", "int32", "uint32", "float32", "int64", "uint64", "float64"]),
            _prop("values", "array", "Typed values to encode and write.", items={"type": "number"}),
            _prop("byteorder", "string", "Byte order (big/little).", required=False, default="big"),
            _prop("wordorder", "string", "Word order (big/little).", required=False, default="big"),
            slave,
        ]),
        _tool("list_tags", "List available tags from the register map file.", []),
        _tool("read_tag", "Read a value using the configured tag map (REGISTER_MAP_FILE).", [
            _prop("name", "string", "Tag name from the register map."),
        ]),
        _tool("write_tag", "Write a value using the configured tag map. Only holding regs and coils are writable.", [
            _prop("name", "string", "Tag name from the register map."),
            _prop("value", "string", "Value to write (will be converted to the tag's data type)."),
        ]),
        _tool("read_exception_status", "Read the exception status from the Modbus device (function code 7).", [
            slave,
        ]),
        _tool("ping", "Return Modbus server health and connection status.", []),
        _tool("diagnose_connection", "Run connectivity diagnostics against the Modbus endpoint and return a health report.", [
            slave,
        ]),
    ]


def _deduplicate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate tool names, keeping the first occurrence."""
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for t in tools:
        if t["name"] not in seen:
            seen.add(t["name"])
            out.append(t)
    return out


def _build_mqtt_tools() -> List[Dict[str, Any]]:
    """15 MQTT + Sparkplug B MCP tool definitions."""
    return [
        _tool("get_broker_info", "Get MQTT broker connection info and status.", []),
        _tool("subscribe_topic", "Subscribe to an MQTT topic pattern.", [
            _prop("topic", "string", "MQTT topic or wildcard pattern."),
            _prop("qos", "integer", "Quality of Service level (0, 1, or 2).", required=False, default=0),
        ]),
        _tool("unsubscribe_topic", "Unsubscribe from an MQTT topic.", [
            _prop("topic", "string", "MQTT topic to unsubscribe from."),
        ]),
        _tool("publish_message", "Publish a message to an MQTT topic.", [
            _prop("topic", "string", "MQTT topic to publish to."),
            _prop("payload", "string", "Message payload (UTF-8 string or JSON)."),
            _prop("qos", "integer", "Quality of Service level (0, 1, or 2).", required=False, default=0),
            _prop("retain", "boolean", "Whether to set the retain flag.", required=False, default=False),
        ]),
        _tool("get_subscriptions", "List active MQTT subscriptions.", []),
        _tool("get_received_messages", "Retrieve messages received on subscribed topics.", []),
        _tool("publish_device_birth", "Publish a Sparkplug B DBIRTH certificate for a device.", [
            _prop("device_id", "string", "Device identifier."),
            _prop("metrics", "array", "List of metric objects with name, value, and type.", items={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {},
                    "type": {"type": "string"},
                },
            }),
        ]),
        _tool("publish_device_death", "Publish a Sparkplug B DDEATH certificate for a device.", [
            _prop("device_id", "string", "Device identifier."),
        ]),
        _tool("publish_device_data", "Publish a Sparkplug B DDATA update for a device.", [
            _prop("device_id", "string", "Device identifier."),
            _prop("metrics", "array", "List of metric objects with name, value, and type.", items={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {},
                    "type": {"type": "string"},
                },
            }),
        ]),
        _tool("publish_device_command", "Publish a Sparkplug B DCMD message to a device.", [
            _prop("device_id", "string", "Device identifier."),
            _prop("metrics", "array", "List of command metric objects.", items={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {},
                    "type": {"type": "string"},
                },
            }),
        ]),
        _tool("get_sparkplug_state", "List published Sparkplug birth certificates tracked by the adapter.", []),
        _tool("set_sparkplug_config", "Update Sparkplug B configuration (group ID, edge node ID).", [
            _prop("group_id", "string", "Sparkplug group identifier.", required=False),
            _prop("edge_node_id", "string", "Sparkplug edge node identifier.", required=False),
        ]),
        _tool("subscribe_sparkplug_topics", "Subscribe to standard Sparkplug B topic namespaces.", [
            _prop("group_id", "string", "Sparkplug group ID to subscribe to.", required=False),
        ]),
        _tool("get_sparkplug_metrics", "Decode and return the latest Sparkplug metrics from received messages.", []),
        _tool("clear_received_messages", "Clear the received message buffer.", []),
    ]


def _build_opcua_tools() -> List[Dict[str, Any]]:
    """7 OPC UA MCP tool definitions."""
    return [
        _tool("read_opcua_node", "Read the value of a specific OPC UA node.", [
            _prop("node_id", "string", "OPC UA node identifier (e.g. 'ns=2;i=3')."),
        ]),
        _tool("write_opcua_node", "Write a value to a specific OPC UA node.", [
            _prop("node_id", "string", "OPC UA node identifier."),
            _prop("value", "string", "Value to write (auto-converted to the node's data type)."),
        ]),
        _tool("browse_opcua_node_children", "Browse the children of a specific OPC UA node.", [
            _prop("node_id", "string", "OPC UA node identifier to browse."),
        ]),
        _tool("call_opcua_method", "Call a method on a specific OPC UA object node.", [
            _prop("object_node_id", "string", "OPC UA object node that owns the method."),
            _prop("method_node_id", "string", "OPC UA method node to call."),
            _prop("arguments", "array", "Method arguments.", required=False, items={}),
        ]),
        _tool("read_multiple_opcua_nodes", "Read multiple OPC UA nodes in a single call.", [
            _prop("node_ids", "array", "List of OPC UA node identifiers.", items={"type": "string"}),
        ]),
        _tool("write_multiple_opcua_nodes", "Write multiple OPC UA nodes in a single call.", [
            _prop("nodes_to_write", "array", "List of {node_id, value} objects.", items={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "value": {},
                },
            }),
        ]),
        _tool("get_all_variables", "Return all non-server OPC UA variables exposed by the connected endpoint.", []),
    ]


def build_all_tools() -> List[Dict[str, Any]]:
    """Return the combined tool list (42 unique tools across 3 protocols)."""
    tools = _build_modbus_tools() + _build_mqtt_tools() + _build_opcua_tools()
    return _deduplicate_tools(tools)


ALL_MODBUS_TOOL_NAMES = [
    "read_register", "write_register", "read_coils", "write_coil",
    "read_input_registers", "read_multiple_holding_registers",
    "read_discrete_inputs", "write_registers", "write_coils_bulk",
    "mask_write_register", "read_device_information",
    "read_holding_typed", "read_input_typed", "write_holding_typed",
    "read_exception_status",
    "list_tags", "read_tag", "write_tag",
    "ping", "diagnose_connection",
]

ALL_MQTT_TOOL_NAMES = [
    "get_broker_info", "subscribe_topic", "unsubscribe_topic",
    "publish_message", "get_subscriptions", "get_received_messages",
    "publish_device_birth", "publish_device_death", "publish_device_data",
    "publish_device_command", "get_sparkplug_state", "set_sparkplug_config",
    "subscribe_sparkplug_topics", "get_sparkplug_metrics",
    "clear_received_messages",
]

ALL_OPCUA_TOOL_NAMES = [
    "read_opcua_node", "write_opcua_node", "browse_opcua_node_children",
    "call_opcua_method", "read_multiple_opcua_nodes",
    "write_multiple_opcua_nodes", "get_all_variables",
]

ALL_TOOL_NAMES = ALL_MODBUS_TOOL_NAMES + ALL_MQTT_TOOL_NAMES + ALL_OPCUA_TOOL_NAMES

WRITE_CAPABLE_TOOLS = [
    "write_register", "write_coil", "write_registers", "write_coils_bulk",
    "mask_write_register", "write_holding_typed", "write_tag",
    "publish_message", "publish_device_birth", "publish_device_death",
    "publish_device_data", "publish_device_command",
    "set_sparkplug_config",
    "write_opcua_node", "write_multiple_opcua_nodes",
]

# ---------------------------------------------------------------------------
# Prompt corpus: 45 test prompts across 4 categories
# ---------------------------------------------------------------------------


def _build_discovery_prompts() -> List[Dict[str, Any]]:
    """5 discovery prompts -- model must identify/list tool subsets."""
    return [
        {
            "id": "D1",
            "category": "discovery",
            "prompt": "List all available tools.",
            "expected_tools": ALL_TOOL_NAMES,
        },
        {
            "id": "D2",
            "category": "discovery",
            "prompt": "Which tools can perform write operations?",
            "expected_tools": WRITE_CAPABLE_TOOLS,
        },
        {
            "id": "D3",
            "category": "discovery",
            "prompt": "List the Modbus-specific tools.",
            "expected_tools": ALL_MODBUS_TOOL_NAMES,
        },
        {
            "id": "D4",
            "category": "discovery",
            "prompt": "Which tools are related to Sparkplug B?",
            "expected_tools": [
                "publish_device_birth", "publish_device_death",
                "publish_device_data", "publish_device_command",
                "get_sparkplug_state", "set_sparkplug_config",
                "subscribe_sparkplug_topics", "get_sparkplug_metrics",
            ],
        },
        {
            "id": "D5",
            "category": "discovery",
            "prompt": "Which tools support reading data from OPC UA nodes?",
            "expected_tools": [
                "read_opcua_node", "read_multiple_opcua_nodes",
                "get_all_variables", "browse_opcua_node_children",
            ],
        },
    ]


def _build_tool_selection_prompts() -> List[Dict[str, Any]]:
    """15 tool selection prompts (5 per protocol)."""
    return [
        # Modbus (5)
        {
            "id": "TS1",
            "category": "tool_selection",
            "prompt": "I need to read the value of holding register 100 from a Modbus device.",
            "expected_tool": "read_register",
        },
        {
            "id": "TS2",
            "category": "tool_selection",
            "prompt": "Set holding register 50 to the value 1234 on the Modbus PLC.",
            "expected_tool": "write_register",
        },
        {
            "id": "TS3",
            "category": "tool_selection",
            "prompt": "Read the temperature sensor from Modbus input registers 0 through 3 as a 32-bit float.",
            "expected_tool": "read_input_typed",
        },
        {
            "id": "TS4",
            "category": "tool_selection",
            "prompt": "Check if the Modbus TCP connection is alive and healthy.",
            "expected_tool": "ping",
        },
        {
            "id": "TS5",
            "category": "tool_selection",
            "prompt": "Toggle coil at address 10 to ON on the Modbus device.",
            "expected_tool": "write_coil",
        },
        # MQTT (5)
        {
            "id": "TS6",
            "category": "tool_selection",
            "prompt": "Send a JSON payload to the MQTT topic 'factory/line1/status'.",
            "expected_tool": "publish_message",
        },
        {
            "id": "TS7",
            "category": "tool_selection",
            "prompt": "Start listening for messages on the MQTT topic 'sensors/#'.",
            "expected_tool": "subscribe_topic",
        },
        {
            "id": "TS8",
            "category": "tool_selection",
            "prompt": "Check whether the MQTT broker connection is active.",
            "expected_tool": "get_broker_info",
        },
        {
            "id": "TS9",
            "category": "tool_selection",
            "prompt": "Publish a Sparkplug B data update for device 'pump-1' with a temperature metric.",
            "expected_tool": "publish_device_data",
        },
        {
            "id": "TS10",
            "category": "tool_selection",
            "prompt": "Register a new device 'valve-3' on the Sparkplug B network with its birth certificate.",
            "expected_tool": "publish_device_birth",
        },
        # OPC UA (5)
        {
            "id": "TS11",
            "category": "tool_selection",
            "prompt": "Read the current value of OPC UA node ns=2;i=5.",
            "expected_tool": "read_opcua_node",
        },
        {
            "id": "TS12",
            "category": "tool_selection",
            "prompt": "Set the valve position node ns=2;i=14 to 75.0 in the OPC UA server.",
            "expected_tool": "write_opcua_node",
        },
        {
            "id": "TS13",
            "category": "tool_selection",
            "prompt": "Show me all the child nodes under the Sensors folder in OPC UA (ns=2;i=2).",
            "expected_tool": "browse_opcua_node_children",
        },
        {
            "id": "TS14",
            "category": "tool_selection",
            "prompt": "Enumerate all variables available in the OPC UA server's address space.",
            "expected_tool": "get_all_variables",
        },
        {
            "id": "TS15",
            "category": "tool_selection",
            "prompt": "Read the temperature and pressure OPC UA nodes (ns=2;i=3 and ns=2;i=4) simultaneously.",
            "expected_tool": "read_multiple_opcua_nodes",
        },
    ]


def _build_parameter_correctness_prompts() -> List[Dict[str, Any]]:
    """15 parameter correctness prompts (5 per protocol)."""
    return [
        # Modbus (5)
        {
            "id": "PC1",
            "category": "parameter_correctness",
            "prompt": "Read holding register at address 42 from slave 2.",
            "expected_tool": "read_register",
            "expected_params": {"address": 42, "slave_id": 2},
        },
        {
            "id": "PC2",
            "category": "parameter_correctness",
            "prompt": "Write the value 500 to holding register 10 on the default slave.",
            "expected_tool": "write_register",
            "expected_params": {"address": 10, "value": 500},
        },
        {
            "id": "PC3",
            "category": "parameter_correctness",
            "prompt": "Read 8 coils starting from address 0 on slave 3.",
            "expected_tool": "read_coils",
            "expected_params": {"address": 0, "count": 8, "slave_id": 3},
        },
        {
            "id": "PC4",
            "category": "parameter_correctness",
            "prompt": "Read a 32-bit float from input registers starting at address 100 with big-endian byte order.",
            "expected_tool": "read_input_typed",
            "expected_params": {"address": 100, "dtype": "float32", "byteorder": "big"},
        },
        {
            "id": "PC5",
            "category": "parameter_correctness",
            "prompt": "Apply a mask write to register 200: AND mask 0xFF00 and OR mask 0x00AB on slave 1.",
            "expected_tool": "mask_write_register",
            "expected_params": {"address": 200, "and_mask": 0xFF00, "or_mask": 0x00AB},
        },
        # MQTT (5)
        {
            "id": "PC6",
            "category": "parameter_correctness",
            "prompt": "Publish '{\"temp\": 25.5}' to MQTT topic 'sensors/temp' with QoS 1 and retain enabled.",
            "expected_tool": "publish_message",
            "expected_params": {"topic": "sensors/temp", "qos": 1, "retain": True},
        },
        {
            "id": "PC7",
            "category": "parameter_correctness",
            "prompt": "Subscribe to MQTT topic 'factory/+/alarms' with QoS 2.",
            "expected_tool": "subscribe_topic",
            "expected_params": {"topic": "factory/+/alarms", "qos": 2},
        },
        {
            "id": "PC8",
            "category": "parameter_correctness",
            "prompt": "Unsubscribe from MQTT topic 'sensors/#'.",
            "expected_tool": "unsubscribe_topic",
            "expected_params": {"topic": "sensors/#"},
        },
        {
            "id": "PC9",
            "category": "parameter_correctness",
            "prompt": "Send a Sparkplug B DDATA update for device 'motor-1' with metric 'rpm' = 1500 (type int).",
            "expected_tool": "publish_device_data",
            "expected_params": {"device_id": "motor-1"},
        },
        {
            "id": "PC10",
            "category": "parameter_correctness",
            "prompt": "Send a Sparkplug B command to device 'valve-2' to set 'position' to 50.0 (type float).",
            "expected_tool": "publish_device_command",
            "expected_params": {"device_id": "valve-2"},
        },
        # OPC UA (5)
        {
            "id": "PC11",
            "category": "parameter_correctness",
            "prompt": "Read OPC UA node ns=2;i=7.",
            "expected_tool": "read_opcua_node",
            "expected_params": {"node_id": "ns=2;i=7"},
        },
        {
            "id": "PC12",
            "category": "parameter_correctness",
            "prompt": "Write value 100.5 to OPC UA node ns=2;i=14.",
            "expected_tool": "write_opcua_node",
            "expected_params": {"node_id": "ns=2;i=14"},
        },
        {
            "id": "PC13",
            "category": "parameter_correctness",
            "prompt": "Browse children of OPC UA node ns=2;i=1.",
            "expected_tool": "browse_opcua_node_children",
            "expected_params": {"node_id": "ns=2;i=1"},
        },
        {
            "id": "PC14",
            "category": "parameter_correctness",
            "prompt": "Read OPC UA nodes ns=2;i=3, ns=2;i=4, and ns=2;i=5 together.",
            "expected_tool": "read_multiple_opcua_nodes",
            "expected_params": {"node_ids": ["ns=2;i=3", "ns=2;i=4", "ns=2;i=5"]},
        },
        {
            "id": "PC15",
            "category": "parameter_correctness",
            "prompt": "Call OPC UA method ns=2;i=100 on object ns=2;i=1 with arguments [42, true].",
            "expected_tool": "call_opcua_method",
            "expected_params": {"object_node_id": "ns=2;i=1", "method_node_id": "ns=2;i=100"},
        },
    ]


def _build_error_interpretation_prompts() -> List[Dict[str, Any]]:
    """10 error interpretation prompts with real fault-injection envelopes."""
    return [
        {
            "id": "EI1",
            "category": "error_interpretation",
            "prompt": (
                "I called read_register with address=9999 and got this error envelope:\n"
                '{"success": false, "data": null, "error": "ModbusException: Illegal address 9999", '
                '"meta": {"address": 9999, "slave_id": 1, "duration_ms": 12.5, "attempts": 3}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "illegal_address",
        },
        {
            "id": "EI2",
            "category": "error_interpretation",
            "prompt": (
                "I called write_register and got this error envelope:\n"
                '{"success": false, "data": null, "error": "Writes are disabled by configuration", '
                '"meta": {"address": 1, "slave_id": 1}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "guarded_write",
        },
        {
            "id": "EI3",
            "category": "error_interpretation",
            "prompt": (
                "I called read_register and got this error envelope:\n"
                '{"success": false, "data": null, "error": "TimeoutError: Timed out after 5.0s", '
                '"meta": {"address": 0, "slave_id": 1, "duration_ms": 5002.1, "attempts": 3}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "timeout",
        },
        {
            "id": "EI4",
            "category": "error_interpretation",
            "prompt": (
                "I called publish_message with topic='' and got this error envelope:\n"
                '{"success": false, "data": null, "error": "Publish failed for : Invalid empty topic", '
                '"meta": {"duration_ms": 0.5, "connected": true, "topic": "", "qos": 0}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "invalid_input",
        },
        {
            "id": "EI5",
            "category": "error_interpretation",
            "prompt": (
                "I called write_opcua_node with value='not_a_number' on a float node and got:\n"
                '{"success": false, "data": null, "error": "Write failed for ns=2;i=14: '
                "TypeError: float() argument must be a string or a real number, not 'not_a_number'\", "
                '"meta": {"duration_ms": 8.3, "server_url": "opc.tcp://127.0.0.1:4840/freeopcua/server/"}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "type_mismatch",
        },
        {
            "id": "EI6",
            "category": "error_interpretation",
            "prompt": (
                "I called get_broker_info and got this error envelope:\n"
                '{"success": false, "data": null, "error": "Not connected to MQTT broker: Client is not connected", '
                '"meta": {"duration_ms": 1.2, "connected": false}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "endpoint_unavailable",
        },
        {
            "id": "EI7",
            "category": "error_interpretation",
            "prompt": (
                "I called read_opcua_node with node_id='ns=2;i=99999' and got:\n"
                '{"success": false, "data": null, "error": "Read failed for ns=2;i=99999: '
                'BadNodeIdUnknown", "meta": {"duration_ms": 5.1, '
                '"server_url": "opc.tcp://127.0.0.1:4840/freeopcua/server/"}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "illegal_address",
        },
        {
            "id": "EI8",
            "category": "error_interpretation",
            "prompt": (
                "I called subscribe_topic with qos=5 and got:\n"
                '{"success": false, "data": null, "error": "Subscribe failed for sensors/#: '
                'Invalid QoS value 5 (must be 0, 1, or 2)", '
                '"meta": {"duration_ms": 0.3, "connected": true, "topic": "sensors/#", "qos": 5}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "invalid_input",
        },
        {
            "id": "EI9",
            "category": "error_interpretation",
            "prompt": (
                "I called read_register and got this error:\n"
                '{"success": false, "data": null, "error": "ModbusException: Illegal function code", '
                '"meta": {"address": 0, "slave_id": 1, "duration_ms": 3.2, "attempts": 1}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "protocol_error",
        },
        {
            "id": "EI10",
            "category": "error_interpretation",
            "prompt": (
                "I called write_register with value=70000 and got:\n"
                '{"success": false, "data": null, "error": "Value 70000 out of uint16 range (0-65535)", '
                '"meta": {"address": 1, "value": 70000}}\n'
                "What class of error is this? Respond with exactly one of: "
                "illegal_address, timeout, type_mismatch, endpoint_unavailable, guarded_write, invalid_input, protocol_error"
            ),
            "expected_error_class": "invalid_input",
        },
    ]


def build_prompt_corpus() -> List[Dict[str, Any]]:
    """Return the full 45-prompt corpus."""
    corpus: List[Dict[str, Any]] = []
    corpus.extend(_build_discovery_prompts())
    corpus.extend(_build_tool_selection_prompts())
    corpus.extend(_build_parameter_correctness_prompts())
    corpus.extend(_build_error_interpretation_prompts())
    return corpus


# ---------------------------------------------------------------------------
# Claude API interaction
# ---------------------------------------------------------------------------


async def call_claude(
    client: Any,  # anthropic.AsyncAnthropic
    model: str,
    prompt: str,
    tools: List[Dict[str, Any]],
    category: str,
) -> Dict[str, Any]:
    """Send a single prompt to the Claude API and return the raw response.

    For discovery and error_interpretation categories we ask for a text
    response. For tool_selection and parameter_correctness we enable tool use.
    """
    system_msg = (
        "You are an expert industrial automation assistant. You have access "
        "to MCP (Model Context Protocol) tools for Modbus, MQTT/Sparkplug B, "
        "and OPC UA protocols. Answer precisely and use tool calls when the "
        "user asks you to perform an action."
    )

    messages = [{"role": "user", "content": prompt}]

    kwargs: Dict[str, Any] = {
        "model": model,
        "max_tokens": 2048,
        "system": system_msg,
        "messages": messages,
    }

    # Always provide tools so the model knows about them, but for
    # discovery / error interpretation we tell it not to force a tool call.
    if category in ("tool_selection", "parameter_correctness"):
        kwargs["tools"] = tools
        kwargs["tool_choice"] = {"type": "any"}
    else:
        # Discovery and error interpretation -- include tools for context
        # but let the model respond with text.
        kwargs["tools"] = tools
        kwargs["tool_choice"] = {"type": "auto"}

    try:
        response = await client.messages.create(**kwargs)
        return {
            "success": True,
            "response": response,
            "model": model,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "model": model,
        }


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def evaluate_discovery(
    response_data: Dict[str, Any],
    expected_tools: List[str],
) -> Dict[str, Any]:
    """Evaluate a discovery response for tool recall."""
    if not response_data.get("success"):
        return {
            "correct": False,
            "recall": 0.0,
            "found_tools": [],
            "missing_tools": expected_tools,
            "error": response_data.get("error"),
        }

    response = response_data["response"]
    # Extract text from the response
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text
        elif hasattr(block, "name"):
            text += block.name

    text_lower = text.lower()

    found = []
    missing = []
    for tool_name in expected_tools:
        # Check both exact name and underscore-to-space variants
        variants = [
            tool_name.lower(),
            tool_name.replace("_", " ").lower(),
            tool_name.replace("_", "-").lower(),
        ]
        if any(v in text_lower for v in variants):
            found.append(tool_name)
        else:
            missing.append(tool_name)

    recall = len(found) / len(expected_tools) if expected_tools else 1.0

    return {
        "correct": recall >= 0.8,
        "recall": round(recall, 4),
        "found_tools": found,
        "missing_tools": missing,
    }


def evaluate_tool_selection(
    response_data: Dict[str, Any],
    expected_tool: str,
) -> Dict[str, Any]:
    """Evaluate whether the model selected the correct tool."""
    if not response_data.get("success"):
        return {
            "correct": False,
            "selected_tool": None,
            "expected_tool": expected_tool,
            "error": response_data.get("error"),
        }

    response = response_data["response"]
    selected_tool = None

    for block in response.content:
        if hasattr(block, "type") and block.type == "tool_use":
            selected_tool = block.name
            break

    # Also check text content in case the model mentioned the tool name
    if selected_tool is None:
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        # Try to find the expected tool name in text
        if expected_tool in text:
            selected_tool = expected_tool

    correct = selected_tool == expected_tool

    return {
        "correct": correct,
        "selected_tool": selected_tool,
        "expected_tool": expected_tool,
    }


def evaluate_parameter_correctness(
    response_data: Dict[str, Any],
    expected_tool: str,
    expected_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate parameter correctness from a tool_use block."""
    if not response_data.get("success"):
        return {
            "correct": False,
            "tool_correct": False,
            "field_results": {},
            "per_field_accuracy": 0.0,
            "error": response_data.get("error"),
        }

    response = response_data["response"]
    tool_use_block = None

    for block in response.content:
        if hasattr(block, "type") and block.type == "tool_use":
            tool_use_block = block
            break

    if tool_use_block is None:
        return {
            "correct": False,
            "tool_correct": False,
            "field_results": {},
            "per_field_accuracy": 0.0,
            "error": "No tool_use block found in response",
        }

    tool_correct = tool_use_block.name == expected_tool
    actual_params = tool_use_block.input if hasattr(tool_use_block, "input") else {}

    field_results: Dict[str, bool] = {}
    for key, expected_value in expected_params.items():
        actual_value = actual_params.get(key)
        if isinstance(expected_value, list):
            # For lists, check if all expected items are present
            if isinstance(actual_value, list):
                field_results[key] = set(str(x) for x in expected_value) == set(str(x) for x in actual_value)
            else:
                field_results[key] = False
        elif isinstance(expected_value, bool):
            # Bool check must precede int/float because bool is a subclass of int
            field_results[key] = bool(actual_value) == expected_value
        elif isinstance(expected_value, (int, float)):
            # Numeric comparison with tolerance
            try:
                field_results[key] = abs(float(actual_value) - float(expected_value)) < 0.01
            except (TypeError, ValueError):
                field_results[key] = False
        else:
            field_results[key] = str(actual_value).strip() == str(expected_value).strip()

    total_fields = len(field_results)
    correct_fields = sum(1 for v in field_results.values() if v)
    per_field_accuracy = correct_fields / total_fields if total_fields > 0 else 1.0

    return {
        "correct": tool_correct and per_field_accuracy == 1.0,
        "tool_correct": tool_correct,
        "selected_tool": tool_use_block.name,
        "expected_tool": expected_tool,
        "actual_params": actual_params,
        "expected_params": expected_params,
        "field_results": field_results,
        "per_field_accuracy": round(per_field_accuracy, 4),
    }


def evaluate_error_interpretation(
    response_data: Dict[str, Any],
    expected_error_class: str,
) -> Dict[str, Any]:
    """Evaluate whether the model correctly identified the error class."""
    if not response_data.get("success"):
        return {
            "correct": False,
            "identified_class": None,
            "expected_class": expected_error_class,
            "error": response_data.get("error"),
        }

    response = response_data["response"]
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    text_lower = text.lower().strip()

    # The valid error classes -- ordered longest-first to avoid substring
    # collisions (e.g. "invalid_input" should not match "invalid" inside
    # "illegal_address" context).
    valid_classes = [
        "endpoint_unavailable", "illegal_address", "protocol_error",
        "type_mismatch", "guarded_write", "invalid_input", "timeout",
    ]

    # Try to find the identified class in the response.
    # We search for all matches and pick the expected one if present;
    # otherwise fall back to the first match found.
    identified_class = None
    matches_found: List[str] = []

    for cls in valid_classes:
        variants = [cls, cls.replace("_", " "), cls.replace("_", "-")]
        if any(v in text_lower for v in variants):
            matches_found.append(cls)

    if expected_error_class in matches_found:
        identified_class = expected_error_class
    elif matches_found:
        identified_class = matches_found[0]

    correct = identified_class == expected_error_class

    return {
        "correct": correct,
        "identified_class": identified_class,
        "expected_class": expected_error_class,
        "response_text": text[:500],
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def _serialize_response_for_json(result: Dict[str, Any]) -> Dict[str, Any]:
    """Strip non-serializable objects (API response objects) from results."""
    clean = dict(result)
    clean.pop("response", None)  # anthropic response object
    # Recursively clean nested dicts
    for key, value in clean.items():
        if isinstance(value, dict):
            clean[key] = _serialize_response_for_json(value)
    return clean


async def run_assessment_for_model(
    client: Any,
    model: str,
    tools: List[Dict[str, Any]],
    corpus: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run the full 45-prompt assessment for a single model."""
    discovery_results: List[Dict[str, Any]] = []
    tool_selection_results: List[Dict[str, Any]] = []
    parameter_results: List[Dict[str, Any]] = []
    error_results: List[Dict[str, Any]] = []

    total = len(corpus)
    for idx, entry in enumerate(corpus):
        prompt_id = entry["id"]
        category = entry["category"]
        prompt = entry["prompt"]

        print(f"  [{model}] ({idx + 1}/{total}) {prompt_id}: {category}...")

        # Rate-limit: brief pause between calls to avoid hitting API limits
        if idx > 0:
            await asyncio.sleep(0.5)

        response_data = await call_claude(client, model, prompt, tools, category)

        if category == "discovery":
            evaluation = evaluate_discovery(response_data, entry["expected_tools"])
            evaluation["prompt_id"] = prompt_id
            evaluation["prompt"] = prompt
            discovery_results.append(evaluation)

        elif category == "tool_selection":
            evaluation = evaluate_tool_selection(response_data, entry["expected_tool"])
            evaluation["prompt_id"] = prompt_id
            evaluation["prompt"] = prompt
            tool_selection_results.append(evaluation)

        elif category == "parameter_correctness":
            evaluation = evaluate_parameter_correctness(
                response_data, entry["expected_tool"], entry["expected_params"]
            )
            evaluation["prompt_id"] = prompt_id
            evaluation["prompt"] = prompt
            parameter_results.append(evaluation)

        elif category == "error_interpretation":
            evaluation = evaluate_error_interpretation(
                response_data, entry["expected_error_class"]
            )
            evaluation["prompt_id"] = prompt_id
            evaluation["prompt"] = prompt
            error_results.append(evaluation)

    # Aggregate metrics
    discovery_recall_values = [r["recall"] for r in discovery_results]
    discovery_recall = (
        round(sum(discovery_recall_values) / len(discovery_recall_values), 4)
        if discovery_recall_values
        else 0.0
    )

    tool_selection_correct = sum(1 for r in tool_selection_results if r["correct"])
    tool_selection_accuracy = (
        round(tool_selection_correct / len(tool_selection_results), 4)
        if tool_selection_results
        else 0.0
    )

    param_correct = sum(1 for r in parameter_results if r["correct"])
    param_accuracy = (
        round(param_correct / len(parameter_results), 4)
        if parameter_results
        else 0.0
    )
    per_field_values = [r["per_field_accuracy"] for r in parameter_results if "per_field_accuracy" in r]
    per_field_accuracy = (
        round(sum(per_field_values) / len(per_field_values), 4)
        if per_field_values
        else 0.0
    )

    error_correct = sum(1 for r in error_results if r["correct"])
    error_accuracy = (
        round(error_correct / len(error_results), 4)
        if error_results
        else 0.0
    )

    return {
        "discovery": {
            "recall": discovery_recall,
            "details": discovery_results,
        },
        "tool_selection": {
            "accuracy": tool_selection_accuracy,
            "details": tool_selection_results,
        },
        "parameter_correctness": {
            "accuracy": param_accuracy,
            "per_field_accuracy": per_field_accuracy,
            "details": parameter_results,
        },
        "error_interpretation": {
            "accuracy": error_accuracy,
            "details": error_results,
        },
    }


async def main() -> None:
    """Run the LLM assessment across all models and write results."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Please set it before running this assessment:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic Python package is not installed.")
        print("  pip install anthropic")
        return

    GENERATED.mkdir(parents=True, exist_ok=True)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    tools = build_all_tools()
    corpus = build_prompt_corpus()

    print(f"IndustriConnect LLM Assessment")
    print(f"  Tools defined: {len(tools)}")
    print(f"  Prompts: {len(corpus)}")
    print(f"  Models: {', '.join(MODELS)}")
    print()

    # Verify tool and prompt counts
    assert len(corpus) == 45, f"Expected 45 prompts, got {len(corpus)}"

    modbus_count = len([t for t in tools if t["name"] in ALL_MODBUS_TOOL_NAMES])
    mqtt_count = len([t for t in tools if t["name"] in ALL_MQTT_TOOL_NAMES])
    opcua_count = len([t for t in tools if t["name"] in ALL_OPCUA_TOOL_NAMES])
    print(f"  Modbus tools: {modbus_count}")
    print(f"  MQTT tools: {mqtt_count}")
    print(f"  OPC UA tools: {opcua_count}")
    print()

    results: Dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool_counts": {
            "modbus": modbus_count,
            "mqtt": mqtt_count,
            "opcua": opcua_count,
            "total": len(tools),
        },
        "prompt_counts": {
            "discovery": len([p for p in corpus if p["category"] == "discovery"]),
            "tool_selection": len([p for p in corpus if p["category"] == "tool_selection"]),
            "parameter_correctness": len([p for p in corpus if p["category"] == "parameter_correctness"]),
            "error_interpretation": len([p for p in corpus if p["category"] == "error_interpretation"]),
            "total": len(corpus),
        },
        "models": {},
    }

    for model in MODELS:
        print(f"Running assessment for {model}...")
        start_time = time.monotonic()

        try:
            model_results = await run_assessment_for_model(client, model, tools, corpus)
            elapsed = round(time.monotonic() - start_time, 1)

            print(f"  Completed in {elapsed}s")
            print(f"    Discovery recall:        {model_results['discovery']['recall']:.1%}")
            print(f"    Tool selection accuracy:  {model_results['tool_selection']['accuracy']:.1%}")
            print(f"    Parameter accuracy:       {model_results['parameter_correctness']['accuracy']:.1%}")
            print(f"    Per-field accuracy:       {model_results['parameter_correctness']['per_field_accuracy']:.1%}")
            print(f"    Error interpretation:     {model_results['error_interpretation']['accuracy']:.1%}")
            print()

            results["models"][model] = model_results

        except Exception as exc:
            print(f"  FAILED: {exc}")
            results["models"][model] = {
                "error": str(exc),
                "discovery": {"recall": 0.0, "details": []},
                "tool_selection": {"accuracy": 0.0, "details": []},
                "parameter_correctness": {"accuracy": 0.0, "per_field_accuracy": 0.0, "details": []},
                "error_interpretation": {"accuracy": 0.0, "details": []},
            }

    # Write output
    output_path = GENERATED / "llm_assessment_results.json"

    # Clean non-serializable objects before writing
    def _clean_for_json(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _clean_for_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean_for_json(item) for item in obj]
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        return str(obj)

    cleaned_results = _clean_for_json(results)
    output_path.write_text(json.dumps(cleaned_results, indent=2), encoding="utf-8")
    print(f"Results written to {output_path}")

    # Print summary table
    print()
    print("=" * 72)
    print(f"{'Metric':<30} ", end="")
    for model in MODELS:
        short = model.split("-")[1]  # "sonnet" or "haiku"
        print(f"  {short:>12}", end="")
    print()
    print("-" * 72)

    metrics = [
        ("Discovery recall", lambda r: r["discovery"]["recall"]),
        ("Tool selection accuracy", lambda r: r["tool_selection"]["accuracy"]),
        ("Parameter accuracy", lambda r: r["parameter_correctness"]["accuracy"]),
        ("Per-field accuracy", lambda r: r["parameter_correctness"]["per_field_accuracy"]),
        ("Error interpretation", lambda r: r["error_interpretation"]["accuracy"]),
    ]

    for label, getter in metrics:
        print(f"{label:<30} ", end="")
        for model in MODELS:
            model_data = results["models"].get(model, {})
            try:
                value = getter(model_data)
                print(f"  {value:>11.1%}", end="")
            except (KeyError, TypeError):
                print(f"  {'N/A':>12}", end="")
        print()
    print("=" * 72)
    print()
    print("Note: Multi-family evaluation (GPT-4, Gemini, etc.) is future work.")


if __name__ == "__main__":
    asyncio.run(main())
