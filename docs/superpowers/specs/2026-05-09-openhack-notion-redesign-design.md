# OpenHack — Notion Warm Minimalism Redesign

## Overview

Redesign the entire OpenHack application from the current dark rocket/space theme to a light, warm minimalism inspired by Notion's design system.

The app currently uses dark space backgrounds (`#060913`) with flame-orange and star-gold accents. This redesign flips to a light-mode-only warm palette: white and cream surfaces, near-black text, Notion Blue (`#0075de`) as the singular accent, whisper-thin borders, and soft multi-layer shadows.

## Goals

- Make the platform feel approachable and workspace-grade
- Differentiate from generic dark-hackathon templates
- Apply consistently across all 25+ pages and 40+ components
- Preserve all existing functionality — pure visual migration

## Decisions

- **Light mode only:** The app will be light-mode-only. Dark mode is deprecated.
- **Notion Blue is the only saturated accent:** `#0075de` for CTAs, links, focus rings, badges. No orange, no gold in the UI chrome.
- **Section alternation rhythm:** White (`#ffffff`) sections alternate with Warm White (`#f6f5f4`) sections for visual cadence.
- **Inter as primary font:** Notion uses `NotionInter` (modified Inter). We use standard Inter from Google Fonts as the closest available equivalent.

## Color System

### Backgrounds

| Token | Hex | Usage |
|---|---|---|
| `bg` | `#ffffff` | Page background |
| `bgWarm` | `#f6f5f4` | Alternating section backgrounds, subtle surfaces |
| `bgDark` | `#31302e` | Dark feature sections (sparingly) |
| `bgCard` | `#ffffff` | Card surfaces |
| `bgInput` | `#ffffff` | Input backgrounds |
| `bgHover` | `rgba(0,0,0,0.05)` | Hover states on buttons, rows |

### Text

| Token | Hex | Usage | Contrast |
|---|---|---|---|
| `textPrimary` | `rgba(0,0,0,0.95)` | Headings, body text | ~18:1 AAA |
| `textSecondary` | `#615d59` | Descriptions, labels | ~5.5:1 AA |
| `textMuted` | `#a39e98` | Placeholders, disabled | ~3.2:1 (exempt) |
| `textInverse` | `#ffffff` | Text on dark surfaces |

### Brand & Interactive

| Token | Hex | Usage |
|---|---|---|
| `accentPrimary` | `#0075de` | Primary buttons, links, active states |
| `accentHover` | `#005bab` | Button/link hover |
| `accentFocus` | `#097fe8` | Focus rings |
| `accentSubtle` | `#f2f9ff` | Badge backgrounds, tinted surfaces |

### Semantic

| Token | Hex | Usage |
|---|---|---|
| `success` | `#1aae39` | Success states, live badges |
| `warning` | `#dd5b00` | Warning states, pending |
| `error` | `#ef4444` | Error states, destructive (retained) |

### Borders

| Token | Value | Usage |
|---|---|---|
| `borderWhisper` | `1px solid rgba(0,0,0,0.1)` | Standard card/input borders |
| `borderLight` | `1px solid #dddddd` | Input borders |
| `borderStrong` | `1px solid rgba(0,0,0,0.2)` | Elevated borders |

## Legacy Token Mapping

The existing codebase imports legacy constants from `theme.ts`. Map them as re-exports:

| Legacy Export | New Value | Notes |
|---|---|---|
| `PAGE_BG` | `#ffffff` | |
| `CARD_BG` | `#ffffff` | |
| `INPUT_BG` | `#ffffff` | |
| `NAV_BG` | `#ffffff` | |
| `EXPANDED_BG` | `#f6f5f4` | |
| `TABLE_HOVER` | `rgba(0,0,0,0.05)` | |
| `PRIMARY` | `#0075de` | Notion Blue replaces brand blue |
| `PRIMARY_HOVER` | `#005bab` | |
| `CYAN` | `#0075de` | Retired, mapped to Notion Blue |
| `TEXT_PRIMARY` | `rgba(0,0,0,0.95)` | |
| `TEXT_SECONDARY` | `#615d59` | |
| `TEXT_MUTED` | `#a39e98` | |
| `BORDER` | `rgba(0,0,0,0.1)` | |
| `SUCCESS` | `#1aae39` | Notion green |
| `WARNING` | `#dd5b00` | Notion orange |
| `ERROR` | `#ef4444` | Retained |

## Typography

| Level | Font | Size | Weight | Line Height | Letter Spacing |
|---|---|---|---|---|---|
| Display | Inter | 48px | 700 | 1.00 | -1.5px |
| H1 | Inter | 32px | 700 | 1.10 | -0.5px |
| H2 | Inter | 24px | 600 | 1.20 | normal |
| H3 | Inter | 20px | 600 | 1.30 | normal |
| Body | Inter | 16px | 400 | 1.50 | normal |
| Small | Inter | 14px | 400 | 1.43 | normal |
| Label | Inter | 12px | 500 | 1.33 | 0.125px |
| Mono | JetBrains Mono | 13px | 500 | 1.50 | normal |

**Font import (update `index.html`):**
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
```

## Component Styles

### Buttons

**Primary (Blue):**
- Background: `#0075de`
- Text: white
- Border-radius: 4px
- Padding: 8px 16px
- Hover: `#005bab`
- Active: `transform: scale(0.95)`
- Focus: `2px solid #097fe8` outline

