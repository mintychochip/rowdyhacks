---
version: alpha
name: Rowdy
description: CSUB hackathon submission integrity checker — dark, data-dense dashboard with gold accents

colors:
  page: "#080c1a"
  card: "#0d1433"
  input: "#111a3e"
  nav: "#080c1a"
  expanded: "#080c1a"
  table-hover: "#0d1433"

  primary: "#1a5ce7"
  primary-hover: "#003db8"
  primary-disabled: "#0a2266"

  gold: "#FFC72C"

  text-primary: "#e8e8f0"
  text-secondary: "#b0b8d0"
  text-muted: "#8088a0"
  text-dim: "#556666"
  text-white: "#ffffff"

  border: "#1a2040"
  border-light: "#2a3050"
  input-border: "#333344"

  success: "#00c853"
  warning: "#FFC72C"
  error: "#ff4444"
  error-text: "#ff6b6b"
  info: "#3b82f6"
  orange: "#ff9800"

  status-pending: "#f59e0b"
  status-accepted: "#10b981"
  status-rejected: "#ef4444"
  status-checked-in: "#3b82f6"

  gold-bg10: "#FFC72C10"
  gold-bg20: "#FFC72C20"
  primary-bg20: "#1a5ce720"
  success-bg10: "#00c85310"
  success-bg20: "#00c85320"
  warning-bg10: "#FFC72C10"
  warning-bg20: "#FFC72C20"
  warning-border30: "#FFC72C30"
  error-bg10: "#ff444410"
  error-bg20: "#ff444420"
  error-border30: "#ff444430"
  info-bg20: "#3b82f620"

typography:
  heading-xl:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  heading-lg:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 22px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  heading-md:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.4
  body-lg:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.06em"
  score-lg:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.0
    letterSpacing: "-0.02em"
  mono-data:
    fontFamily: "'Space Mono', 'JetBrains Mono', 'Fira Code', monospace"
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
    fontFeature: "'tnum'"

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px

rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px

components:
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-white}"
    rounded: "{rounded.md}"
    typography: "{typography.body-lg}"
    padding: 12px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  input:
    backgroundColor: "{colors.input}"
    textColor: "{colors.text-white}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
    border: "1px solid {colors.input-border}"
  chip:
    rounded: "{rounded.sm}"
    typography: "{typography.label-caps}"
  header-nav:
    backgroundColor: "{colors.nav}"
    border: "1px solid {colors.border}"
  data-table:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.md}"
  table-row-hover:
    backgroundColor: "{colors.table-hover}"
  badge-success:
    backgroundColor: "{colors.success-bg10}"
    textColor: "{colors.success}"
    rounded: "{rounded.lg}"
  badge-warning:
    backgroundColor: "{colors.warning-bg10}"
    textColor: "{colors.warning}"
    rounded: "{rounded.lg}"
  badge-error:
    backgroundColor: "{colors.error-bg10}"
    textColor: "{colors.error-text}"
    rounded: "{rounded.lg}"
---

## Overview

Rowdy is a dark-theme, data-dense dashboard for judging hackathon submissions. The brand anchors to CSUB's deep blue (`#001e40`) and gold (`#FFC72C`), brightened for dark backgrounds. The interface alternates between list/table views (submissions, results) and focused drill-down views (check details, narrative reports).

Design philosophy: **utilitarian but polished** — fast scanning, clear severity hierarchy, minimal chrome, gold reserved for brand moments (logo, key accents).

## Colors

### Surface layering (darkest → lightest)

The dark background uses four depth layers. Each layer brightens slightly to create subtle elevation without borders:

| Token | Value | Usage |
|-------|-------|-------|
| `page` | `#080c1a` | Full-page background |
| `nav` | `#080c1a` | Top navigation bar (same as page — border-separated) |
| `card` | `#0d1433` | Cards, table containers, modals |
| `input` | `#111a3e` | Form inputs, search fields |
| `table-hover` | `#0d1433` | Hover state on table rows |

### Accent

| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#1a5ce7` | Primary CTA buttons, links, active states |
| `primary-hover` | `#003db8` | Button hover (darker blue) |
| `gold` | `#FFC72C` | Logo, brand accents — **never** as a functional element |

### Text

Four-state hierarchy from white to nearly invisible:

| Token | Value | Usage |
|-------|-------|-------|
| `text-primary` | `#e8e8f0` | Body text, headings |
| `text-secondary` | `#b0b8d0` | Supporting text, labels |
| `text-muted` | `#8088a0` | Tertiary info, placeholders |
| `text-dim` | `#556666` | Very low emphasis (rare) |
| `text-white` | `#ffffff` | Text on primary buttons |

### Semantic

| Token | Value | Meaning |
|-------|-------|---------|
| `success` | `#00c853` | Pass, accepted, on-track |
| `warning` | `#FFC72C` | Attention needed (reuses gold for semantic alignment) |
| `error` | `#ff4444` | Fail, rejected, blocked |
| `error-text` | `#ff6b6b` | Lighter red for text on dark backgrounds |
| `info` | `#3b82f6` | Informational highlights |
| `orange` | `#ff9800` | Intermediate severity |

### Status badges

| Token | Value | Meaning |
|-------|-------|---------|
| `status-pending` | `#f59e0b` | Awaiting action |
| `status-accepted` | `#10b981` | Approved |
| `status-rejected` | `#ef4444` | Denied |
| `status-checked-in` | `#3b82f6` | Present / attended |

### Alpha-blend backgrounds

Tokens suffixed `bg10`/`bg20`/`border30` are hex colors with baked-in alpha for consistent layering without CSS opacity:

