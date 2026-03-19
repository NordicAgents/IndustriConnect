import asyncio
import os
import json
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

from pymodbus.client import (
    AsyncModbusTcpClient,
    AsyncModbusUdpClient,
    AsyncModbusSerialClient,
)
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

from dotenv import load_dotenv

load_dotenv()

# Modbus client configuration from environment variables
MODBUS_TYPE = os.environ.get("MODBUS_TYPE", "tcp").lower()  # tcp, udp, or serial
MODBUS_HOST = os.environ.get("MODBUS_HOST", "127.0.0.1")
MODBUS_PORT = int(os.environ.get("MODBUS_PORT", 502))
MODBUS_SERIAL_PORT = os.environ.get("MODBUS_SERIAL_PORT", "/dev/ttyUSB0")
MODBUS_BAUDRATE = int(os.environ.get("MODBUS_BAUDRATE", 9600))
MODBUS_PARITY = os.environ.get("MODBUS_PARITY", "N")
MODBUS_STOPBITS = int(os.environ.get("MODBUS_STOPBITS", 1))
MODBUS_BYTESIZE = int(os.environ.get("MODBUS_BYTESIZE", 8))
MODBUS_TIMEOUT = float(os.environ.get("MODBUS_TIMEOUT", 1))
MODBUS_DEFAULT_SLAVE_ID = int(os.environ.get("MODBUS_DEFAULT_SLAVE_ID", 1))

# Reliability and safety controls
def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

MODBUS_MAX_RETRIES = int(os.environ.get("MODBUS_MAX_RETRIES", 2))
MODBUS_RETRY_BACKOFF_BASE = float(os.environ.get("MODBUS_RETRY_BACKOFF_BASE", 0.2))  # seconds
MODBUS_TOOL_TIMEOUT = os.environ.get("MODBUS_TOOL_TIMEOUT")
MODBUS_TOOL_TIMEOUT = float(MODBUS_TOOL_TIMEOUT) if MODBUS_TOOL_TIMEOUT else None
MODBUS_WRITES_ENABLED = _env_bool("MODBUS_WRITES_ENABLED", True)

# Optional register tag map
REGISTER_MAP_FILE = os.environ.get("REGISTER_MAP_FILE")
_TAG_MAP: Dict[str, Dict[str, Any]] = {}
if REGISTER_MAP_FILE and os.path.exists(REGISTER_MAP_FILE):
    try:
        with open(REGISTER_MAP_FILE, "r", encoding="utf-8") as f:
            _TAG_MAP = json.load(f)
    except Exception:
        _TAG_MAP = {}

# Application context for dependency injection
@dataclass
class AppContext:
    modbus_client: Union[AsyncModbusTcpClient, AsyncModbusUdpClient, AsyncModbusSerialClient]


# -----------------------------
# Helpers
# -----------------------------

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


async def _with_timeout(coro: Awaitable[Any], timeout: Optional[float]) -> Any:
    if timeout is None or timeout <= 0:
        return await coro
    return await asyncio.wait_for(coro, timeout=timeout)


async def _retry_call(
    ctx: Context,
    op: str,
    call_factory: Callable[[], Awaitable[Any]],
    max_retries: int,
    timeout: Optional[float],
) -> Tuple[Optional[Any], Optional[str], float, int]:
    """Execute call with retries and timeout. Returns (result, error, duration, attempts)."""
    attempt = 0
    start = time.perf_counter()
    last_err: Optional[str] = None
    while True:
        try:
            attempt += 1
            result = await _with_timeout(call_factory(), timeout)
            return result, None, (time.perf_counter() - start) * 1000.0, attempt
        except (ModbusException, asyncio.TimeoutError) as e:
            last_err = f"{type(e).__name__}: {str(e)}"
            await ctx.error(f"{op} failed on attempt {attempt}: {last_err}")
            if attempt > max_retries:
                break
            backoff = MODBUS_RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)
        except Exception as e:  # unexpected
            last_err = f"Unexpected {type(e).__name__}: {str(e)}"
            await ctx.error(f"{op} unexpected error on attempt {attempt}: {last_err}")
            break
    return None, last_err, (time.perf_counter() - start) * 1000.0, attempt


