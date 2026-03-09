# Figure 1 — Three-Layer Architecture Diagram

## Purpose
System architecture overview for the IndustriConnect MCP suite.
Used in Section 3.1 of the paper.

## Final filename
`../fig1_architecture.png`  (place in `arxiv-paper/figures/`)

---

## AI Image Generation Prompt

Create a clean, professional **technical architecture diagram** with three horizontal layers connected by arrows, suitable for an academic paper figure. The style should be modern infographic / technical documentation — crisp, minimal, white background, readable at 90% column width (~14 cm).

### Layout (top to bottom)

**LAYER 1 — Top box (blue/indigo, rounded corners):**
Label: `MCP Client / AI Assistant`
Sub-label (smaller text): `Claude Desktop  ·  mcp-manager-ui  ·  Custom LLM Application`
Icon: a stylised chat bubble with a robot/AI face OR a circuit-brain icon, placed left of text
Box fill: light indigo (#E8EAF6) with indigo border (#3949AB)

**Arrow 1 (bidirectional, between Layer 1 and Layer 2):**
Label on arrow: `stdio  /  JSON-RPC 2.0  (MCP)`
Arrow style: bold, dark teal, double-headed

**LAYER 2 — Middle box (teal/green, rounded corners):**
Label: `IndustriConnect Protocol MCP Server`
Sub-label: `FastMCP · Python · asyncio · Unified Response Envelope`
Icon: Python snake logo + a small gear/cog icon, placed left of text
Box fill: light teal (#E0F2F1) with teal border (#00897B)

**Arrow 2 (bidirectional, between Layer 2 and Layer 3):**
Label on arrow: `Native Protocol Library`
Arrow style: bold, dark orange, double-headed

**LAYER 3 — Bottom box (orange/amber, rounded corners):**
Label: `Industrial Device  or  Mock Simulator`
Sub-label: `PLC · RTU · Sensor Gateway · Software Mock`
Icons: small PLC/factory equipment icon + a laptop/terminal icon for mock, placed left of text
Box fill: light amber (#FFF8E1) with amber border (#F57F17)

### Small protocol badges (optional enhancement)
Below Layer 3, show a single row of small pill-shaped badges (no larger than 10pt text):
`Modbus` · `OPC UA` · `MQTT` · `BACnet` · `DNP3` · `EtherCAT` · `EtherNet/IP` · `PROFIBUS` · `PROFINET` · `S7comm`
Badge colour: grey (#F5F5F5) with dark grey border

### Overall style
- White background, no shadows
- Font: clean sans-serif (Inter, Roboto, or similar), bold for layer labels
- Minimum font size visible at 300 DPI print: 10pt
- Total image dimensions: 1600×900 px (landscape), 300 DPI
- No decorative elements, gradients, or 3D effects
- High contrast for black-and-white printing

---

## Suggested tools
- **ChatGPT / DALL-E**: Use the prompt above
- **Midjourney**: `technical architecture diagram, three horizontal layers, blue teal orange, white background, professional infographic, no shadows --ar 16:9 --style raw`
- **Figma / draw.io**: Build manually for maximum control (recommended for publication quality)
- **Excalidraw**: Good for a hand-drawn academic diagram aesthetic

## Notes
- The figure must be legible in both colour and greyscale print
- Ensure text within boxes is readable at final print size
