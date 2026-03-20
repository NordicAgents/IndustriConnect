"""Generate fig3_protocol_map.png — IndustriConnect protocol landscape.

Fixes:
- Remove duplicate S7comm (exactly 10 protocols)
- Visually distinguish 3 flagship adapters from 7 scaffold modules
- Use "MQTT + Sparkplug B" label
- Add a legend
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- data ---
# 10 protocols, ordered clockwise from top
protocols = [
    ("Modbus",              True),
    ("MQTT +\nSparkplug B", True),
    ("OPC UA",              True),
    ("BACnet/IP",           False),
    ("DNP3",                False),
    ("EtherCAT",            False),
    ("EtherNet/IP",         False),
    ("PROFIBUS\nDP/PA",     False),
    ("PROFINET",            False),
    ("Siemens\nS7comm",     False),
]

n = len(protocols)
angles = [np.pi / 2 - i * 2 * np.pi / n for i in range(n)]

# --- colours ---
flagship_bg   = "#1a73e8"
flagship_text = "#ffffff"
scaffold_bg   = "#e8eaed"
scaffold_text = "#3c4043"
hub_bg        = "#f8f9fa"
hub_edge      = "#1a73e8"

# --- figure ---
fig, ax = plt.subplots(figsize=(6, 6), dpi=200)
ax.set_xlim(-2.1, 2.1)
ax.set_ylim(-2.1, 2.1)
ax.set_aspect("equal")
ax.axis("off")

# Hub hexagon
hex_r = 0.62
hex_angles = [np.pi / 6 + i * np.pi / 3 for i in range(6)]
hex_xs = [hex_r * np.cos(a) for a in hex_angles]
hex_ys = [hex_r * np.sin(a) for a in hex_angles]
hex_patch = plt.Polygon(
    list(zip(hex_xs, hex_ys)),
    closed=True,
    facecolor=hub_bg,
    edgecolor=hub_edge,
    linewidth=2.0,
    zorder=3,
)
ax.add_patch(hex_patch)
ax.text(0, 0.08, "IndustriConnect", ha="center", va="center",
        fontsize=9, fontweight="bold", color=hub_edge, zorder=4)
ax.text(0, -0.14, "MCP adapter ecosystem", ha="center", va="center",
        fontsize=6.0, color="#5f6368", zorder=4)

# Spoke radius
spoke_r = 1.45
box_w, box_h = 0.92, 0.38

for i, (label, is_flagship) in enumerate(protocols):
    a = angles[i]
    cx = spoke_r * np.cos(a)
    cy = spoke_r * np.sin(a)

    # Connecting line
    # start from hub edge toward the box
    line_start_r = hex_r + 0.06
    line_end_r = spoke_r - box_w * 0.55
    lx0, ly0 = line_start_r * np.cos(a), line_start_r * np.sin(a)
    lx1, ly1 = line_end_r * np.cos(a), line_end_r * np.sin(a)
    ax.plot([lx0, lx1], [ly0, ly1], color="#dadce0", linewidth=1.2, zorder=1)

    # Determine box height (taller for two-line labels)
    lines = label.count("\n") + 1
    bh = box_h if lines == 1 else box_h + 0.14

    bg = flagship_bg if is_flagship else scaffold_bg
    tc = flagship_text if is_flagship else scaffold_text
    ec = flagship_bg if is_flagship else "#dadce0"
    lw = 2.0 if is_flagship else 1.2

    rect = mpatches.FancyBboxPatch(
        (cx - box_w / 2, cy - bh / 2), box_w, bh,
        boxstyle="round,pad=0.06",
        facecolor=bg, edgecolor=ec, linewidth=lw, zorder=2,
    )
    ax.add_patch(rect)
    ax.text(cx, cy, label, ha="center", va="center",
            fontsize=7.2, fontweight="bold", color=tc, zorder=3,
            linespacing=1.15)

# --- legend ---
legend_elements = [
    mpatches.Patch(facecolor=flagship_bg, edgecolor=flagship_bg,
                   label="Evaluated flagship"),
    mpatches.Patch(facecolor=scaffold_bg, edgecolor="#dadce0",
                   label="Scaffold module"),
]
leg = ax.legend(handles=legend_elements, loc="lower center",
                frameon=True, fontsize=7, ncol=2,
                bbox_to_anchor=(0.5, -0.04), handlelength=1.2,
                handleheight=0.9, borderpad=0.5)
leg.get_frame().set_edgecolor("#dadce0")
leg.get_frame().set_linewidth(0.8)

plt.tight_layout(pad=0.3)
fig.savefig(
    "/Users/mx/Documents/Work/industriAgents/IndustriConnect-MCPs/arxiv-paper/figures/fig3_protocol_map.png",
    dpi=200, bbox_inches="tight", facecolor="white",
)
print("Done — fig3_protocol_map.png written")