async def _chunked_read(
    ctx: Context,
    label: str,
    read_func: Callable[[int, int], Awaitable[Any]],
    start_address: int,
    total_count: int,
    per_request_limit: int,
    attr: str,
    timeout: Optional[float],
) -> Tuple[Optional[List[Any]], Optional[str], Dict[str, Any]]:
    """Generic chunked reader for registers/coils.

    - read_func: async function(start, size) -> response
    - attr: response attribute to extract ("registers" or "bits")
    """
    if total_count <= 0:
        return None, "Count must be positive", {}

    values: List[Any] = []
    chunks: List[Dict[str, Any]] = []
    remaining = total_count
    current = start_address
    while remaining > 0:
        size = min(remaining, per_request_limit)
        op = f"{label}[{current}:{current+size-1}]"

        async def _call() -> Any:
            return await read_func(current, size)

        result, err, duration_ms, attempts = await _retry_call(
            ctx, op, _call, MODBUS_MAX_RETRIES, timeout
        )
        if err is not None:
            return None, err, {"partial": values, "chunks": chunks}
        # pymodbus response
        if hasattr(result, "isError") and result.isError():
            return None, f"Device error: {result}", {"partial": values, "chunks": chunks}
        chunk_vals = getattr(result, attr, None)
        if chunk_vals is None:
            return None, "Malformed response", {"partial": values, "chunks": chunks}
        # trim to the requested size, some backends over-return
        values.extend(list(chunk_vals)[:size])
        chunks.append(
            {
                "address": current,
                "count": size,
                "duration_ms": round(duration_ms, 3),
                "attempts": attempts,
            }
        )
        current += size
        remaining -= size
    return values, None, {"chunks": chunks}


# Typed decode/encode utilities
_DTYPE_SIZES = {
    "int16": 1,
    "uint16": 1,
    "int32": 2,
    "uint32": 2,
    "float32": 2,
    "int64": 4,
    "uint64": 4,
    "float64": 4,
}


def _to_endian(v: str) -> Endian:
    return Endian.Big if str(v).lower() in {"b", "big", ">"} else Endian.Little


def _decode_values(
    registers: List[int],
    dtype: str,
    count: int,
    byteorder: str,
    wordorder: str,
) -> List[Any]:
    size = _DTYPE_SIZES.get(dtype)
    if not size:
        raise ValueError(f"Unsupported dtype: {dtype}")
    expected_regs = size * count
    if len(registers) < expected_regs:
        raise ValueError(
            f"Insufficient registers: have {len(registers)}, need {expected_regs} for {count} {dtype}"
        )
    dec = BinaryPayloadDecoder.fromRegisters(
        registers[:expected_regs], byteorder=_to_endian(byteorder), wordorder=_to_endian(wordorder)
    )
    vals: List[Any] = []
    for _ in range(count):
        if dtype == "int16":
            vals.append(dec.decode_16bit_int())
        elif dtype == "uint16":
            vals.append(dec.decode_16bit_uint())
        elif dtype == "int32":
            vals.append(dec.decode_32bit_int())
        elif dtype == "uint32":
            vals.append(dec.decode_32bit_uint())
        elif dtype == "float32":
            vals.append(dec.decode_32bit_float())
        elif dtype == "int64":
            vals.append(dec.decode_64bit_int())
        elif dtype == "uint64":
            vals.append(dec.decode_64bit_uint())
        elif dtype == "float64":
            vals.append(dec.decode_64bit_float())
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")
    return vals


def _encode_values(values: List[Any], dtype: str, byteorder: str, wordorder: str) -> List[int]:
    b = BinaryPayloadBuilder(byteorder=_to_endian(byteorder), wordorder=_to_endian(wordorder))
    for v in values:
        if dtype == "int16":
            b.add_16bit_int(int(v))
        elif dtype == "uint16":
            b.add_16bit_uint(int(v))
        elif dtype == "int32":
            b.add_32bit_int(int(v))
        elif dtype == "uint32":
            b.add_32bit_uint(int(v))
        elif dtype == "float32":
            b.add_32bit_float(float(v))
        elif dtype == "int64":
            b.add_64bit_int(int(v))
        elif dtype == "uint64":
            b.add_64bit_uint(int(v))
        elif dtype == "float64":
            b.add_64bit_float(float(v))
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")
    return b.to_registers()

