# IndustriConnect MCP Suite

A collection of Model Context Protocol (MCP) servers and tools for industrial automation protocols. This repo lets AI assistants and other MCP‑compatible clients talk to real (or simulated) PLCs and control systems using familiar protocols like Modbus, MQTT/Sparkplug B, OPC UA, BACnet, DNP3, EtherCAT, EtherNet/IP, PROFIBUS, PROFINET, and Siemens S7 (S7comm).

<img width="1456" height="774" alt="Screenshot 2025-12-08 at 21 32 53" src="https://github.com/user-attachments/assets/de160a10-9def-466c-a679-7c6f08fe91d1" />


All protocol stacks follow the same pattern:

- A Python MCP server that exposes a consistent set of tools over stdio
- A mock device/server that simulates a realistic industrial process for safe local testing
- A shared response envelope: `{ success, data, error, meta }`

The `mcp-manager-ui` project adds a web UI for working with these servers and other MCP backends from a single place.

---

## Prerequisites

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| Python | 3.11+ (3.13+ for OPC UA) | Runtime for all MCP servers and mocks | [python.org](https://www.python.org/downloads/) |
| uv | latest | Python package manager — handles deps automatically | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Node.js | 18+ | Only needed for `mcp-manager-ui` web dashboard | [nodejs.org](https://nodejs.org/) |
| Claude Desktop or Claude Code | latest | MCP client to interact with the servers | [claude.ai/download](https://claude.ai/download) |

> **Note:** You do not need to install Python packages manually. Running `uv sync` in any subdirectory installs everything automatically.

---

## Quick Start

Every protocol follows the same three-step pattern: **start a mock → start the MCP server → connect a client**. This example uses Modbus — swap the directory and command for any other protocol (see the [Protocol Quick Reference](#protocol-quick-reference) table below).

**1. Clone the repo**

```bash
git clone https://github.com/yashika-sharma/IndustriConnect-MCPs.git
cd IndustriConnect-MCPs
```

**2. Start a mock device** (Terminal 1)

```bash
cd MODBUS-Project/modbus-mock-server
uv sync
uv run modbus-mock-server        # listens on 0.0.0.0:1502
```

**3. Start the MCP server** (Terminal 2)

```bash
cd MODBUS-Project/modbus-python
uv sync
MODBUS_TYPE=tcp MODBUS_HOST=127.0.0.1 MODBUS_PORT=1502 MODBUS_DEFAULT_SLAVE_ID=1 \
  uv run modbus-mcp
```

**4. Connect a client**

- **Claude Desktop** — add the server to your config ([see below](#use-with-claude-desktop))
- **Claude Code** — the `.mcp.json` at the repo root is auto-discovered ([see below](#use-with-claude-code))

**5. Ask the assistant something**

> "Read the first 10 holding registers from the mock Modbus device."
> "What is the current pump speed setpoint?"

> **Tip:** The same pattern works for all 10 protocols. Check the table below and swap the directory and command.

---

## Protocol Quick Reference

| Protocol | Mock Dir | Mock Command | Port | MCP Dir | MCP Command |
|----------|----------|-------------|------|---------|-------------|
| Modbus | `modbus-mock-server` | `uv run modbus-mock-server` | 1502 | `modbus-python` | `uv run modbus-mcp` |
| MQTT | `mqtt-mock-server` | `uv run mqtt-mock-server` | 1883 | `mqtt-python` | `uv run mqtt-mcp` |
| OPC UA | `opcua-local-server` | `uv run main.py` | 4840 | `opcua-mcp-server` | `uv run opcua-mcp-server.py` |
| BACnet | `bacnet-mock-device` | `uv run bacnet-mock-device` | 7900 | `bacnet-python` | `uv run bacnet-mcp` |
| DNP3 | `dnp3-mock-outstation` | `uv run dnp3-mock-outstation` | 7300 | `dnp3-python` | `uv run dnp3-mcp` |
| EtherCAT | `ethercat-mock-slave` | `uv run ethercat-mock-slave` | 6700 | `ethercat-python` | `uv run ethercat-mcp` |
| EtherNet/IP | `ethernetip-mock-server` | `uv run ethernetip-mock-server` | 5025 | `ethernetip-python` | `uv run ethernetip-mcp` |
| PROFIBUS | `profibus-mock-slave` | `uv run profibus-mock-slave` | 7100 | `profibus-python` | `uv run profibus-mcp` |
| PROFINET | `profinet-mock-server` | `uv run profinet-mock-server` | 5600 | `profinet-python` | `uv run profinet-mcp` |
| S7comm | `s7comm-mock-server` | `uv run s7comm-mock-server` | 1102 | `s7comm-python` | `uv run s7comm-mcp` |

> Run `uv sync` in both the mock and MCP subdirectories before first use. Each project's README has full env var documentation.

---

## Use with Claude Desktop

Add some or all of the servers to your Claude Desktop configuration file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Replace `/absolute/path/to/IndustriConnect-MCPs` with the actual path on your machine. Start the corresponding mock servers before using the tools.

```json
{
  "mcpServers": {
    "Modbus MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/MODBUS-Project/modbus-python", "run", "modbus-mcp"],
      "env": {
        "MODBUS_TYPE": "tcp",
        "MODBUS_HOST": "127.0.0.1",
        "MODBUS_PORT": "1502",
        "MODBUS_DEFAULT_SLAVE_ID": "1"
      }
    },
    "MQTT MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/MQTT-Project/mqtt-python", "run", "mqtt-mcp"],
      "env": {
        "MQTT_BROKER_URL": "mqtt://127.0.0.1:1883",
        "MQTT_CLIENT_ID": "mqtt-mcp-client",
        "SPARKPLUG_GROUP_ID": "factory",
        "SPARKPLUG_EDGE_NODE_ID": "edge-node-1"
      }
    },
    "OPC UA MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/OPCUA-Project/opcua-mcp-server", "run", "opcua-mcp-server.py"],
      "env": {
        "OPCUA_SERVER_URL": "opc.tcp://localhost:4840"
      }
    },
    "BACnet MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/BACnet-Project/bacnet-python", "run", "bacnet-mcp"],
      "env": {
        "BACNET_INTERFACE": "0.0.0.0",
        "BACNET_PORT": "47808"
      }
    },
    "DNP3 MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/DNP3-Project/dnp3-python", "run", "dnp3-mcp"],
      "env": {
        "DNP3_CONNECTION_TYPE": "tcp",
        "DNP3_HOST": "127.0.0.1",
        "DNP3_PORT": "7300"
      }
    },
    "EtherCAT MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/EtherCAT-Project/ethercat-python", "run", "ethercat-mcp"],
      "env": {
        "ETHERCAT_INTERFACE": "eth0"
      }
    },
    "EtherNet/IP MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/EtherNetIP-Project/ethernetip-python", "run", "ethernetip-mcp"],
      "env": {
        "ENIP_HOST": "127.0.0.1",
        "ENIP_PORT": "5025",
        "ENIP_SLOT": "0"
      }
    },
    "PROFIBUS MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/PROFIBUS-Project/profibus-python", "run", "profibus-mcp"],
      "env": {
        "PROFIBUS_MOCK": "true"
      }
    },
    "PROFINET MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/PROFINET-Project/profinet-python", "run", "profinet-mcp"],
      "env": {
        "PROFINET_INTERFACE": "eth0"
      }
    },
    "S7comm MCP": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/IndustriConnect-MCPs/S7comm-Project/s7comm-python", "run", "s7comm-mcp"],
      "env": {
        "S7_HOST": "127.0.0.1",
        "S7_PORT": "1102",
        "S7_RACK": "0",
        "S7_SLOT": "2"
      }
    }
  }
}
```

> **Note:** You only need to include the servers you plan to use. Remove entries for protocols you don't need.

---

## Use with Claude Code

This repo includes a `.mcp.json` file at the root that Claude Code auto-discovers when you open the project. It configures all 10 MCP servers with relative paths so it works out of the box after cloning.

To use it:

1. Start the mock server(s) you need (see [Protocol Quick Reference](#protocol-quick-reference))
2. Open the repo in Claude Code — the MCP servers are detected automatically
3. Start chatting with the protocol tools

The `.mcp.json` uses relative paths via `--directory`, so no path editing is required.

<details>
<summary>View the full .mcp.json configuration</summary>

```json
{
  "mcpServers": {
    "Modbus MCP": {
      "command": "uv",
      "args": ["--directory", "MODBUS-Project/modbus-python", "run", "modbus-mcp"],
      "env": {
        "MODBUS_TYPE": "tcp",
        "MODBUS_HOST": "127.0.0.1",
        "MODBUS_PORT": "1502",
        "MODBUS_DEFAULT_SLAVE_ID": "1"
      }
    },
    "...": "all 10 servers — see .mcp.json at repo root"
  }
}
```

</details>

---

## What Is MCP and Why Here?

The Model Context Protocol (MCP) is a simple, transport‑agnostic way to expose tools and data sources to AI assistants over stdio. In this repository, MCP servers act as protocol‑aware "gateways" between an assistant and industrial systems:

- MCP client (e.g., Claude Desktop, mcp-manager-ui, or another MCP runner)
- ↔ MCP server (e.g., Modbus, OPC UA, S7comm)
- ↔ Industrial device / mock device

This separation keeps:

- **Industrial protocol logic** in focused Python projects
- **Conversation and UX** in clients like Claude or `mcp-manager-ui`

You can safely develop and test flows against mocks before connecting to real PLCs or field devices.

---

## Repository Layout

Top‑level structure:

```text
IndustriConnect-MCPs/
├── BACnet-Project/      # BACnet/IP MCP server + mock device
├── DNP3-Project/        # DNP3 MCP server + mock outstation
├── EtherCAT-Project/    # EtherCAT MCP server + mock slave
├── EtherNetIP-Project/  # EtherNet/IP MCP server + mock PLC
├── MODBUS-Project/      # Modbus MCP server + mock device
├── MQTT-Project/        # MQTT + Sparkplug B MCP server + mock broker
├── OPCUA-Project/       # OPC UA MCP server + local OPC UA server
├── PROFIBUS-Project/    # PROFIBUS DP/PA MCP server + mock slave
├── PROFINET-Project/    # PROFINET MCP server + mock IO device
├── S7comm-Project/      # Siemens S7 MCP server + mock PLC
├── mcp-manager-ui/      # Web UI for managing MCP servers and LLMs
└── whitepaper/          # Architecture and design background
```

Each protocol project has:

- `*-python/` – Python MCP server (`uv` + `mcp[cli]` or FastMCP)
- `*-mock-*` – Mock device or server that simulates a plant/process
- `README.md` – Protocol‑specific docs and quickstart
- `docs/roadmap/...` (referenced from the README) – Implementation plan and deeper notes

> Note: Earlier TypeScript/Node MCP implementations have been removed. The suite is now Python‑first with a consistent layout and tooling across all protocols.

---

## Projects Overview

Each protocol project contains a Python MCP server and a mock device/server. See the [Protocol Quick Reference](#protocol-quick-reference) table for commands and ports. Full details are in each project's `README.md`.

- `mcp-manager-ui/` – React + TypeScript web UI for connecting to multiple MCP servers, chatting with LLMs, and inspecting tool schemas and responses.

---

## Common Design Patterns

Across all protocol servers:

- **Transport**: stdio MCP servers, usually run via `uv run <entrypoint>`
- **Config**: environment variables and optional `.env` files (e.g., host, port, timeouts)
- **Envelope**: tools return a consistent shape:

  ```json
  {
    "success": true,
    "data": { "...": "protocol-specific payload" },
    "error": null,
    "meta": { "latency_ms": 12, "raw": {} }
  }
  ```

- **Mocks first**: every stack ships with a mock device/server so you can:
  - Develop prompts and workflows safely
  - Debug tools without needing access to production hardware
  - Reproduce issues deterministically

---

## mcp-manager-ui

The `mcp-manager-ui` project provides a browser UI for managing MCP backends, testing tools interactively, and running conversations against one or more MCP servers.

```bash
cd mcp-manager-ui
npm install
cd mcp-backend && npm install && cd ..
npm run dev          # starts frontend + backend concurrently
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend WebSocket | ws://localhost:3003 |
| Backend HTTP | http://localhost:3002 |

See `mcp-manager-ui/README.md` for full configuration (LLM API keys, Ollama setup, etc.).

---

## Whitepaper and Architecture

For a deeper dive into the motivation, architecture, and design decisions behind this suite (including security, safety, and roadmap), see:

- `whitepaper/` – high‑level whitepaper for the IndustriConnect MCP suite

---

## Contributing & Roadmap

- Contributions are welcome as:
  - New tools or coverage within an existing protocol
  - Improvements to mocks and test scenarios
  - Documentation updates and examples

Please open issues or pull requests in the relevant project, following any contribution guidelines in that folder's README or roadmap.
