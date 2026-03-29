# IndustriConnect MCP Suite

A collection of Model Context Protocol (MCP) servers and tools for industrial automation protocols. This repo lets AI assistants and other MCP‑compatible clients talk to real (or simulated) PLCs and control systems using familiar protocols like Modbus, MQTT/Sparkplug B, OPC UA, BACnet, DNP3, EtherCAT, EtherNet/IP, PROFIBUS, PROFINET, and Siemens S7 (S7comm).

<img width="1456" height="774" alt="Screenshot 2025-12-08 at 21 32 53" src="https://github.com/user-attachments/assets/de160a10-9def-466c-a679-7c6f08fe91d1" />


All protocol stacks follow the same pattern:

- A Python MCP server that exposes a consistent set of tools over stdio
- A mock device/server that simulates a realistic industrial process for safe local testing
- A shared response envelope: `{ success, data, error, meta }`

The `mcp-manager-ui` project adds a web UI for working with these servers and other MCP backends from a single place.

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

## What Is MCP and Why Here?

The Model Context Protocol (MCP) is a simple, transport‑agnostic way to expose tools and data sources to AI assistants over stdio. In this repository, MCP servers act as protocol‑aware “gateways” between an assistant and industrial systems:

- MCP client (e.g., Claude Desktop, mcp-manager-ui, or another MCP runner)
- ↔ MCP server (e.g., Modbus, OPC UA, S7comm)
- ↔ Industrial device / mock device

This separation keeps:

- **Industrial protocol logic** in focused Python projects
- **Conversation and UX** in clients like Claude or `mcp-manager-ui`

You can safely develop and test flows against mocks before connecting to real PLCs or field devices.

---

## Projects Overview

High‑level summary of each protocol project:

- `MODBUS-Project/`
  - **modbus-python** – Modbus TCP/UDP/RTU client wrapped as an MCP server
  - **modbus-mock-server** – Mock Modbus TCP device with a realistic register map
- `MQTT-Project/`
  - **mqtt-python** – MQTT + Sparkplug B MCP server (publish, subscribe, Sparkplug lifecycle)
  - **mqtt-mock-server** – Mock MQTT broker + Sparkplug edge nodes
- `OPCUA-Project/`
  - **opcua-mcp-server** – OPC UA MCP server (read/write nodes, browse, methods, bulk operations)
  - **opcua-local-server** – Rich mock OPC UA server simulating an industrial plant
- `BACnet-Project/`
  - **bacnet-python** – BACnet/IP MCP server
  - **bacnet-mock-device** – Mock BACnet device for discovery and property access tests
- `DNP3-Project/`
  - **dnp3-python** – DNP3 master MCP server
  - **dnp3-mock-outstation** – Mock DNP3 outstation
- `EtherCAT-Project/`
  - **ethercat-python** – EtherCAT MCP server (PySOEM‑based)
  - **ethercat-mock-slave** – Mock EtherCAT slave for local smoke tests
- `EtherNetIP-Project/`
  - **ethernetip-python** – EtherNet/IP MCP server (Rockwell/AB controllers)
  - **ethernetip-mock-server** – Mock CIP server with representative tags/UDTs
- `PROFIBUS-Project/`
  - **profibus-python** – PROFIBUS DP/PA MCP server
  - **profibus-mock-slave** – Mock PROFIBUS slave
- `PROFINET-Project/`
  - **profinet-python** – PROFINET MCP server
  - **profinet-mock-server** – Mock PROFINET IO device
- `S7comm-Project/`
  - **s7comm-python** – Siemens S7 (S7comm) MCP server using `python-snap7`
  - **s7comm-mock-server** – Mock Siemens PLC for DB/I/O/SZL testing
- `mcp-manager-ui/`
  - React + TypeScript web UI for:
    - Connecting to multiple local/remote MCP servers
    - Chatting with LLMs using those tools
    - Inspecting tool schemas and responses

For details and protocol‑specific examples, open the `README.md` in each project directory.

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

## Quick Start (Example: Modbus)

1. **Start the Modbus mock device**

   ```bash
   cd MODBUS-Project/modbus-mock-server
   uv sync
   uv run modbus-mock-server  # listens on 0.0.0.0:1502
   ```

2. **Run the Modbus MCP server**

   ```bash
   cd ../modbus-python
   export MODBUS_TYPE=tcp
   export MODBUS_HOST=127.0.0.1
   export MODBUS_PORT=1502
   export MODBUS_DEFAULT_SLAVE_ID=1
   uv sync
   uv run modbus-mcp
   ```

3. **Wire it into Claude Desktop (or another MCP client)**

   Example `claude_desktop_config.json` snippet:

   ```json
   {
     "mcpServers": {
       "Modbus MCP (Python)": {
         "command": "uv",
         "args": ["--directory", "/absolute/path/to/MODBUS-Project/modbus-python", "run", "modbus-mcp"],
         "env": {
           "MODBUS_TYPE": "tcp",
           "MODBUS_HOST": "127.0.0.1",
           "MODBUS_PORT": "1502",
           "MODBUS_DEFAULT_SLAVE_ID": "1"
         }
       }
     }
   }
   ```

4. **Ask the assistant to use the tools**

   Once connected, you can say things like:

   - “Read the first 10 holding registers from the mock Modbus device.”
   - “Increase the pump speed setpoint to 60%.”

Replace the paths and environment variables for other protocols; each project’s README contains protocol‑specific examples and configuration.

---

## mcp-manager-ui

The `mcp-manager-ui` project provides a browser UI for:

- Managing MCP backends (including these protocol servers)
- Testing tools interactively
- Running conversations against one or more MCP servers

See `mcp-manager-ui/README.md` for installation and usage instructions.

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

Please open issues or pull requests in the relevant project, following any contribution guidelines in that folder’s README or roadmap.

## 📌 Citation
If you use this work, please cite:

```bibtex
@misc{xavier2026industriconnectmcpadaptersmockfirst,
  title={IndustriConnect: MCP Adapters and Mock-First Evaluation for AI-Assisted Industrial Operations},
  author={Melwin Xavier and Melveena Jolly and Vaisakh M A and Midhun Xavier},
  year={2026},
  eprint={2603.24703},
  archivePrefix={arXiv},
  primaryClass={cs.SE},
  url={https://arxiv.org/abs/2603.24703}
}
