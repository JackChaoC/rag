# Design QA

- Source visual truth: `C:\Users\13181\.codex\generated_images\01a0b923-6785-7d00-b815-b778c8c52a96\exec-ca558f4b-c902-40ce-afe7-9a1c9047ab8e.png`
- Implementation screenshot surface: `D:\Rubbish\rag\frontend\.design-qa\comparison.html` (`http://127.0.0.1:8000/ui/.design-qa/comparison.html`)
- Implementation route: `http://127.0.0.1:8000/ui/#/documents`
- Viewport: source and implementation normalized to 1488 × 1058 CSS px, rendered side by side at 0.48 scale in the in-app browser
- Source pixels: 1488 × 1058
- Implementation CSS size: 1488 × 1058; browser density 1×
- State: Documents route; source contains illustrative rows, implementation correctly shows the real empty dataset

## Full-view comparison evidence

The in-app browser displayed the reference and live implementation together on the persisted comparison surface. The implementation preserves the selected concept's 220 px dark sidebar, compact top status bar, four-stat strip, primary document action, filter toolbar, and table-dominant hierarchy. The requested theme change is intentional: cobalt is replaced by emerald (`#0f8f6f`) with a deep green sidebar (`#13231e`).

## Focused region comparison evidence

The live Documents route was also inspected at its native viewport. Header, statistics, toolbar, table header, empty state, navigation icons, spacing, focus affordances, and service status were legible without clipping. No extra focused crop was needed because there are no raster assets or small custom illustrations; the dense table region was readable in the native capture.

## Required fidelity surfaces

- Fonts and typography: Inter-style UI hierarchy with IBM Plex Mono for identifiers; weights, wrapping, and compact table text match the reference intent.
- Spacing and layout rhythm: sidebar, content margins, stat cards, toolbar, and table align to the reference composition; responsive collapse was also exercised through the comparison iframe.
- Colors and visual tokens: emerald replacement is applied consistently to active navigation, primary actions, focus rings, badges, and score tokens; semantic warning and error colors remain distinct.
- Image quality and assets: the design contains no product imagery. Phosphor Icons supplies all visible interface icons; no placeholder or handcrafted SVG/CSS icon substitutes are present.
- Copy and content: Chinese route labels and action copy are specific to the actual RAG HTTP contract. The empty dataset difference from the mock is expected and truthful.

## Findings

No actionable P0, P1, or P2 visual differences remain. The empty table is caused by the current database state, not an implementation mismatch.

## Comparison history

- Initial comparison rendered the implementation iframe at a responsive mobile width, which was not a valid same-viewport comparison.
- Fixed the comparison surface to render the implementation at 1488 × 1058 CSS px and scale both sides equally.
- Post-fix evidence shows matching desktop proportions and hierarchy. No P0/P1/P2 issue remained.

## Interaction and runtime verification

- Routes tested: Documents, Add Document, Search, Chunk Query, System Status.
- Real search request tested with Top-K 5; Ollama embedding and Qdrant query both returned HTTP 200.
- Browser console warnings/errors: none.
- Contract tests: 6 passed.
- Full suite: 23 passed, 4 skipped.

## Follow-up polish

- P3: populated document rows can be visually rechecked after the user adds sample content.

final result: passed
