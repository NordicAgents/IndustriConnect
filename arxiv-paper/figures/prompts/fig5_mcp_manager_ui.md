# Figure 5 — mcp-manager-ui Screenshot / Illustration

## Purpose
Shows the mcp-manager-ui web console interface.
Used in Section 6 of the paper.

## Final filename
`../fig5_mcp_manager_ui.png`  (place in `arxiv-paper/figures/`)

---

## Option A — Use a Real Screenshot (Recommended)

If you have the mcp-manager-ui running locally, the best approach is:

1. Start the UI: `cd mcp-manager-ui && npm install && npm run dev`
2. Start and connect several mock MCP servers (Modbus, OPC UA, S7comm)
3. Send a sample prompt such as:
   _"Read the first 5 holding registers from the Modbus device"_
4. Let the AI respond with tool call results visible
5. Take a full-window screenshot at 1440×900 or 1920×1080 px
6. Crop to show the sidebar + chat panel (omit browser chrome if desired)
7. Save as `fig5_mcp_manager_ui.png` at 300 DPI

---

## Option B — AI-Generated UI Mockup

If a real screenshot is not available, generate a stylised UI mockup:

### AI Image Generation Prompt

Create a **realistic dark-mode web application UI mockup** representing an
industrial MCP server management console. Style: professional SaaS product
screenshot, suitable for an IEEE journal figure.

### Layout (left sidebar + main panel)

**Left sidebar (~25% width), dark (#1E293B background):**

Top: App logo area with text `mcp-manager-ui` in white bold sans-serif

Below: Section header `MCP Servers` with a `+ Add` button

Server list entries (each with status indicator dot):
```
● Modbus MCP          [green dot — connected]
  TCP · 127.0.0.1:1502 · 14 tools

● OPC UA MCP          [green dot — connected]
  opc.tcp://localhost · 8 tools

● S7comm MCP          [yellow dot — connecting]
  192.168.0.1 · 12 tools

○ MQTT MCP            [grey dot — offline]
  mqtt://broker:1883 · 10 tools
```

Below servers: Section header `LLM Provider`
Dropdown showing: `Anthropic Claude ▾`

**Main panel (~75% width), slightly lighter dark (#0F172A background):**

Top bar: `Chat Session #1` tab, settings gear icon

Chat area showing a conversation:

User message bubble (right-aligned, indigo background):
```
"Read the current pump speed and temperature
 from the Modbus device"
```

AI response (left-aligned, dark card):
```
I'll read both values from the Modbus device.

[Tool Call] read_holding_typed
  address: 100, dtype: "float32"
  → { "success": true, "data": { "values": [1450.5], "dtype": "float32" }, "meta": { "latency_ms": 8.2 } }

[Tool Call] read_holding_typed
  address: 104, dtype: "float32"
  → { "success": true, "data": { "values": [72.3], "dtype": "float32" }, "meta": { "latency_ms": 7.9 } }

The pump is currently running at **1,450.5 RPM**
with a temperature of **72.3°C** — both values
are within normal operating parameters.
```

Tool call cards should be styled as collapsible monospace code blocks in dark
grey (#334155), showing the arguments and response compactly.

### Colour palette
- Background: #0F172A (near-black navy)
- Sidebar: #1E293B
- Cards: #334155
- User message: #4338CA (indigo)
- AI message: #1E293B
- Green status: #22C55E
- Yellow status: #EAB308
- Text: #F1F5F9
- Muted text: #94A3B8
- Accent: #14B8A6 (teal)

### Style
- Realistic browser chrome (macOS style) OR frameless screenshot crop
- Total image: 1440×810 px (16:9), 300 DPI
- Subtle but readable — all text legible at print size

---

## Suggested tools
- **Real screenshot** (Option A): Strongly preferred for publication
- **Figma**: Build as a UI mockup with components — second best
- **ChatGPT / DALL-E**: `Dark mode web application screenshot of industrial IoT
  MCP server manager, left sidebar with server list and status indicators,
  main chat panel with AI conversation and tool call results, professional
  SaaS product UI, navy dark theme`
- **Midjourney**: `dark mode industrial IoT management dashboard UI screenshot,
  left sidebar, chat interface, professional software, navy background --ar 16:9`

## Notes
- DO NOT include any real API keys or sensitive connection strings in the screenshot
- The tool call result cards are a key differentiator — make them clearly visible
- Ensure the server status dots (green/yellow/grey) are clearly distinguishable
- If using Option A, blur or anonymise any sensitive data before publication