# Lifespan manager for Modbus client
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage Modbus client lifecycle."""
    # Initialize Modbus client based on MODBUS_TYPE
    if MODBUS_TYPE == "tcp":
        client = AsyncModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    elif MODBUS_TYPE == "udp":
        client = AsyncModbusUdpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    elif MODBUS_TYPE == "serial":
        client = AsyncModbusSerialClient(
            port=MODBUS_SERIAL_PORT,
            baudrate=MODBUS_BAUDRATE,
            parity=MODBUS_PARITY,
            stopbits=MODBUS_STOPBITS,
            bytesize=MODBUS_BYTESIZE,
            timeout=MODBUS_TIMEOUT
        )
    else:
        raise ValueError(f"Invalid MODBUS_TYPE: {MODBUS_TYPE}. Must be 'tcp', 'udp', or 'serial'.")

    # Connect to the Modbus device
    await client.connect()
    if not getattr(client, "connected", False):
        raise RuntimeError(f"Failed to connect to Modbus {MODBUS_TYPE} device")

    try:
        yield AppContext(modbus_client=client)
    finally:
        # Cleanup
        client.close()

# Initialize MCP server
mcp = FastMCP(
    name="Modbus MCP Server",
    dependencies=["pymodbus"],
    lifespan=app_lifespan
)

# Tools: Read and write Modbus registers
@mcp.tool()
async def read_register(address: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]: 
    """
    Read a single Modbus holding register.
    Parameters:
        address (int): The starting address of the holding register (0-65535).
        slave_id (int): The Modbus slave ID (device ID).(2025/05/12)
    Returns:
        str: The value of the register or an error message.
    """
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"read_register addr={address} slave={slave_id}"
    async def _call():
        return await client.read_holding_registers(address=address, count=1, slave=slave_id)
    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"address": address, "slave_id": slave_id})
    value = result.registers[0]
    await ctx.info(f"Read register {address} from slave {slave_id}: {value}")
    return _make_result(True, data={"value": value}, meta={"address": address, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})

@mcp.tool()
async def write_register(address: int, value: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Write a value to a Modbus holding register.

    Parameters:
        address (int): The address of the holding register (0-65535).
        value (int): The value to write (0-65535).
        slave_id (int): The Modbus slave ID (device ID).

    Returns:
        str: Success message or an error message.
    """
    if not MODBUS_WRITES_ENABLED:
        return _make_result(False, error="Writes are disabled by configuration", meta={"address": address, "slave_id": slave_id})
    if not (0 <= value <= 65535):
        return _make_result(False, error=f"Value {value} out of uint16 range (0-65535)", meta={"address": address, "value": value})
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"write_register addr={address} value={value} slave={slave_id}"
    async def _call():
        return await client.write_register(address=address, value=value, slave=slave_id)
    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "value": value, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"address": address, "value": value, "slave_id": slave_id})
    await ctx.info(f"Wrote {value} to register {address} on slave {slave_id}")
    return _make_result(True, data={"written": value}, meta={"address": address, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})

# Tools: Coil operations
@mcp.tool()
async def read_coils(address: int, count: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Read the status of multiple Modbus coils.

    Parameters:
        address (int): The starting address of the coils (0-65535).
        count (int): The number of coils to read (1-2000).
        slave_id (int): The Modbus slave ID (device ID).

    Returns:
        str: A list of coil states (True/False) or an error message.
    """
    client = ctx.request_context.lifespan_context.modbus_client
    values, err, meta = await _chunked_read(
        ctx,
        "read_coils",
        lambda start, size: client.read_coils(address=start, count=size, slave=slave_id),
        address,
        count,
        2000,
        "bits",
        MODBUS_TOOL_TIMEOUT,
    )
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": count, "slave_id": slave_id, **meta})
    await ctx.info(f"Read {count} coils starting at {address} from slave {slave_id}")
    return _make_result(True, data={"values": values}, meta={"address": address, "count": count, "slave_id": slave_id, **meta})

@mcp.tool()
async def write_coil(address: int, value: bool, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Write a value to a single Modbus coil.

    Parameters:
        address (int): The address of the coil (0-65535).
        value (bool): The value to write (True for ON, False for OFF).
        slave_id (int): The Modbus slave ID (device ID).

    Returns:
        str: Success message or an error message.
    """
    if not MODBUS_WRITES_ENABLED:
        return _make_result(False, error="Writes are disabled by configuration", meta={"address": address, "slave_id": slave_id})
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"write_coil addr={address} value={value} slave={slave_id}"
    async def _call():
        return await client.write_coil(address=address, value=value, slave=slave_id)
    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "value": value, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"address": address, "value": value, "slave_id": slave_id})
    await ctx.info(f"Wrote {value} to coil {address} on slave {slave_id}")
    return _make_result(True, data={"written": value}, meta={"address": address, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})