| Token | Hex |
|-------|-----|
| `gold-bg10` | `#FFC72C10` |
| `gold-bg20` | `#FFC72C20` |
| `primary-bg20` | `#1a5ce720` |
| `success-bg10` | `#00c85310` |
| `success-bg20` | `#00c85320` |
| `warning-bg10` | `#FFC72C10` |
| `warning-bg20` | `#FFC72C20` |
| `warning-border30` | `#FFC72C30` |
| `error-bg10` | `#ff444410` |
| `error-bg20` | `#ff444420` |
| `error-border30` | `#ff444430` |
| `info-bg20` | `#3b82f620` |

## Typography

Two font families: **Space Grotesk** for UI, headings, body, and labels; **Space Mono** for data (scores, tables, code, tokens). Both loaded from Google Fonts with `display=swap`.

### Hierarchy

| Token | Family | Size | Weight | Line | Usage |
|-------|--------|------|--------|------|-------|
| `score-lg` | Grotesk | 32px | 700 | 1.0 | Large score display (hero) |
| `heading-xl` | Grotesk | 28px | 700 | 1.2 | Page titles |
| `heading-lg` | Grotesk | 22px | 700 | 1.3 | Section headers |
| `heading-md` | Grotesk | 16px | 600 | 1.4 | Card headers, sub-section titles |
| `body-lg` | Grotesk | 15px | 400 | 1.5 | Default body text |
| `body-sm` | Grotesk | 13px | 400 | 1.5 | Secondary text, descriptions |
| `label-caps` | Grotesk | 12px | 600 | 1.3 | Uppercase labels, badges, chips |
| `mono-data` | Mono | 14px | 500 | 1.4 | Scores, tokens, git SHAs, table data |

### Rules

- **Never** use a weight below 400 — thin text disappears on dark backgrounds
- **Tabular nums** (`tnum` feature) on `mono-data` so columns of numbers align
- `letterSpacing: -0.02em` on large headings — tightens the geometric grotesk without looking compressed
- `letterSpacing: 0.06em` on `label-caps` — improves legibility of all-caps labels

## Layout

4px base unit. All spacing values snap to multiples of 4.

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4px | Tight gaps, icon-to-label spacing |
| `sm` | 8px | Element gaps, padding in compact rows |
| `md` | 16px | Standard section/component padding |
| `lg` | 24px | Card padding, section separation |
| `xl` | 48px | Major page section breaks |

### Rules

- **No arbitrary spacing** — values not in the scale are a bug
- Card internal padding defaults to `lg` (24px)
- Stacked sections use `md` (16px) gaps unless visually distinct (in which case `xl`)

## Elevation & Depth

Three shadow levels create depth on the dark surface without visible borders:

| Level | Shadow | Usage |
|-------|--------|-------|
| Card | `0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)` | Default cards, tables |
| Elevated | `0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)` | Hover cards, dropdowns |
| Modal | `0 8px 32px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.4)` | Dialogs, modals |

### Rules

- **Never** use borders for elevation separation — use shadows or background layer changes
- Borders are reserved for input fields and table dividers only

## Shapes

| Token | Value | Usage |
|-------|-------|-------|
| `sm` | 4px | Inputs, small containers |
| `md` | 8px | Cards, buttons, table containers |
| `lg` | 12px | Large cards, modals |
| `full` | 9999px | Pill badges, status chips, circular avatars |

### Rules

- Buttons use `md` (8px) — enough to feel modern, not so rounded they look playful
- Status badges use `full` for the pill look
- Cards use `md` — sharper than `lg` to keep the data-dense feel

## Components

### Card
```
backgroundColor: card (#0d1433)
rounded: md (8px)
padding: lg (24px)
```
The default container. On hover, apply elevated shadow but keep the same background — don't change color.

### Button (Primary)
```
backgroundColor: primary (#1a5ce7)
textColor: text-white (#ffffff)
rounded: md (8px)
typography: body-lg
padding: 12px
```
Full-width primary CTA. Hover: `primary-hover` (#003db8). Never use gold for buttons — gold is brand-only.

### Input
```
backgroundColor: input (#111a3e)
textColor: text-white (#ffffff)
rounded: sm (4px)
padding: 10px 12px
border: 1px solid input-border (#333344)
```
Form fields. Focus state uses a lighter border (not implemented as token — use `border-light`).

### Navigation
```
backgroundColor: nav (#080c1a)
border: 1px solid border (#1a2040)
```
Top navigation bar. Same background as page, separated by a subtle bottom border. Logo in gold, links in muted.

### Data Table
```
backgroundColor: card (#0d1433)
rounded: md (8px)
```
Row hover: `table-hover` (#0d1433). Header text in `label-caps` style with `text-muted` color. Data cells in `mono-data` where numeric.

### Status Badge
- **Success**: `success-bg10` background, `success` text, `full` rounded
- **Warning**: `warning-bg10` background, `warning` text, `full` rounded
- **Error**: `error-bg10` background, `error-text` text, `full` rounded

### Score Display
Large scores (hero number): `score-lg` typography, `mono-data` font family override for the numerals, gold or primary color depending on context.

## Do's and Don'ts

### Do
- Use Space Grotesk for all UI text, Space Mono for all data
- Snap all spacing to the 4px scale (`xs` through `xl`)
- Use the four-layer surface system for depth (page → card → input)
- Reserve gold for logo and brand accents — never as a functional color
- Use `tnum` on all numeric columns for alignment

### Don't
- Use arbitrary px values outside the spacing scale
- Use borders for elevation — use shadows or background layering
- Mix font families — Grotesk for UI, Mono for data, never a third
- Use gold on interactive elements (buttons, links) — blue is the interactive accent
- Go below 400 font weight — thin text is illegible on dark backgrounds
