# Figure 3 — Protocol Ecosystem Map

## Purpose
Visual overview of all nine industrial protocols supported by IndustriConnect.
Used in Section 4 of the paper (alongside Table 1).

## Final filename
`../fig3_protocol_map.png`  (place in `arxiv-paper/figures/`)

---

## AI Image Generation Prompt

Create a **hub-and-spoke ecosystem diagram** showing IndustriConnect at the
centre connecting to nine industrial protocol domains. Style: technology
ecosystem / constellation map — dark background, coloured glowing nodes,
clean lines. Suitable for a full-width figure in an academic paper.

### Center hub
A hexagonal or circular badge labelled:
```
IndustriConnect
MCP Suite
```
Dark navy fill (#0F172A), white text, teal border glow (#14B8A6)
Size: largest element in the diagram

### Nine spoke nodes (evenly distributed around the hub)

Each spoke is a rounded rectangle node connected to the hub by a glowing line.
Arrange them in a circle or octagonal layout with even spacing.

| Node label | Icon | Colour | Sector |
|---|---|---|---|
| **Modbus** | Industrial meter / dial gauge icon | Orange (#F97316) | Manufacturing, energy |
| **MQTT + Sparkplug B** | Cloud with lightning bolt / wireless signal | Cyan (#06B6D4) | IIoT, edge |
| **OPC UA** | Unified architecture / OPC foundation logo style | Blue (#3B82F6) | Unified data access |
| **BACnet / IP** | Building / HVAC unit icon | Green (#22C55E) | Building automation |
| **DNP3** | Power line / electricity tower icon | Yellow (#EAB308) | Power utility SCADA |
| **EtherCAT** | Ethernet ring / circular arrows icon | Purple (#A855F7) | Motion control |
| **EtherNet/IP** | Robot arm / Rockwell PLC icon | Red (#EF4444) | Discrete manufacturing |
| **PROFIBUS** | Bus topology / RS-485 connector icon | Amber (#F59E0B) | Process automation |
| **PROFINET** | Factory floor / conveyor belt icon | Indigo (#6366F1) | Siemens factory |
| **S7comm** | PLC / Siemens S7 controller icon | Teal (#14B8A6) | Siemens PLCs |

Each node should show:
- Protocol name (bold, ~12pt)
- Small icon (16×16px equivalent)
- Domain label (smaller italic text, ~8pt): e.g., "Manufacturing & Energy"

### Connection lines (hub to each node)
Glowing lines, colour matching the target node, 2px width with subtle blur glow effect.

### Background
Very dark navy (#0A0F1E) or near-black. Subtle hexagonal grid pattern in the background
(very faint, #1E293B) for a tech/industrial aesthetic.

### Optional: Outer ring annotation
A faint dashed outer circle with text annotations at cardinal points:
- Top: "Fieldbus Protocols"
- Right: "Industrial Ethernet"
- Bottom: "IIoT & Messaging"
- Left: "Building & Utility"

### Style
- Total image: 1600×1400 px, 300 DPI (square-ish, for full column width)
- High contrast — readable at 14 cm print width
- All text must be legible without magnification

---

## Suggested tools
- **Figma**: Build as a component diagram — best for publication
- **draw.io**: Use circular layout with custom icons from Flaticon/Noun Project
- **ChatGPT / DALL-E**: `Hub and spoke diagram of nine industrial automation
  protocols connected to a central IndustriConnect badge, dark navy background,
  glowing colored nodes, tech infographic style, IEEE paper figure`
- **Midjourney**: `technology ecosystem hub and spoke diagram, nine colorful
  nodes, dark background, glowing lines, industrial IoT protocols --ar 1:1
  --style raw --v 6`

## Notes
- Do NOT use copyrighted vendor logos (Siemens, Rockwell, etc.) — use generic icons
- The figure should print clearly in greyscale (use labels, not only colour)
- Recommended icon sources: Flaticon (industrial), Noun Project, or custom SVG