# Tools: Input registers
@mcp.tool()
async def read_input_registers(address: int, count: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Read multiple Modbus input registers.

    Parameters:
        address (int): The starting address of the input registers (0-65535).
        count (int): The number of registers to read (1-125).
        slave_id (int): The Modbus slave ID (device ID).

    Returns:
        str: A list of register values or an error message.
    """
    client = ctx.request_context.lifespan_context.modbus_client
    values, err, meta = await _chunked_read(
        ctx,
        "read_input_registers",
        lambda start, size: client.read_input_registers(address=start, count=size, slave=slave_id),
        address,
        count,
        125,
        "registers",
        MODBUS_TOOL_TIMEOUT,
    )
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": count, "slave_id": slave_id, **meta})
    await ctx.info(f"Read {count} input registers starting at {address} from slave {slave_id}")
    return _make_result(True, data={"registers": values}, meta={"address": address, "count": count, "slave_id": slave_id, **meta})

# Tools: Read multiple holding registers
@mcp.tool()
async def read_multiple_holding_registers(address: int, count: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Read multiple Modbus holding registers.

    Parameters:
        address (int): The starting address of the holding registers (0-65535).
        count (int): The number of registers to read (1-125).
        slave_id (int): The Modbus slave ID (device ID).

    Returns:
        str: A list of register values or an error message.
    """
    client = ctx.request_context.lifespan_context.modbus_client
    values, err, meta = await _chunked_read(
        ctx,
        "read_holding_registers",
        lambda start, size: client.read_holding_registers(address=start, count=size, slave=slave_id),
        address,
        count,
        125,
        "registers",
        MODBUS_TOOL_TIMEOUT,
    )
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": count, "slave_id": slave_id, **meta})
    await ctx.info(f"Read {count} holding registers starting at {address} from slave {slave_id}")
    return _make_result(True, data={"registers": values}, meta={"address": address, "count": count, "slave_id": slave_id, **meta})

# Prompts: Templates for Modbus interactions
@mcp.prompt()
def analyze_register(value: str) -> List[base.Message]:
    """Prompt to analyze a Modbus register value."""
    return [
        base.UserMessage(f"I read this value from a Modbus register: {value}"),
        base.UserMessage("Can you help me understand what it means?"),
        base.AssistantMessage("I'll help analyze the register value. Please provide any context about the device or system.")
    ]

def main() -> None:
    """Run the MCP server."""
    mcp.run()

# -----------------------------
# Additional protocol coverage tools
# -----------------------------

@mcp.tool()
async def read_discrete_inputs(address: int, count: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Read multiple Modbus discrete inputs (function 2).

    Parameters:
        address (int): Starting address (0-65535)
        count (int): Number of inputs to read (1+)
        slave_id (int): Device ID
    """
    client = ctx.request_context.lifespan_context.modbus_client
    values, err, meta = await _chunked_read(
        ctx,
        "read_discrete_inputs",
        lambda start, size: client.read_discrete_inputs(address=start, count=size, slave=slave_id),
        address,
        count,
        2000,
        "bits",
        MODBUS_TOOL_TIMEOUT,
    )
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": count, "slave_id": slave_id, **meta})
    await ctx.info(f"Read {count} discrete inputs starting at {address} from slave {slave_id}")
    return _make_result(True, data={"values": values}, meta={"address": address, "count": count, "slave_id": slave_id, **meta})


@mcp.tool()
async def write_registers(address: int, values: List[int], ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Write multiple holding registers (function 16).

    Parameters:
        address (int): Starting address
        values (List[int]): Register values
        slave_id (int): Device ID
    """
    if not MODBUS_WRITES_ENABLED:
        return _make_result(False, error="Writes are disabled by configuration", meta={"address": address, "slave_id": slave_id})
    if not values:
        return _make_result(False, error="Values list must not be empty")
    for i, v in enumerate(values):
        if not (0 <= v <= 65535):
            return _make_result(False, error=f"Value {v} at index {i} out of uint16 range (0-65535)", meta={"address": address, "index": i, "value": v})
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"write_registers addr={address} n={len(values)} slave={slave_id}"
    async def _call():
        return await client.write_registers(address=address, values=values, slave=slave_id)
    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": len(values), "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"address": address, "count": len(values), "slave_id": slave_id})
    await ctx.info(f"Wrote {len(values)} registers starting at {address} on slave {slave_id}")
    return _make_result(True, data={"written": len(values)}, meta={"address": address, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})


