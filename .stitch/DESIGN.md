# Design System: Almaty Mobility — Quiet Evidence Dossier
**Project ID:** 15089572861475027317

## 1. Visual Theme & Atmosphere

The interface is a calm civic research dossier, not a control-room dashboard and not a marketing page. It should feel like a carefully typeset university case study combined with an auditable municipal decision record: restrained, precise, spacious, and trustworthy.

Use warm paper-like surfaces, charcoal typography, hairline dividers, editorial headings, compact evidence labels, and one desaturated sage accent. The map remains visually unchanged and appears as a framed supporting exhibit rather than the dominant product surface. Avoid gradients, glass effects, bright colors, oversized rounded cards, heavy shadows, decorative illustrations, and dashboard clutter.

## 2. Color Palette & Roles

- **Canvas / Warm Paper** (`#F5F3EE`): default page background.
- **Primary Surface** (`#FCFBF8`): cards, tables, navigation, and evidence panels.
- **Raised Surface** (`#FFFFFF`): focused actions and the most important summary block.
- **Primary Ink** (`#1D221F`): headings, key metrics, primary navigation.
- **Secondary Ink** (`#656B66`): descriptions, captions, secondary metadata.
- **Quiet Ink** (`#6B716C`): timestamps, tertiary notes, and technical labels; darkened from the initial exploration to retain small-text contrast on the warm canvas.
- **Hairline Border** (`#DCDDD7`): all card, table, and section boundaries.
- **Strong Border** (`#BFC4BE`): focused or selected boundaries only.
- **Sage Accent** (`#526A5B`): links, selected states, positive deltas, and the single primary action.
- **Sage Wash** (`#E7EDE8`): real-data and completed-state backgrounds.
- **Proxy Sand** (`#EFE8DA`): proxy labels and evidence caveats.
- **Proxy Ink** (`#745F38`): text on proxy labels.
- **Risk Wash** (`#F2E8E5`): blocked or missing-evidence states.
- **Risk Ink** (`#815B52`): blocked-state text; never use vivid red.
- **Map Frame** (`#171C19`): quiet dark border around the unchanged map.

Color is scarce. Most of the interface must remain warm monochrome; sage, sand, and muted risk tones communicate evidence state only.

## 3. Typography Rules

- **Editorial headings:** `Iowan Old Style`, `Baskerville`, `Palatino Linotype`, `Book Antiqua`, `Georgia`, serif. Use 600 weight, tight tracking from `-0.035em` to `-0.02em`, and line-height between `1.02` and `1.15`.
- **Interface and body:** `Avenir Next`, `SF Pro Text`, `Helvetica Neue`, system sans-serif. Use regular 400–500 weights and generous line-height from `1.5` to `1.65`.
- **Evidence metadata:** `SFMono-Regular`, `SF Mono`, `IBM Plex Mono`, `Menlo`, monospace. Use 11–12px, medium weight, and modest positive tracking.
- Hero headings should be visually significant but never promotional: `clamp(2.5rem, 6vw, 5.5rem)` with a controlled line length.
- Use sentence case. Uppercase is reserved for tiny evidence labels and table column labels.
- Numerical comparisons use tabular numerals and align consistently.

## 4. Component Styling

- **Header:** 56–64px tall, warm translucent surface with a subtle backdrop blur, one hairline bottom border, compact wordmark, and no shadow.
- **Navigation:** quiet text links with an underline or 2px sage rule for the active item. Minimum 44px target size.
- **Primary button:** charcoal or sage background, off-white text, 6px radius, no shadow, 44–48px minimum height. Active press may scale to `0.985`.
- **Secondary button:** transparent or white surface, hairline border, charcoal text, 6px radius.
- **Cards:** flat surfaces, 1px hairline border, 8–12px radius maximum, 24–32px padding. No decorative elevation.
- **Status labels:** small rounded tags are allowed for evidence states only. Use muted washes, 11px monospace type, and visible text labels; never rely on color alone.
- **KPI rows:** editorial ledger treatment with horizontal dividers, large tabular values, compact source/claim metadata, and no oversized dashboard tiles.
- **Evidence lists:** use numbered rows, understated square markers, or hairline separators rather than icon-heavy cards.
- **Accordions / details:** borderless container with a single divider; use a text disclosure and native marker styling.
- **Map exhibit:** retain all map visuals and data. Place it inside a crisp frame with a short caption, evidence label, and attribution. Do not recolor map layers.
- **Tables:** white or paper surface, sticky header only where useful, 1px separators, keyboard-focusable horizontal overflow container, and responsive stacked summaries on narrow screens.
- **Loading / error / empty states:** centered editorial message, one plain action, no illustrations or animated spinners larger than 24px.

## 5. Layout Principles

- Desktop content width: `min(100% - 48px, 1320px)`; reading columns should not exceed `72ch`.
- Use a 12-column desktop grid, a 6-column tablet grid, and one column below 720px.
- Major section spacing: 88–128px desktop, 64–80px mobile.
- Internal stack rhythm: 8px, 12px, 16px, 24px, 32px, 48px.
- The dossier first viewport should communicate, in order: case identity, controlled change `36 s → 32 s`, evidence level `proxy`, recommendation `request more evidence`, core KPI comparison, and a direct path to evidence/downloads.
- Below the fold, group content into three quiet chapters: **Result**, **Evidence**, and **Reproduce**.
- The supporting map may occupy at most one half of a desktop chapter and must stack below the written result on mobile.
- Sandbox must retain the full map engine but remove visual competition around it: one compact disclaimer rail above the map, then the existing map viewport. On mobile, ancillary controls should collapse into deliberate drawers or stacked panels rather than overlapping the map.
- Preserve visible focus states, 44px pointer targets, reduced-motion behavior, print readability, English-only presentation, and claim labels exactly as supported by evidence.

## 6. Motion & Interaction

- Keep motion nearly invisible: 160–240ms color/opacity transitions and optional 8px content entry movement.
- Respect `prefers-reduced-motion` and disable nonessential transitions.
- Do not animate layout dimensions, map position, or evidence values for decoration.
- Hover should clarify interactivity, never create floating cards or bright glows.

## 7. Content Guardrails

- Current dossier and KPI values are `proxy`.
- Road geometry is a non-live `real-data` snapshot.
- Workflow and procurement package are `demo`.
- Never present unconditional funding as available at the current evidence level.
- Do not describe the sandbox as live traffic, calibrated evidence, or an autonomous recommendation.

## 8. Stitch References

- Desktop dossier screen: `0d72f514f7584f7b8d1216db8fe8ca3e`.
- Mobile dossier screen: `55c5a36e283f480f8b369dbf87f227ea`.
- Generated design-system asset: `assets/3f9b00a79b614b28bef6d531b40f64bb`.
- Downloaded reference exports live in `.stitch/designs/`; implementation adapts their hierarchy to the existing evidence contracts and keeps the map engine unchanged.
