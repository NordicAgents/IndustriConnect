from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP
from opcua import Client
from opcua.ua import NodeClass


SERVER_URL = os.getenv(
    "OPCUA_SERVER_URL",
    "opc.tcp://127.0.0.1:4840/freeopcua/server/",
)
_OPCUA_CLIENT: Optional[Client] = None


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


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(val) for key, val in value.items()}
    return str(value)


def _convert_value(raw_value: Any, current_value: Any) -> Any:
    if isinstance(current_value, bool):
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return int(float(raw_value))
    if isinstance(current_value, float):
        return float(raw_value)
    return raw_value


@asynccontextmanager
async def opcua_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Handle OPC UA client connection lifecycle."""
    global _OPCUA_CLIENT
    client = Client(SERVER_URL)
    try:
        await asyncio.to_thread(client.connect)
        _OPCUA_CLIENT = client
        yield {"opcua_client": client}
    finally:
        _OPCUA_CLIENT = None
        await asyncio.to_thread(client.disconnect)


mcp = FastMCP("OPCUA-Control", lifespan=opcua_lifespan)


def _client() -> Client:
    if _OPCUA_CLIENT is None:
        raise RuntimeError("OPC UA client is not connected")
    return _OPCUA_CLIENT


async def _ensure_connected() -> Client:
    """Return a healthy OPC UA client, reconnecting if the current one is stale."""
    global _OPCUA_CLIENT
    client = _OPCUA_CLIENT
    if client is not None:
        try:
            # Liveness probe: read the ServerStatus node
            server_node = client.get_node("ns=0;i=2259")
            await asyncio.to_thread(server_node.get_value)
            return client
        except Exception:
            # Stale connection — tear it down
            try:
                await asyncio.to_thread(client.disconnect)
            except Exception:
                pass
            _OPCUA_CLIENT = None

    # Create a fresh connection
    new_client = Client(SERVER_URL)
    await asyncio.to_thread(new_client.connect)
    _OPCUA_CLIENT = new_client
    return new_client


@mcp.tool()
async def read_opcua_node(node_id: str) -> Dict[str, Any]:
    """Read the value of a specific OPC UA node."""
    client = await _ensure_connected()
    start = time.perf_counter()
    try:
        node = client.get_node(node_id)
        value = await asyncio.to_thread(node.get_value)
        return _make_result(
            True,
            data={"node_id": node_id, "value": _serialize_value(value)},
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Read failed for {node_id}: {exc}",
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )


@mcp.tool()
async def write_opcua_node(node_id: str, value: Any) -> Dict[str, Any]:
    """Write a value to a specific OPC UA node."""
    client = await _ensure_connected()
    start = time.perf_counter()
    try:
        node = client.get_node(node_id)
        current_value = await asyncio.to_thread(node.get_value)
        converted_value = _convert_value(value, current_value)
        await asyncio.to_thread(node.set_value, converted_value)
        return _make_result(
            True,
            data={"node_id": node_id, "written_value": _serialize_value(converted_value)},
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Write failed for {node_id}: {exc}",
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )


@mcp.tool()
async def browse_opcua_node_children(node_id: str) -> Dict[str, Any]:
    """Browse the children of a specific OPC UA node."""
    client = await _ensure_connected()
    start = time.perf_counter()
    try:
        node = client.get_node(node_id)
        raw_children = await asyncio.to_thread(node.get_children)
        children = []
        for child in raw_children:
            browse_name = await asyncio.to_thread(child.get_browse_name)
            children.append(
                {
                    "node_id": child.nodeid.to_string(),
                    "browse_name": f"{browse_name.NamespaceIndex}:{browse_name.Name}",
                }
            )
        return _make_result(
            True,
            data={"node_id": node_id, "children": children},
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Browse failed for {node_id}: {exc}",
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )


@mcp.tool()
async def call_opcua_method(
    object_node_id: str,
    method_node_id: str,
    arguments: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Call a method on a specific OPC UA object node."""
    client = await _ensure_connected()
    start = time.perf_counter()
    method_args = arguments or []
    try:
        object_node = client.get_node(object_node_id)
        method_node = client.get_node(method_node_id)
        result = await asyncio.to_thread(
            object_node.call_method,
            method_node,
            *method_args,
        )
        return _make_result(
            True,
            data={
                "object_node_id": object_node_id,
                "method_node_id": method_node_id,
                "arguments": [_serialize_value(arg) for arg in method_args],
                "result": _serialize_value(result),
            },
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Method call failed for {method_node_id}: {exc}",
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )


