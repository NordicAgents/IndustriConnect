# Figure 4 — Mock-First Development Lifecycle

## Purpose
Illustrates the three-stage development lifecycle: Mock → Staging → Production.
Used in Section 5 of the paper.

## Final filename
`../fig4_mock_lifecycle.png`  (place in `arxiv-paper/figures/`)

---

## AI Image Generation Prompt

Create a **horizontal three-stage development lifecycle flowchart** showing the
IndustriConnect mock-first development methodology. Style: clean modern
infographic, white background, suitable for a journal paper figure.

### Overall layout
Three large boxes arranged horizontally (left → right), connected by forward
arrows. A feedback loop arrow curves back from Stage 2 to Stage 1.

---

### Stage 1 — Mock Development (left box)

Box colour: light green fill (#DCFCE7), green border (#16A34A)
Title (bold, large): `1. Mock Development`
Subtitle: `Safe · Hardware-Free · Iterative`

Content inside box:
- **Icon**: Laptop/terminal with a green shield badge labelled "SAFE"
- **Bullet points** (small text):
  - Mock device simulator running locally
  - Develop and refine AI prompts
  - Validate tool call sequences
  - Debug without hardware risk
  - Reproducible, deterministic state

Bottom badge: `uv run modbus-mock-server` (grey pill, monospace font)

---

### Arrow 1 (Stage 1 → Stage 2)
Bold right-pointing arrow, dark grey
Label on arrow: `Promote to staging\n(change env vars)`

---

### Stage 2 — Staging / Integration (centre box)

Box colour: light yellow fill (#FEF9C3), amber border (#D97706)
Title (bold, large): `2. Staging / Integration`
Subtitle: `Shadow System · Real Protocol · Controlled`

Content inside box:
- **Icon**: Server rack icon + test tube / beaker icon
- Yellow badge: "TEST"
- **Bullet points**:
  - Point MCP server at staging device
  - Validate against real protocol behaviour
  - Integration testing
  - Measure latency and reliability
  - Regression tests against mock baseline

---

### Feedback arrow (Stage 2 → Stage 1)
Curved arrow going back from Stage 2 to Stage 1, above the boxes
Colour: amber/orange, dashed line
Label: `Iterate on issues found`

---

### Arrow 2 (Stage 2 → Stage 3)
Bold right-pointing arrow, dark grey
Label on arrow: `Approve for production\n(enable write flags)`

---

### Stage 3 — Production (right box)

Box colour: light blue fill (#DBEAFE), blue border (#1D4ED8)
Title (bold, large): `3. Production`
Subtitle: `Live Equipment · Monitored · Gated Writes`

Content inside box:
- **Icon**: Factory / PLC icon with a blue deployment badge
- **Bullet points**:
  - MCP server on edge gateway or OT network
  - WRITES\_ENABLED flag reviewed
  - Latency, error rate monitoring
  - Write approval flows (future)
  - Audit logging

---

### Below the three boxes — Shared elements bar
A thin horizontal bar spanning the full width, light grey background, labelled:
`All stages: same MCP server binary · same AI prompts · only environment variables change`
This emphasises the configuration-only promotion model.

---

### Style
- White background
- Font: clean sans-serif, bold for stage titles
- Total image: 1800×700 px (wide landscape), 300 DPI
- All text readable at 14 cm print width
- Greyscale safe (stages distinguished by numbering and labels, not only colour)

---

## Suggested tools
- **Figma**: Build as a component flow diagram — best result
- **draw.io / diagrams.net**: Use flowchart shapes with colour fill
- **Canva**: Use timeline/process template and customise
- **ChatGPT / DALL-E**: `Three-stage software development lifecycle flowchart,
  Mock Development, Staging Integration, Production, left to right flow,
  green yellow blue color scheme, white background, professional infographic,
  feedback loop arrow from stage 2 back to stage 1`

## Notes
- The feedback arrow (Stage 2 → Stage 1) is an important design element — do not omit
- The bottom shared-elements bar differentiates this from a generic 3-stage lifecycle
- Print legibility at 14 cm width is critical