@mcp.tool()
async def write_coils_bulk(address: int, values: List[bool], ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Write multiple coils (function 15).
    """
    if not MODBUS_WRITES_ENABLED:
        return _make_result(False, error="Writes are disabled by configuration", meta={"address": address, "slave_id": slave_id})
    if not values:
        return _make_result(False, error="Values list must not be empty")
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"write_coils addr={address} n={len(values)} slave={slave_id}"
    async def _call():
        return await client.write_coils(address=address, values=values, slave=slave_id)
    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": len(values), "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"address": address, "count": len(values), "slave_id": slave_id})
    await ctx.info(f"Wrote {len(values)} coils starting at {address} on slave {slave_id}")
    return _make_result(True, data={"written": len(values)}, meta={"address": address, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})


@mcp.tool()
async def mask_write_register(address: int, and_mask: int, or_mask: int, ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID) -> Dict[str, Any]:
    """
    Mask write register (function 22): (register = (register & and_mask) | (or_mask & ~and_mask)).
    """
    if not MODBUS_WRITES_ENABLED:
        return _make_result(False, error="Writes are disabled by configuration", meta={"address": address, "slave_id": slave_id})
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"mask_write_register addr={address} and={and_mask} or={or_mask} slave={slave_id}"
    async def _call():
        return await client.mask_write_register(address=address, and_mask=and_mask, or_mask=or_mask, slave=slave_id)
    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "and_mask": and_mask, "or_mask": or_mask, "slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"address": address, "and_mask": and_mask, "or_mask": or_mask, "slave_id": slave_id})
    await ctx.info(f"Mask write register {address} on slave {slave_id}")
    return _make_result(True, data={"address": address, "and_mask": and_mask, "or_mask": or_mask}, meta={"slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})


@mcp.tool()
async def read_device_information(ctx: Context, slave_id: int = MODBUS_DEFAULT_SLAVE_ID, read_code: int = 0x03, object_id: int = 0x00) -> Dict[str, Any]:
    """
    Read device information (MEI type 0x2B/0x0E). read_code: 0x01=basic, 0x02=regular, 0x03=extended.
    """
    client = ctx.request_context.lifespan_context.modbus_client
    op = f"read_device_information slave={slave_id} code={read_code} obj={object_id}"

    async def _call():
        # Try both possible method names across pymodbus versions
        if hasattr(client, "read_device_information"):
            return await client.read_device_information(slave=slave_id, read_code=read_code, object_id=object_id)
        elif hasattr(client, "read_device_identification"):
            return await client.read_device_identification(slave=slave_id, read_code=read_code, object_id=object_id)
        else:
            raise AttributeError("Client does not support device information")

    result, err, duration_ms, attempts = await _retry_call(ctx, op, _call, MODBUS_MAX_RETRIES, MODBUS_TOOL_TIMEOUT)
    if err is not None:
        return _make_result(False, error=err, meta={"slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})
    if hasattr(result, "isError") and result.isError():
        return _make_result(False, error=str(result), meta={"slave_id": slave_id})

    # Attempt to normalize fields
    data: Dict[str, Any] = {}
    for attr in ("information", "informations", "items", "values"):
        v = getattr(result, attr, None)
        if v:
            data = dict(v)
            break
    return _make_result(True, data=data, meta={"slave_id": slave_id, "duration_ms": round(duration_ms, 3), "attempts": attempts})


# -----------------------------
# Typed read helpers/tools
# -----------------------------

@mcp.tool()
async def read_holding_typed(
    address: int,
    dtype: str,
    ctx: Context,
    count: int = 1,
    byteorder: str = "big",
    wordorder: str = "big",
    scale: float = 1.0,
    offset: float = 0.0,
    slave_id: int = MODBUS_DEFAULT_SLAVE_ID,
) -> Dict[str, Any]:
    """
    Read holding registers and decode as typed values.
    """
    size = _DTYPE_SIZES.get(dtype)
    if not size:
        return _make_result(False, error=f"Unsupported dtype: {dtype}")
    total = size * max(count, 1)
    client = ctx.request_context.lifespan_context.modbus_client
    regs, err, meta = await _chunked_read(
        ctx,
        "read_holding_registers",
        lambda start, sz: client.read_holding_registers(address=start, count=sz, slave=slave_id),
        address,
        total,
        125,
        "registers",
        MODBUS_TOOL_TIMEOUT,
    )
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": count, "dtype": dtype, "slave_id": slave_id, **meta})
    try:
        vals = _decode_values(regs, dtype, count, byteorder, wordorder)
        vals = [v * float(scale) + float(offset) for v in vals]
    except Exception as e:
        return _make_result(False, error=str(e), meta={"address": address, "count": count, "dtype": dtype, "slave_id": slave_id})
    return _make_result(True, data={"values": vals}, meta={"address": address, "count": count, "dtype": dtype, "byteorder": byteorder, "wordorder": wordorder, "scale": scale, "offset": offset, "slave_id": slave_id, **meta})


@mcp.tool()
async def read_input_typed(
    address: int,
    dtype: str,
    ctx: Context,
    count: int = 1,
    byteorder: str = "big",
    wordorder: str = "big",
    scale: float = 1.0,
    offset: float = 0.0,
    slave_id: int = MODBUS_DEFAULT_SLAVE_ID,
) -> Dict[str, Any]:
    """
    Read input registers and decode as typed values.
    """
    size = _DTYPE_SIZES.get(dtype)
    if not size:
        return _make_result(False, error=f"Unsupported dtype: {dtype}")
    total = size * max(count, 1)
    client = ctx.request_context.lifespan_context.modbus_client
    regs, err, meta = await _chunked_read(
        ctx,
        "read_input_registers",
        lambda start, sz: client.read_input_registers(address=start, count=sz, slave=slave_id),
        address,
        total,
        125,
        "registers",
        MODBUS_TOOL_TIMEOUT,
    )
    if err is not None:
        return _make_result(False, error=err, meta={"address": address, "count": count, "dtype": dtype, "slave_id": slave_id, **meta})
    try:
        vals = _decode_values(regs, dtype, count, byteorder, wordorder)
        vals = [v * float(scale) + float(offset) for v in vals]
    except Exception as e:
        return _make_result(False, error=str(e), meta={"address": address, "count": count, "dtype": dtype, "slave_id": slave_id})
    return _make_result(True, data={"values": vals}, meta={"address": address, "count": count, "dtype": dtype, "byteorder": byteorder, "wordorder": wordorder, "scale": scale, "offset": offset, "slave_id": slave_id, **meta})


# -----------------------------
# Tag map tools
# -----------------------------

def _normalize_table(val: str) -> str:
    v = str(val).lower()
    if v in {"holding", "hr", "register", "holding_register"}:
        return "holding"
    if v in {"input", "ir", "input_register", "inputs"}:
        return "input"
    if v in {"coil", "coils"}:
        return "coil"
    if v in {"discrete", "di", "discrete_input", "discrete_inputs"}:
        return "discrete"
    return v


@mcp.tool()
async def list_tags(ctx: Context) -> Dict[str, Any]:
    """List available tags from the register map file."""
    if not _TAG_MAP:
        return _make_result(True, data={"tags": []})
    tags = []
    for name, spec in sorted(_TAG_MAP.items()):
        tags.append({"name": name, **spec})
    return _make_result(True, data={"tags": tags})


@mcp.tool()
async def read_tag(name: str, ctx: Context) -> Dict[str, Any]:
    """Read a value using the configured tag map (REGISTER_MAP_FILE)."""
    spec = _TAG_MAP.get(name)
    if not spec:
        return _make_result(False, error=f"Unknown tag: {name}")
    table = _normalize_table(spec.get("table", "holding"))
    addr = int(spec.get("address", 0))
    count = int(spec.get("count", 1))
    slave_id = int(spec.get("slave_id", MODBUS_DEFAULT_SLAVE_ID))
    dtype = spec.get("dtype")
    byteorder = spec.get("byteorder", "big")
    wordorder = spec.get("wordorder", "big")
    scale = float(spec.get("scale", 1.0))
    offset = float(spec.get("offset", 0.0))
    if table in {"holding", "input"} and dtype:
        if table == "holding":
            return await read_holding_typed(addr, dtype, ctx, count=count, byteorder=byteorder, wordorder=wordorder, scale=scale, offset=offset, slave_id=slave_id)
        else:
            return await read_input_typed(addr, dtype, ctx, count=count, byteorder=byteorder, wordorder=wordorder, scale=scale, offset=offset, slave_id=slave_id)
    # Fallback to raw reads
    if table == "holding":
        return await read_multiple_holding_registers(addr, count, ctx, slave_id)
    if table == "input":
        return await read_input_registers(addr, count, ctx, slave_id)
    if table == "coil":
        return await read_coils(addr, count, ctx, slave_id)
    if table == "discrete":
        return await read_discrete_inputs(addr, count, ctx, slave_id)
    return _make_result(False, error=f"Unsupported table: {table}")


@mcp.tool()
async def write_tag(
    name: str,
    value: Any,
    ctx: Context,
) -> Dict[str, Any]:
    """Write a value using the configured tag map. Only holding regs and coils are writable."""
    if not MODBUS_WRITES_ENABLED:
        return _make_result(False, error="Writes are disabled by configuration")
    spec = _TAG_MAP.get(name)
    if not spec:
        return _make_result(False, error=f"Unknown tag: {name}")
    table = _normalize_table(spec.get("table", "holding"))
    addr = int(spec.get("address", 0))
    slave_id = int(spec.get("slave_id", MODBUS_DEFAULT_SLAVE_ID))
    if table == "coil":
        return await write_coil(addr, bool(value), ctx, slave_id)
    if table == "holding":
        dtype = spec.get("dtype", "uint16")
        byteorder = spec.get("byteorder", "big")
        wordorder = spec.get("wordorder", "big")
        # value could be scalar or list
        vals = value if isinstance(value, list) else [value]
        if dtype == "uint16":
            for i, v in enumerate(vals):
                if not (0 <= int(v) <= 65535):
                    return _make_result(False, error=f"Value {v} at index {i} out of uint16 range (0-65535)", meta={"tag": name, "index": i, "value": v})
        try:
            regs = _encode_values(vals, dtype, byteorder, wordorder)
        except Exception as e:
            return _make_result(False, error=str(e))
        return await write_registers(addr, regs, ctx, slave_id)
    return _make_result(False, error=f"Unsupported/writable table for tag '{name}': {table}")


# -----------------------------
# Health
# -----------------------------

@mcp.tool()
async def ping(ctx: Context) -> Dict[str, Any]:
    """Return server health and connection status."""
    client = ctx.request_context.lifespan_context.modbus_client
    status = {
        "connected": bool(getattr(client, "connected", False)),
        "type": MODBUS_TYPE,
        "host": MODBUS_HOST if MODBUS_TYPE in {"tcp", "udp"} else None,
        "port": MODBUS_PORT if MODBUS_TYPE in {"tcp", "udp"} else None,
        "serial_port": MODBUS_SERIAL_PORT if MODBUS_TYPE == "serial" else None,
        "writes_enabled": MODBUS_WRITES_ENABLED,
        "max_retries": MODBUS_MAX_RETRIES,
        "tool_timeout": MODBUS_TOOL_TIMEOUT,
        "tag_count": len(_TAG_MAP) if _TAG_MAP else 0,
    }
    return _make_result(True, data=status)
