"""Generate fig5_mcp_manager_ui.png — IndustriConnect MCP Manager UI mockup.

Fixes:
- Correct adapter names (Modbus, MQTT + Sparkplug B, OPC UA)
- Correct LLM provider (Claude, not GPT-4)
- Correct tool calls (real IndustriConnect operations)
- Proper IndustriConnect branding
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import textwrap

fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.2)
ax.axis("off")
fig.patch.set_facecolor("#1a1a2e")

# ── Sidebar ──────────────────────────────────────────────
sidebar_w = 2.8
sidebar = FancyBboxPatch((0, 0), sidebar_w, 6.2, boxstyle="square,pad=0",
                          facecolor="#16213e", edgecolor="#0f3460", linewidth=0.8)
ax.add_patch(sidebar)

# Sidebar header
ax.text(0.22, 5.82, "INDUSTRICONNECT", fontsize=8.5, fontweight="bold",
        color="#e94560", va="top", fontfamily="monospace")
ax.text(0.22, 5.55, "MCP Manager v0.3", fontsize=6, color="#7f8c8d", va="top")

# Divider
ax.plot([0.15, sidebar_w - 0.15], [5.38, 5.38], color="#0f3460", linewidth=0.6)

# Adapter label
ax.text(0.22, 5.2, "Protocol Adapters", fontsize=6.5, color="#94a3b8",
        fontweight="bold", va="top")

# Adapter entries
adapters = [
    ("Modbus TCP",           "connected",  True),
    ("MQTT + Sparkplug B",   "connected",  True),
    ("OPC UA",               "connected",  True),
    ("BACnet/IP",            "scaffold",   False),
    ("EtherNet/IP",          "scaffold",   False),
]

y_pos = 4.88
for name, status, active in adapters:
    # Row background for active
    if active:
        row_bg = FancyBboxPatch((0.12, y_pos - 0.18), sidebar_w - 0.24, 0.36,
                                 boxstyle="round,pad=0.04", facecolor="#0f3460",
                                 edgecolor="#1a73e8", linewidth=0.6, alpha=0.7)
        ax.add_patch(row_bg)

    # Status dot
    dot_color = "#2ecc71" if status == "connected" else "#7f8c8d"
    ax.plot(0.35, y_pos, "o", color=dot_color, markersize=4)

    # Name
    ax.text(0.55, y_pos + 0.02, name, fontsize=6.2, color="white" if active else "#7f8c8d",
            va="center")

    # Status text
    st_color = "#2ecc71" if status == "connected" else "#7f8c8d"
    ax.text(sidebar_w - 0.2, y_pos + 0.02, status, fontsize=5, color=st_color,
            va="center", ha="right", style="italic")

    y_pos -= 0.42

# Divider
ax.plot([0.15, sidebar_w - 0.15], [y_pos + 0.12, y_pos + 0.12],
        color="#0f3460", linewidth=0.6)

# System info
y_pos -= 0.18
ax.text(0.22, y_pos, "System", fontsize=6.5, color="#94a3b8",
        fontweight="bold", va="top")
y_pos -= 0.28
ax.text(0.22, y_pos, "LLM Provider", fontsize=5.5, color="#7f8c8d", va="top")
y_pos -= 0.22

# LLM provider box
llm_box = FancyBboxPatch((0.18, y_pos - 0.12), sidebar_w - 0.4, 0.3,
                           boxstyle="round,pad=0.04", facecolor="#0f3460",
                           edgecolor="#1a73e8", linewidth=0.6)
ax.add_patch(llm_box)
ax.text(0.35, y_pos + 0.03, "Claude (Anthropic)", fontsize=6, color="white", va="center")

y_pos -= 0.45
ax.text(0.22, y_pos, "Mock endpoints", fontsize=5.5, color="#7f8c8d", va="top")
y_pos -= 0.22
mock_box = FancyBboxPatch((0.18, y_pos - 0.12), sidebar_w - 0.4, 0.3,
                           boxstyle="round,pad=0.04", facecolor="#0f3460",
                           edgecolor="#2ecc71", linewidth=0.6)
ax.add_patch(mock_box)
ax.text(0.35, y_pos + 0.03, "All mocks running", fontsize=6,
        color="#2ecc71", va="center")

# ── Main chat area ───────────────────────────────────────
chat_x = sidebar_w + 0.15
chat_w = 10 - chat_x - 0.1

# Chat header
header_bg = FancyBboxPatch((chat_x, 5.7), chat_w, 0.4,
                            boxstyle="square,pad=0", facecolor="#16213e",
                            edgecolor="#0f3460", linewidth=0.6)
ax.add_patch(header_bg)
ax.text(chat_x + 0.15, 5.9, "Chat Session", fontsize=8, fontweight="bold",
        color="white", va="center")
ax.text(chat_x + 1.55, 5.9, "|  Connected to: Modbus, MQTT+SB, OPC UA",
        fontsize=5.5, color="#7f8c8d", va="center")

# Chat body background
chat_bg = FancyBboxPatch((chat_x, 0.05), chat_w, 5.62,
                          boxstyle="square,pad=0", facecolor="#1a1a2e",
                          edgecolor="#0f3460", linewidth=0.6)
ax.add_patch(chat_bg)

# ── Chat messages ────────────────────────────────────────
msg_x = chat_x + 0.2
msg_w = chat_w - 0.4
cy = 5.35

def draw_user_msg(y, text):
    """Draw a user message bubble (right-aligned)."""
    lines = textwrap.wrap(text, width=55)
    h = len(lines) * 0.2 + 0.12
    bx = msg_x + msg_w - 4.8
    bubble = FancyBboxPatch((bx, y - h), 4.8, h,
                             boxstyle="round,pad=0.06", facecolor="#e94560",
                             edgecolor="none", alpha=0.85)
    ax.add_patch(bubble)
    ax.text(bx + 0.1, y - 0.04, "Operator", fontsize=4.5, color="#ffccd5",
            va="top", fontweight="bold")
    ty = y - 0.22
    for line in lines:
        ax.text(bx + 0.1, ty, line, fontsize=5.5, color="white", va="top")
        ty -= 0.18
    return y - h - 0.12

def draw_ai_msg(y, text):
    """Draw an AI message bubble (left-aligned)."""
    lines = textwrap.wrap(text, width=62)
    h = len(lines) * 0.18 + 0.12
    bubble = FancyBboxPatch((msg_x, y - h), 5.4, h,
                             boxstyle="round,pad=0.06", facecolor="#0f3460",
                             edgecolor="#1a73e8", linewidth=0.5, alpha=0.8)
    ax.add_patch(bubble)
    ax.text(msg_x + 0.1, y - 0.04, "Assistant", fontsize=4.5,
            color="#94a3b8", va="top", fontweight="bold")
    ty = y - 0.2
    for line in lines:
        ax.text(msg_x + 0.1, ty, line, fontsize=5.5, color="#e0e0e0", va="top")
        ty -= 0.18
    return y - h - 0.12

def draw_tool_call(y, tool, params, result_lines):
    """Draw a tool call block."""
    n_result = len(result_lines)
    h = 0.38 + n_result * 0.16
    box = FancyBboxPatch((msg_x + 0.15, y - h), 5.2, h,
                          boxstyle="round,pad=0.05", facecolor="#0d1117",
                          edgecolor="#30363d", linewidth=0.6)
    ax.add_patch(box)

    ax.text(msg_x + 0.3, y - 0.08, "Tool Call", fontsize=4.5,
            color="#58a6ff", va="top", fontweight="bold", fontfamily="monospace")
    ax.text(msg_x + 0.9, y - 0.08, tool, fontsize=5,
            color="#79c0ff", va="top", fontfamily="monospace")
    ax.text(msg_x + 0.3, y - 0.24, params, fontsize=4.8,
            color="#8b949e", va="top", fontfamily="monospace")

    ty = y - 0.42
    for rl in result_lines:
        color = "#2ecc71" if rl.startswith('"success"') else "#8b949e"
        if rl.startswith('"error"'):
            color = "#e94560"
        ax.text(msg_x + 0.3, ty, rl, fontsize=4.8, color=color,
                va="top", fontfamily="monospace")
        ty -= 0.16
    return y - h - 0.1

# --- Conversation flow ---

# User message
cy = draw_user_msg(cy,
    "Read the OPC UA temperature sensor and check the Modbus "
    "holding registers at address 0, then publish a status update via MQTT.")

# AI thinking
cy = draw_ai_msg(cy, "I'll query all three adapters for you.")

# Tool call 1: OPC UA read
cy = draw_tool_call(cy,
    "opcua_read_node",
    '{ "node_id": "ns=2;s=Temperature_Sensor_001" }',
    ['"success": true,  "data": { "value": 65.4, "unit": "°C" }',
     '"meta": { "latency_ms": 2.3, "endpoint": "opc.tcp://..." }'])

# Tool call 2: Modbus read
cy = draw_tool_call(cy,
    "modbus_read_holding_registers",
    '{ "address": 0, "count": 4 }',
    ['"success": true,  "data": { "registers": [120, 85, 42, 0] }',
     '"meta": { "latency_ms": 1.5, "device": "127.0.0.1:1502" }'])

# Tool call 3: MQTT publish
cy = draw_tool_call(cy,
    "mqtt_sparkplug_publish_ddata",
    '{ "metric": "temperature", "value": 65.4 }',
    ['"success": true,  "data": { "topic": "spBv1.0/Plant/DDATA/..." }',
     '"meta": { "latency_ms": 1.8, "broker": "127.0.0.1:1883" }'])

# AI summary
cy = draw_ai_msg(cy,
    "OPC UA temperature reads 65.4 °C, Modbus registers [120, 85, 42, 0] "
    "are nominal, and the Sparkplug B DDATA update was published successfully.")

# ── Input bar ────────────────────────────────────────────
input_bg = FancyBboxPatch((chat_x + 0.1, 0.12), chat_w - 0.2, 0.35,
                           boxstyle="round,pad=0.05", facecolor="#0f3460",
                           edgecolor="#1a73e8", linewidth=0.5)
ax.add_patch(input_bg)
ax.text(chat_x + 0.3, 0.295, "Enter operator prompt...", fontsize=5.5,
        color="#5f6a7d", va="center", style="italic")

plt.tight_layout(pad=0.1)
fig.savefig(
    "/Users/mx/Documents/Work/industriAgents/IndustriConnect-MCPs/"
    "arxiv-paper/figures/fig5_mcp_manager_ui.png",
    dpi=200, bbox_inches="tight", facecolor="#1a1a2e",
)
print("Done — fig5_mcp_manager_ui.png written")