@mcp.tool()
async def read_multiple_opcua_nodes(node_ids: List[str]) -> Dict[str, Any]:
    """Read multiple OPC UA nodes in a single tool call."""
    client = await _ensure_connected()
    start = time.perf_counter()
    results = []
    success = True
    for node_id in node_ids:
        try:
            node = client.get_node(node_id)
            value = await asyncio.to_thread(node.get_value)
            results.append({"node_id": node_id, "value": _serialize_value(value)})
        except Exception as exc:
            success = False
            results.append({"node_id": node_id, "error": str(exc)})
    return _make_result(
        success,
        data={"results": results},
        error=None if success else "One or more node reads failed",
        meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
    )


@mcp.tool()
async def write_multiple_opcua_nodes(nodes_to_write: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Write multiple OPC UA nodes in a single tool call."""
    client = await _ensure_connected()
    start = time.perf_counter()
    results = []
    success = True
    for item in nodes_to_write:
        node_id = item["node_id"]
        raw_value = item["value"]
        try:
            node = client.get_node(node_id)
            current_value = await asyncio.to_thread(node.get_value)
            converted_value = _convert_value(raw_value, current_value)
            await asyncio.to_thread(node.set_value, converted_value)
            results.append({"node_id": node_id, "written_value": _serialize_value(converted_value)})
        except Exception as exc:
            success = False
            results.append({"node_id": node_id, "error": str(exc)})
    return _make_result(
        success,
        data={"results": results},
        error=None if success else "One or more node writes failed",
        meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
    )


def _discover_variables(client: Client) -> List[Dict[str, Any]]:
    variables_info: List[Dict[str, Any]] = []
    objects_node = client.get_objects_node()

    def search_variables(node):  # noqa: ANN001
        try:
            children = node.get_children()
        except Exception:
            return

        for child in children:
            try:
                node_class = child.get_node_class()
                browse_name = child.get_browse_name().Name
            except Exception:
                continue

            if browse_name == "Server":
                continue

            if node_class == NodeClass.Variable:
                try:
                    parent_node = child.get_parent()
                    object_id = parent_node.nodeid.to_string() if parent_node else "N/A"
                except Exception:
                    object_id = "N/A"

                try:
                    value = _serialize_value(child.get_value())
                except Exception:
                    value = None

                try:
                    data_type = child.get_data_type().to_string()
                except Exception:
                    data_type = ""

                variables_info.append(
                    {
                        "name": browse_name,
                        "node_id": child.nodeid.to_string(),
                        "object_id": object_id,
                        "value": value,
                        "data_type": data_type,
                    }
                )
            elif node_class == NodeClass.Object:
                search_variables(child)

    search_variables(objects_node)
    return variables_info


@mcp.tool()
async def get_all_variables() -> Dict[str, Any]:
    """Return the non-server OPC UA variables exposed by the connected endpoint."""
    client = await _ensure_connected()
    start = time.perf_counter()
    try:
        variables_info = await asyncio.to_thread(_discover_variables, client)
        return _make_result(
            True,
            data={"variables": variables_info, "count": len(variables_info)},
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )
    except Exception as exc:
        return _make_result(
            False,
            error=f"Variable discovery failed: {exc}",
            meta={"duration_ms": _duration_ms(start), "server_url": SERVER_URL},
        )


if __name__ == "__main__":
    mcp.run(transport="stdio")
