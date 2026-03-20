# Figure 2 — Unified Response Envelope Visualisation

## Purpose
Illustrates the common `{success, data, error, meta}` JSON structure
returned by every IndustriConnect tool. Used in Section 3.3 of the paper.

## Final filename
`../fig2_response_envelope.png`  (place in `arxiv-paper/figures/`)

---

## AI Image Generation Prompt

Create a **data card / JSON visualisation** diagram showing the four fields
of the IndustriConnect response envelope. The style should be professional
technical documentation — suitable for an IEEE journal figure.

### Layout

Show a single large rounded-rectangle card (dark slate #1E293B background,
white text) with a title bar at the top saying `Response Envelope` in a
bold monospace font (e.g., JetBrains Mono or Fira Code).

Inside the card, show four vertically stacked rows, each representing one
field. Each row has three columns:

| Column 1 (field name) | Column 2 (type badge) | Column 3 (example value / description) |
|---|---|---|
| `"success"` | `boolean` | `true` — green checkmark icon |
| `"data"` | `object` | `{ "values": [3.14, 2.72], "address": 100, "dtype": "float32" }` |
| `"error"` | `string \| null` | `null` — shown in muted grey |
| `"meta"` | `object` | `{ "latency_ms": 12.4, "attempts": 1 }` |

### Colour coding for rows
- `success` row: subtle green left-border accent (#22C55E), 4px left border
- `data` row: subtle blue left-border accent (#3B82F6), 4px left border
- `error` row: subtle red left-border accent (#EF4444), 4px left border
- `meta` row: subtle grey left-border accent (#9CA3AF), 4px left border

### Type badges
Small rounded pill shapes (like GitHub language badges):
- `boolean` → green pill
- `object` → blue pill
- `string | null` → red pill
- `object` → grey pill

### Below the card
Show two smaller cards side by side (1/2 width each):
- Left card: `Success Response` — show a compact full JSON example (Modbus float32 read)
- Right card: `Error Response` — show compact JSON with `"success": false`, `"error": "Connection timeout after 5s"`, `"data": null`

Use a light (#F8FAFC) background for the overall composition with the main
dark card centred on it.

### Style
- Monospace font for all JSON code (JetBrains Mono / Fira Code / Courier)
- Sans-serif for labels and descriptions
- Clean, no shadows or 3D effects
- Total image: 1400×800 px, 300 DPI, white/near-white overall background

---

## Suggested tools
- **Figma**: Create the card components manually — best result for publication
- **Carbon.now.sh** or **Ray.so**: Generate the JSON snippet as a code image,
  then compose in Canva or Figma
- **ChatGPT / DALL-E**: `A professional technical data card showing JSON response
  envelope with four color-coded fields success data error meta, dark card on
  white background, monospace font, IEEE journal style`
- **Excalidraw**: Hand-drawn aesthetic works well for academic papers

## Notes
- The two example JSON blocks must be syntactically valid JSON
- Ensure legibility at ~8 cm column width (print)
- Greyscale version must remain distinguishable (use patterns or labels if needed)
