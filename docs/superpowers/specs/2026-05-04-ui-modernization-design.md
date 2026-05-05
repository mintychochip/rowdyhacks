# Hack the Valley UI Modernization — Design Spec

**Date:** 2026-05-04
**Status:** Approved
**Direction:** Raw Hacker Aesthetic (IBM Plex, monochrome, minimal)

## Overview

Modernize the Hack the Valley hackathon platform with a clean, developer-first aesthetic that avoids the cliché "AI startup" or "SaaS product" look. The design should feel authentic to hacker culture—technical, minimal, and not trying too hard.

## Design Principles

1. **Monochrome palette** — Black, white, grays only. No accent colors, no gradients, no glows.
2. **IBM Plex typography** — Sans for UI, Mono for code/data. Neutral and functional.
3. **Sharp geometry** — 4px border radius maximum. No pill shapes, no excessive rounding.
4. **Straightforward language** — "Get Ticket" not "Register Now". No marketing speak.
5. **Information density** — Show what matters, hide what doesn't. Respect screen real estate.

## Color System

### Light Mode
| Token | Value | Usage |
|-------|-------|-------|
| `bg` | `#ffffff` | Page background |
| `bg-subtle` | `#f7f7f7` | Subtle backgrounds, headers |
| `text-primary` | `#000000` | Headlines, important text |
| `text-secondary` | `#444444` | Body copy, descriptions |
| `text-muted` | `#666666` | Labels, metadata |
| `border` | `#e0e0e0` | Dividers, borders |
| `link` | `#0066cc` | Interactive text |

### Dark Mode
| Token | Value | Usage |
|-------|-------|-------|
| `bg` | `#0a0a0a` | Page background |
| `bg-subtle` | `#141414` | Subtle backgrounds, headers |
| `text-primary` | `#ffffff` | Headlines, important text |
| `text-secondary` | `#999999` | Body copy, descriptions |
| `text-muted` | `#666666` | Labels, metadata |
| `border` | `#333333` | Dividers, borders |
| `link` | `#66b3ff` | Interactive text (blue for contrast) |

## Typography

### Font Families
- **UI/Body:** `IBM Plex Sans, -apple-system, sans-serif`
- **Code/Data:** `IBM Plex Mono, monospace`

### Type Scale
| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| H1 | 42px | 600 | 1.1 | Page headlines |
| H2 | 32px | 600 | 1.2 | Section headers |
| H3 | 20px | 600 | 1.3 | Card titles |
| Body | 16px | 400 | 1.6 | Paragraphs |
| Small | 14px | 400 | 1.5 | Secondary text |
| Label | 12px | 500 | 1.0 | Uppercase labels (mono) |
| Code | 13px | 400 | 1.5 | Code blocks, data |

## Components

### Buttons

**Primary Button:**
- Background: `text-primary` color (black in light, white in dark)
- Text: Inverse of background
- Padding: 12px 24px
- Border radius: 4px
- Font: 14px, weight 500
- Hover: Opacity 0.85

**Text Link:**
- Color: `link` token
- No underline default
- Underline on hover
- Font: 14px

### Cards
- Background: `bg` or `bg-subtle`
- Border: 1px solid `border`
- Border radius: 4px
- Padding: 24px
- No shadows (flat design)

### Navigation

**Top Bar:**
- Border bottom: 1px solid `border`
- Height: auto (content-based)
- Padding: 16px 0

**Brand:**
- Logo: 8px square dot (currentColor)
- Text: 16px, weight 600
- Gap: 10px

**Nav Links:**
- Font: 14px
- Color: `text-secondary`
- Hover: `text-primary`
- Gap: 24px

### Code Blocks
- Font: IBM Plex Mono
- Background: `#f5f5f5` (light), `#111` (dark)
- Border: 1px solid `border`
- Border radius: 4px
- Header: 11px, muted text, subtle background
- Body: 13px, secondary text color
- Prompt: `#22c55e` (green)

## Migration Plan

### Phase 1: Theme System
1. Update `theme.ts` with new color tokens
2. Add `ThemeProvider` for light/dark toggle
3. Replace all hardcoded colors with theme tokens

### Phase 2: Typography
1. Add IBM Plex font imports
2. Update global styles
3. Replace all typography with new scale

### Phase 3: Components
1. Update Button, Card, Input components
2. Redesign Navigation (Layout.tsx)
3. Add CodeBlock component

### Phase 4: Pages
1. Redesign HomePage (landing experience)
2. Update Dashboard and internal pages
3. Polish responsive behavior

## Implementation Notes

- Keep existing functionality—only change visuals
- Maintain dark mode as default (current user preference)
- Add light mode toggle in user settings
- Ensure accessibility: WCAG 2.1 AA contrast ratios
- Test on mobile—many hackers use phones for check-in