**Secondary:**
- Background: `rgba(0,0,0,0.05)`
- Text: `rgba(0,0,0,0.95)`
- Border-radius: 4px
- Padding: 8px 16px
- Hover: `rgba(0,0,0,0.08)`

**Ghost:**
- Background: transparent
- Text: `rgba(0,0,0,0.95)`
- Hover: underline

### Cards
- Background: `#ffffff`
- Border: `1px solid rgba(0,0,0,0.1)`
- Border-radius: 12px
- Padding: 24px
- Shadow: `rgba(0,0,0,0.04) 0px 4px 18px, rgba(0,0,0,0.027) 0px 2px 8px, rgba(0,0,0,0.02) 0px 1px 3px, rgba(0,0,0,0.01) 0px 0px 1px`

**Elevated variant:**
- Shadow: deep 5-layer stack (max opacity 0.05, up to 52px blur)

### Inputs
- Background: `#ffffff`
- Border: `1px solid #dddddd`
- Border-radius: 4px
- Padding: 8px 12px
- Text: `rgba(0,0,0,0.95)`
- Placeholder: `#a39e98`
- Focus: `1px solid #0075de` + `0 0 0 3px rgba(0,117,222,0.15)`
- Error: `1px solid #ef4444` + `0 0 0 3px rgba(239,68,68,0.15)`

### Badges
- Blue: `#f2f9ff` bg, `#097fe8` text, 9999px radius, 4px 8px padding, 12px font
- Success: `rgba(26,174,57,0.2)` bg, `#108c3d` text
- Warning: `rgba(221,91,0,0.15)` bg, `#dd5b00` text
- Error: `rgba(239,68,68,0.15)` bg, `#ef4444` text

### Navigation
- Background: `#ffffff`
- Border-bottom: `1px solid rgba(0,0,0,0.1)`
- Links: Inter 15px weight 500, `rgba(0,0,0,0.95)`
- Active link: `#0075de`
- CTA: blue pill button

## Global CSS Updates

**Body:**
```css
body {
  background: #ffffff;
  color: rgba(0, 0, 0, 0.95);
  font-family: 'Inter', -apple-system, sans-serif;
}
```

**Selection:**
```css
::selection {
  background: rgba(0, 117, 222, 0.2);
  color: rgba(0, 0, 0, 0.95);
}
```

**Scrollbar (light):**
```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.15); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.25); }
```

## Page-Specific Strategy

Rather than redesigning 25 pages individually, apply the theme globally and spot-fix:

1. **Global tokens** (`theme.ts`, `index.css`, `Layout.tsx`) — changes propagate everywhere
2. **Spot-fix hardcoded colors** in `frontend/src/pages/*` — search for `#060913`, `#0f172a`, `#f97316`, `#fbbf24`, `#2563eb`, `#1a2542`
3. **Critical pages to verify:** HomePage, Dashboard, AuthPage, AnalyzePage, AssistantPage

### Auth Page
- White background, near-black text
- Inputs with `#dddddd` border, blue focus glow
- Submit button: blue primary
- OAuth buttons: secondary style (`rgba(0,0,0,0.05)` bg)

### Dashboard
- White page background
- Cards with whisper borders and soft shadows
- Blue primary actions (Save, Edit)
- Green success badges for live events
- Tables with `rgba(0,0,0,0.05)` hover rows

### HomePage
- White hero section
- Display heading at 48px Inter weight 700, -1.5px tracking
- Blue CTA button
- Alternating warm white sections for features/schedule

### Assistant Page
- White page background
- User messages: `#f6f5f4` background with whisper border
- AI messages: `#ffffff` background
- Code blocks: `#f6f5f4` with JetBrains Mono

## Files to Modify

| File | Changes |
|---|---|
| `frontend/index.html` | Replace Space Grotesk with Inter font import |
| `frontend/src/theme.ts` | Complete color/typography replacement, light tokens, legacy re-exports |
| `frontend/src/index.css` | Body bg white, selection, scrollbar light, remove dark overrides |
| `frontend/src/components/Layout.tsx` | Navbar: white bg, near-black text, blue CTA, remove dark glassmorphism |
| `frontend/src/pages/*.tsx` | Spot-fix hardcoded dark hex colors |

## Migration Plan

1. **index.html:** Update font `<link>` to Inter + JetBrains Mono. Update theme-color meta to `#ffffff`.
2. **theme.ts:** Replace all tokens with Notion equivalents. Map legacy exports to new values. Remove dark-mode-only code (`getColors`, `ThemeMode`, shadow glows, star fields, orange/gold tokens).
3. **index.css:** Update body background to white, `::selection` to blue tint, scrollbar to light, remove any dark-theme hardcoded colors.
4. **Layout.tsx:** Restyle navbar for light theme (white bg, border-bottom, remove backdrop-blur, remove flame orange logo glow).
5. **Spot-check pages:** Search `frontend/src/pages/` for hardcoded hexes (`#060913`, `#0f172a`, `#f97316`, `#fbbf24`, `#2563eb`, `#1a2542`, `rgba(37,99,235`, `rgba(249,115,22`, `rgba(251,191,36`) and replace with theme tokens.
6. **Verify:** HomePage, Dashboard, AuthPage, AnalyzePage, AssistantPage render correctly.

## Accessibility

- `textPrimary` on white: ~18:1 ratio (WCAG AAA)
- `textSecondary` on white: ~5.5:1 ratio (WCAG AA)
- `textMuted` is exempt — placeholders and disabled states only
- Focus states: 2px solid blue outline + soft shadow ring
- `prefers-reduced-motion`: disable `scale()` active transforms
