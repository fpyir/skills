---
name: field-guide-explainer
description: >-
  Create beautiful self-contained HTML explainers in a technical field-guide style:
  forest-green panels, lime accents, editorial typography, numbered chapters,
  annotated examples, and purposeful interactive diagrams. Use for visual guides,
  technical walkthroughs, and single-page educational articles, especially when
  asked to reuse the IFC explainer design. Not a general dashboard or application UI skill.
---

# Field Guide Explainer

Turn a subject into a readable, visual single-page explanation using the design system of the user-approved IFC guide. Preserve its recognizable composition and visual language while letting the subject determine the content and interactions.

## Resources

- Read [references/design-system.md](references/design-system.md) before designing. It records the palette, type, spacing, layout, component choices, and responsive behavior.
- Start a new standalone page from [assets/starter.html](assets/starter.html). It contains the original stylesheet and a neutral, accessible page skeleton. Copy it to the requested output location before editing; never modify the installed skill while using it.
- Use [assets/ifc-reference.html](assets/ifc-reference.html) as the canonical completed example. Inspect only the relevant sections when borrowing file highlights, token traces, the graph, or the calculator. Its subject matter and numerical assumptions are examples, not reusable facts.

## Shape the explanation

Identify the reader's question and the understanding they should leave with. Build a short narrative arc: orient them with a concrete example, explain the pieces, follow a mechanism, and discuss implications or limits. Adapt the section count and order; do not force every subject into the IFC page's five chapters.

Preserve the characteristic silhouette:

- A quiet paper-colored navigation bar with a compact monogram and a few chapter anchors.
- A forest-green opening with a large, tightly set title; one restrained serif-italic emphasis; concise context; and an example paired with a diagram.
- A light reading surface with numbered sections, generous spacing, fine rules, and diagrams integrated into the explanation.
- Where useful, one dark synthesis section explaining the architecture or whole mechanism.
- A short practical close and source notes, rather than a marketing call to action.

The first viewport should already teach something. Avoid a giant title-only hero, generic feature cards, decorative stock imagery, or empty badges. Use diagrams and typography as the visual identity.

## Build the page

Default to one portable `.html` file with inline CSS and JavaScript, system fonts, and no runtime dependencies. It should work when opened directly from disk. External citation links are fine; do not make the page depend on a CDN, server, or network request. Respect an explicit request to integrate into an existing app instead.

Use the starter's tokens and components, adapting them rather than inventing a second design system. Keep subject-specific labels, favicon, page title, metadata, navigation, diagram text, and footer consistent. Replace every `{{...}}` slot and remove template comments before delivery. Do not ship copied IFC examples, sample dates, dead styles/scripts, unused controls, or invented author branding.

Use semantic HTML and real text for content. Use CSS or SVG for diagrams. Do not use screenshots of text, emoji as a substitute for diagram structure, or require hover to reveal essential information. Keep code readable and allow long tokens to wrap; place genuinely wide comparison tables in a labeled overflow container.

Choose interactions only when they explain a relationship:

- Region selection for mapping source content to an explanation.
- A stepper for a finite sequence, with visible state and back/replay behavior.
- A calculator when the underlying model is meaningful and supported.

A static diagram is preferable when it communicates the same point more clearly. Do not add sliders, tabs, or metrics merely to imitate the reference. Keep explanatory controls local; no persistence, uploads, connectors, or deployment unless the task calls for them.

Distinguish illustrative models from measured results. State assumptions and units next to calculators; derive every displayed result and mark from the same inputs. Preserve ties, edge cases, and consistent scales. Clearly label curated demonstrations that are not general parsers or simulators. Keep sourced claims linked near the relevant explanation, with full references below when helpful.

## Verify and deliver

Follow the task's testing instructions, including any rule reserving manual browser review for the user. Opening a preview for the user is not permission to conduct manual UI testing yourself.

For a standalone file, check HTML nesting, unique IDs, internal links, JavaScript syntax, referenced selectors, and absence of external runtime assets. Exercise nontrivial interaction logic programmatically: step boundaries/replay, selector updates, formulas, ties, and range endpoints. Check narrow-width layouts, keyboard accessibility, and enlarged text visually only when authorized; otherwise state that visual review remains with the user. Do not claim a DOM-only check establishes visual correctness.

Keep motion optional and respect reduced-motion preferences. Preserve visible keyboard focus, associated input labels, and live text for important state changes. Give static diagrams accessible descriptions. Make the static article readable without JavaScript and avoid printing inert controls as primary content.

Return a concise link to the completed HTML and, when available, open it for user review using the environment's file or preview mechanism. Do not publish externally just because this skill was invoked.
