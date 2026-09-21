# Field Guide design system

The canonical example is `../assets/ifc-reference.html`. The user approved its design and general layout. Reuse the visual decisions, not the IFC subject or a fixed article outline.

## Visual thesis

An engineering field guide with editorial confidence: dark green technical plates alternate with a clean paper reading surface. Large titles establish hierarchy; code, diagrams, fine rules, and chapter numbers do the organizational work. Lime highlights structure on dark surfaces. Orange is a restrained index or caution accent. Avoid gradients as decoration, excessive rounded cards, shadows, and dashboard-like KPI grids.

## Tokens

The starter carries the exact CSS. Keep these roles consistent:

| Token | Value | Role |
| --- | --- | --- |
| `--paper` | `#f7f8f4` | Main page and navigation |
| `--white` | `#ffffff` | Code and interactive surfaces |
| `--ink` | `#172e2b` | Headings and primary text |
| `--muted` | `#54645e` | Supporting text on light surfaces |
| `--line` | `#d6ded6` | Fine dividers and light outlines |
| `--forest` | `#142c2a` | Hero, synthesis section, selected controls |
| `--forest-light` | `#203e39` | Nodes within dark panels |
| `--lime` | `#d8f781` | Important marks and labels on dark surfaces |
| `--green` | `#376952` | Active data, limits, and references on light surfaces |
| `--orange` | `#b64720` | Chapter numbering and caution rules |
| `--blue` | `#245e95` | Types or symbolic values on light surfaces |
| `--purple` | `#74529a` | Optional additional semantic category |

On dark surfaces, use `#f4f6ed` for primary text, `#c3d2ca` for supporting text, and `#4a6358` for subtle borders. Light syntax colors include `#93d6e2` and `#ffbd8b`. Lime is not body text on paper. Color should distinguish meaning and always have a text or shape counterpart. Light-mode-only is the intentional reference design; do not add an unrequested theme toggle.

## Typography and measure

- Body: system sans, 16px, line-height 1.65; introductory copy 17–18px.
- Title: system sans, weight around 550, tightly tracked (`-.065em`), `clamp(3rem, 6.7vw, 5.4rem)`. Highlight one meaningful fragment with Iowan/Palatino/Georgia italic, normal weight, lime.
- Section titles: `clamp(2rem, 3.6vw, 3rem)`, tracking `-.045em`, weight around 550.
- Monospace: SFMono-Regular/Consolas/Liberation Mono. Use for code, chapter indices, small overlines, compact status, and formulas; not paragraphs.
- Overlines: 12px, modest uppercase letter spacing. Primary labels and controls: at least 14px. Preserve 16px body text. Secondary code metadata may be smaller but must remain legible.
- Main container: max 1160px, centered. Desktop gutters 40px; tablet 22px; phone 18px. Introductory paragraph measure around 690px.
- Section padding: 76px vertically on desktop, 48px on phones. Heading gutter: 72px for the section index; reduce to 48px/35px at smaller widths.

## Composition and component map

Read the named classes in the reference when adapting a component. They are examples, not a requirement to include all of them.

| Need | Classes | Composition |
| --- | --- | --- |
| Page navigation | `.topbar`, `.brand`, `nav` | 72px bar; compact monogram; short chapter anchors; paper background |
| Opening | `.hero`, `.hero-top` | Two columns: title left, short premise right; forest background |
| Example + diagram | `.hero-visual`, `.hero-code`, `.hero-graph` | One outlined plate; two panes; no heavy shadow |
| Relationship graph | `.graph-root`, `.graph-branches`, `.graph-node` | Root above two descendants; lines represent real relationships |
| Chapter heading | `.section-heading`, `.section-number`, `.deck` | Small orange index in its own gutter; title and readable summary |
| Annotated source | `.split`, `.code-panel`, `.file-line`, `.annotation` | Source left, local selector and explanation right; active rows with green side rule |
| Labelled syntax | `.anatomy`, `.anatomy-piece` | Wrapping code pieces, each with a short label underneath |
| Compact vocabulary | `.value-grid`, `.value` | Shared border grid; code/example first, name second, short meaning third |
| Formalism + explanation | `.grammar-row`, `.grammar`, `.grammar-note` | Small dark code panel beside plain-language interpretation |
| Step-through | `.lab`, `.token-stream`, `.trace-readout`, `.lab-actions` | One current example; progress and current state; back/next/replay |
| Pitfalls | `.traps`, `.trap` | Three brief columns with orange top rules; stack on phones |
| Pipeline | `.architecture`, `.pipeline`, `.stage` | Dark synthesis band; numbered steps, fine rules and directional arrows |
| Compact storage | `.storage`, `.memory-strip` | Diagrammatic buffer cells beside their explanation |
| Parallel work | `.parallel`, `.workers` | Input → worker lanes → output; adapt to vertical mobile layout |
| Adjustable model | `.calculator`, `.control`, `.calculator-result`, `.bars` | Labeled inputs left, one dominant result and shared-scale bars right |
| Comparison | `.table-scroll`, `table` | Quiet horizontal dividers; readable row labels; no decorative gridlines |
| Practical close | `.closing`, `.checklist` | Brief conclusion beside a short numbered action list |
| Sources | `.source`, `.references` | Local citations plus collapsible bibliography |

Use 6–12px corner radii on bounded examples and labs. Keep ordinary prose and chapter groupings unboxed. A grid is useful for genuinely parallel concepts, not as the default layout for the entire article.

The reference's dotted background belongs specifically to the node graph; omit it where it adds no meaning. Graphs with more than two children need an adapted layout, not extra children forced into the two-node CSS.

## Interaction contracts

- Buttons use `type="button"`; segmented selections use `aria-pressed`. Do not imply tab semantics without implementing the associated keyboard behavior.
- Highlights update both the source and its explanatory text. Explanations remain available without hover.
- A stepper shows what changed, the current position, and useful state. Back is disabled at the start; the last next button offers replay. Trace tokens should preserve their visual position while advancing.
- Model controls have associated labels, visible values and units. Recompute labels, bars, result, and limiting-resource state together. Explain whether bars share a dynamic scale. Handle equal minima as ties.
- New examples must replace the reference's data and domain-specific descriptions; do not reuse its parser or calculator claims for an unrelated topic.
- Avoid animation unless it helps track change. Never auto-play an explanatory sequence.

## Responsive and accessible behavior

At 900px, stack the main split panels, use two columns for vocabulary and pipeline stages, and reduce heading gutters. At 640px, use one-column reading flow, stack controls/results, and make navigation nonsticky and wrapping. Keep controls at least 44px tall. Test the selected content at 320px and with enlarged text when visual testing is authorized.

The starter inherits the original responsive and print rules. Adapt rules that depend on the number or shape of components: arrows must not point to empty space after wrapping, labels must fit, and diagram text must not shrink into illegibility. Keep each CSS/SVG figure's accessible description in sync with its visible contents.

Use a skip link, a single h1, ordered section headings, real input labels, visible focus, and polite live regions for meaningful updates. Under reduced-motion preferences, disable smooth scrolling and transitions. The static explanation must still communicate the core idea without JavaScript. For printing, hide controls/navigation and preserve useful diagrams and text; expand essential disclosures if required by the content.
