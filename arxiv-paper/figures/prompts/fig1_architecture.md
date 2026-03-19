# Figure 1 — Architecture Diagram (TikZ)

## Status
**Replaced with inline TikZ** in `main.tex`. The previous `fig1_architecture.png` is no longer
referenced by the paper.

## What the TikZ diagram shows

1. **Top layer** — MCP Client / AI Assistant (Claude Desktop, mcp-manager-ui, custom LLM app)
2. **Bidirectional arrow** — stdio / JSON-RPC 2.0 (MCP)
3. **Middle layer** — IndustriConnect Protocol MCP Server (FastMCP, asyncio, write guards)
4. **Response envelope** — `{success, data, error, meta}` shown as a badge
5. **Protocol fan-out** — three evaluated flagship adapters (Modbus, MQTT/SB, OPC UA) plus
   greyed-out scaffold badges (BACnet, DNP3, EtherCAT, EtherNet/IP, S7comm, ...)
6. **Bottom targets** — Mock Simulator (dashed, offline testing) vs Real PLC/RTU (solid, plant deployment)

## Notes
- The diagram is self-contained LaTeX and requires `tikz` with libraries:
  `positioning`, `arrows.meta`, `fit`, `backgrounds`, `calc`.
- Compiles within the `IEEEtran` class at `\columnwidth`.
