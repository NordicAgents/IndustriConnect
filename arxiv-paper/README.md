# IndustriConnect — arXiv Paper

**Title:** IndustriConnect: A Model Context Protocol Suite for AI-Assisted Industrial Automation

**Target:** arXiv — primary category `eess.SY`, cross-list `cs.SE`, `cs.AI`

---

## Files

```
arxiv-paper/
├── main.tex              ← Full LaTeX paper
├── references.bib        ← BibTeX bibliography (peer-reviewed journals only)
├── figures/
│   ├── prompts/          ← AI image generation prompts for each figure
│   │   ├── fig1_architecture.md
│   │   ├── fig2_response_envelope.md
│   │   ├── fig3_protocol_map.md
│   │   ├── fig4_mock_lifecycle.md
│   │   └── fig5_mcp_manager_ui.md
│   ├── fig1_architecture.png       ← Add after generating from prompt
│   ├── fig2_response_envelope.png  ← Add after generating from prompt
│   ├── fig3_protocol_map.png       ← Add after generating from prompt
│   ├── fig4_mock_lifecycle.png     ← Add after generating from prompt
│   └── fig5_mcp_manager_ui.png     ← Screenshot or generated from prompt
└── README.md             ← This file
```

---

## Before You Compile

### 1. Fill in author details
Open `main.tex` and replace every placeholder:

```latex
\author[1]{[Author 1 Name]}
\author[2]{[Author 2 Name]}
\affil[1]{[Department], [University / Institution 1], [City, Country]\\
         \texttt{[author1@example.com]}}
\affil[2]{[Department], [University / Institution 2], [City, Country]\\
         \texttt{[author2@example.com]}}
```

### 2. Add the GitHub URL
In the Conclusion section, replace:
```
\url{https://github.com/[your-repo-path-here]}
```
with the actual repository URL.

### 3. Generate and place figures
Read each prompt file in `figures/prompts/`, generate the image using your
preferred AI image tool (ChatGPT/DALL-E, Midjourney, Figma, etc.), and save
the result as the corresponding PNG in `figures/`:

| Prompt file | Output PNG | Recommended tool |
|---|---|---|
| `fig1_architecture.md` | `fig1_architecture.png` | Figma / draw.io |
| `fig2_response_envelope.md` | `fig2_response_envelope.png` | Figma / Carbon.now.sh |
| `fig3_protocol_map.md` | `fig3_protocol_map.png` | Figma / Midjourney |
| `fig4_mock_lifecycle.md` | `fig4_mock_lifecycle.png` | draw.io / Canva |
| `fig5_mcp_manager_ui.md` | `fig5_mcp_manager_ui.png` | Real screenshot (preferred) |

The paper compiles without these files — placeholder boxes are rendered in
their place — but you must add the figures before arXiv submission.

### 4. Verify references
All entries in `references.bib` include a `note` field where the certainty
is lower. Verify every reference against the actual publication (check DOI)
before submission. arXiv and journal reviewers will check citations.

---

## Compiling the PDF

### Requirements
- TeX Live 2022+ or MacTeX 2022+ (includes `pdflatex`, `bibtex`, `natbib`)
- The `authblk` package (included in TeX Live full install)

### Compile command sequence

```bash
cd arxiv-paper

# Full build (run 3 times to resolve all cross-references)
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

### Quick check (no bibliography resolution)
```bash
pdflatex main.tex
```

### Expected output
- `main.pdf` — approximately 12–16 pages at 11pt, A4
- `main.aux`, `main.bbl`, `main.blg` — intermediate files (safe to delete)

### Missing figure warnings
If figure PNG files are not yet in `figures/`, you will see:
```
LaTeX Warning: File 'figures/fig1_architecture.png' not found.
```
This is expected — the `\IfFileExists` macro renders placeholder boxes instead.
The PDF will still compile successfully.

### Overfull hbox warnings
Minor overfull hbox warnings (< 5pt) in the protocol subsections are acceptable
and will not affect arXiv acceptance. Resolve by rewording the affected
paragraph if desired.

---

## arXiv Submission Checklist

- [ ] Author names and affiliations filled in
- [ ] GitHub repository URL added to Conclusion
- [ ] All five figures generated and placed in `figures/`
- [ ] All references verified against actual publications (DOIs checked)
- [ ] PDF compiles cleanly (`pdflatex` × 3 + `bibtex`)
- [ ] PDF is 10–16 pages
- [ ] No confidential information (API keys, IP addresses) in figures
- [ ] Abstract is under 2000 characters (arXiv limit)
- [ ] Upload: `main.tex`, `references.bib`, `figures/*.png` to arXiv
- [ ] Set primary category: `eess.SY`
- [ ] Add cross-list categories: `cs.SE`, `cs.AI`
- [ ] Set license: Creative Commons Attribution 4.0 (CC BY 4.0) recommended

---

## Package dependencies

The following LaTeX packages are used (all included in TeX Live full):

| Package | Purpose |
|---|---|
| `geometry` | Page margins |
| `microtype` | Typography improvements |
| `amsmath`, `amssymb` | Mathematics |
| `graphicx` | Figures |
| `natbib` | Bibliography (numbers, sort&compress) |
| `hyperref` | Clickable links and DOIs |
| `booktabs` | Professional table rules |
| `xcolor` | Colours for code listings |
| `listings` | Code blocks (Python, JSON) |
| `authblk` | Multiple authors with affiliations |
| `enumitem` | List formatting |
| `caption`, `subcaption` | Figure captions |
| `url` | URL formatting |
