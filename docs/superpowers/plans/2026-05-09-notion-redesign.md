# Notion Warm Minimalism Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the entire Hack the Valley frontend from dark rocket/space theme to light Notion-inspired warm minimalism: white/cream surfaces, near-black text, Notion Blue accent, whisper borders, soft shadows.

**Architecture:** Pure visual migration — no functional changes. Global CSS variables and theme tokens drive the look. Four files provide the global foundation; 7 pages need spot-fixes for hardcoded dark colors.

**Tech Stack:** React + Vite + TypeScript, CSS variables, inline styles with CSS var references

---

## File Map

| File | Responsibility |
|---|---|
| `frontend/index.html` | Font imports (Inter, JetBrains Mono), theme-color meta |
| `frontend/src/theme.ts` | All color/typography/spacing/shadow tokens + legacy re-exports |
| `frontend/src/index.css` | CSS custom properties, body/selection/scrollbar/focus styles |
| `frontend/src/components/Layout.tsx` | Sidebar + top bar styling (light theme) |
| `frontend/src/pages/HomePage.tsx` | Hero section, hardcoded dark colors |
| `frontend/src/pages/Dashboard.tsx` | Dashboard cards, hardcoded colors |
| `frontend/src/pages/ApplyPage.tsx` | Registration form, hardcoded colors |
| `frontend/src/pages/RegisterPage.tsx` | Auth form, hardcoded colors |
| `frontend/src/pages/HackathonDetailPage.tsx` | Detail page, hardcoded colors |
| `frontend/src/pages/JudgePortal.tsx` | Judging UI, hardcoded colors |
| `frontend/src/pages/TracksPage.tsx` | Tracks list, hardcoded colors |

---

## Chunk 1: Global Foundation (index.html, index.css, theme.ts)

### Task 1: Update index.html

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Remove Space Grotesk, keep Inter + JetBrains Mono**

Replace the font link:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

- [ ] **Step 2: Update theme-color meta**

Change:
```html
<meta name="theme-color" content="#ffffff" />
```

- [ ] **Step 3: Verify page loads without font errors**

Run: Open http://localhost:5173
Expected: Page loads, Inter font renders correctly (no 404s in network tab for fonts)

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(theme): switch font imports to Inter + JetBrains Mono, update theme-color"
```

---

### Task 2: Rewrite index.css for light theme

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Replace CSS custom properties with light tokens**

Replace the entire `:root` block (lines 6-91) with:
```css
:root {
  /* Backgrounds */
  --bg-base: #ffffff;
  --bg-primary: #ffffff;
  --bg-secondary: #f6f5f4;
  --bg-tertiary: rgba(0, 0, 0, 0.05);
  --bg-elevated: #ffffff;
  --bg-overlay: rgba(0, 0, 0, 0.4);

  /* Text */
  --text-primary: rgba(0, 0, 0, 0.95);
  --text-secondary: #615d59;
  --text-tertiary: #a39e98;
  --text-muted: #a39e98;
  --text-inverse: #ffffff;

  /* Brand Blue (Notion) */
  --accent-primary: #0075de;
  --accent-primary-hover: #005bab;
  --accent-secondary: #005bab;
  --accent-glow: rgba(0, 117, 222, 0.3);
  --accent-subtle: rgba(0, 117, 222, 0.15);

  /* Semantic */
  --success: #1aae39;
  --success-subtle: rgba(26, 174, 57, 0.15);
  --warning: #dd5b00;
  --warning-subtle: rgba(221, 91, 0, 0.15);
  --error: #ef4444;
  --error-subtle: rgba(239, 68, 68, 0.15);
  --info: #0075de;
  --info-subtle: rgba(0, 117, 222, 0.15);

  /* Borders */
  --border-subtle: rgba(0, 0, 0, 0.08);
  --border-default: rgba(0, 0, 0, 0.1);
  --border-strong: rgba(0, 0, 0, 0.2);
  --border-focus: rgba(0, 117, 222, 0.5);

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
  --font-display: 'Inter', -apple-system, sans-serif;

  /* Shadows */
  --shadow-sm: rgba(0, 0, 0, 0.04) 0px 4px 18px, rgba(0, 0, 0, 0.027) 0px 2px 8px;
  --shadow-md: rgba(0, 0, 0, 0.04) 0px 4px 18px, rgba(0, 0, 0, 0.027) 0px 2px 8px, rgba(0, 0, 0, 0.02) 0px 1px 3px;
  --shadow-lg: rgba(0, 0, 0, 0.01) 0px 1px 3px, rgba(0, 0, 0, 0.02) 0px 3px 7px, rgba(0, 0, 0, 0.02) 0px 7px 15px, rgba(0, 0, 0, 0.04) 0px 14px 28px, rgba(0, 0, 0, 0.05) 0px 23px 52px;
  --shadow-glow: 0 0 20px var(--accent-glow);

  /* Transitions */
  --transition-fast: 100ms ease;
  --transition-base: 150ms ease;
  --transition-slow: 250ms ease;
}
```

- [ ] **Step 2: Update body and selection styles**

Replace `body` block (lines 108-115):
```css
body {
  font-family: var(--font-sans);
  background: var(--bg-base);
  color: var(--text-primary);
  line-height: 1.5;
  min-height: 100vh;
  overflow-x: hidden;
}
```

Replace `::selection` block (lines 137-140):
```css
::selection {
  background: rgba(0, 117, 222, 0.2);
  color: var(--text-primary);
}
```

- [ ] **Step 3: Update scrollbar styles**

Replace scrollbar section (lines 142-169):
```css
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

::-webkit-scrollbar-corner {
  background: transparent;
}

* {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}
```

- [ ] **Step 4: Update input styles**

Replace input section (lines 234-254):
```css
input, textarea {
  background: var(--bg-base);
  border: 1px solid #dddddd;
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  transition: all var(--transition-base);
  color: var(--text-primary);
}

input:hover, textarea:hover {
  border-color: var(--border-strong);
}

input:focus, textarea:focus {
  border-color: var(--accent-primary);
  background: var(--bg-base);
  box-shadow: 0 0 0 3px var(--accent-subtle);
}

input::placeholder, textarea::placeholder {
  color: var(--text-muted);
}
```

- [ ] **Step 5: Verify CSS compiles**

Run: `cd frontend && npx vite build --mode development`
Expected: Build succeeds without CSS errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(theme): rewrite CSS variables for Notion light theme"
```

---

### Task 3: Rewrite theme.ts tokens

**Files:**
- Modify: `frontend/src/theme.ts`

- [ ] **Step 1: Replace color tokens**

Replace all color definitions with light Notion tokens. The file should export:
```typescript
// Backgrounds
const bg = '#ffffff';
const bgPrimary = '#ffffff';
const bgSecondary = '#f6f5f4';
const bgTertiary = 'rgba(0, 0, 0, 0.05)';
const bgElevated = '#ffffff';
const bgOverlay = 'rgba(0, 0, 0, 0.4)';

// Text
const textPrimary = 'rgba(0, 0, 0, 0.95)';
const textSecondary = '#615d59';
const textTertiary = '#a39e98';
const textMuted = '#a39e98';
const textInverse = '#ffffff';

// Brand Blue (Notion)
const accentPrimary = '#0075de';
const accentPrimaryHover = '#005bab';
const accentSecondary = '#005bab';
const accentGlow = 'rgba(0, 117, 222, 0.3)';
const accentSubtle = 'rgba(0, 117, 222, 0.15)';

// Semantic
const success = '#1aae39';
const successSubtle = 'rgba(26, 174, 57, 0.15)';
const warning = '#dd5b00';
const warningSubtle = 'rgba(221, 91, 0, 0.15)';
const error = '#ef4444';
const errorSubtle = 'rgba(239, 68, 68, 0.15)';
const info = '#0075de';
const infoSubtle = 'rgba(0, 117, 222, 0.15)';

// Borders
const borderSubtle = 'rgba(0, 0, 0, 0.08)';
const borderDefault = 'rgba(0, 0, 0, 0.1)';
const borderStrong = 'rgba(0, 0, 0, 0.2)';
const borderFocus = 'rgba(0, 117, 222, 0.5)';
```

- [ ] **Step 2: Update CSS_VARS export**

Map the CSS_VARS object to the new light tokens:
```typescript
export const CSS_VARS = {
  '--bg-base': bg,
  '--bg-primary': bgPrimary,
  '--bg-secondary': bgSecondary,
  '--bg-tertiary': bgTertiary,
  '--bg-elevated': bgElevated,
  '--bg-overlay': bgOverlay,

  '--text-primary': textPrimary,
  '--text-secondary': textSecondary,
  '--text-tertiary': textTertiary,
  '--text-muted': textMuted,
  '--text-inverse': textInverse,

  '--accent-primary': accentPrimary,
  '--accent-primary-hover': accentPrimaryHover,
  '--accent-secondary': accentSecondary,
  '--accent-glow': accentGlow,
  '--accent-subtle': accentSubtle,

  '--success': success,
  '--success-subtle': successSubtle,
  '--warning': warning,
  '--warning-subtle': warningSubtle,
  '--error': error,
  '--error-subtle': errorSubtle,
  '--info': info,
  '--info-subtle': infoSubtle,

  '--border-subtle': borderSubtle,
  '--border-default': borderDefault,
  '--border-strong': borderStrong,
  '--border-focus': borderFocus,
} as const;
```

- [ ] **Step 3: Update legacy exports**

Map legacy exports to new values:
```typescript
export const PAGE_BG = bg;
export const CARD_BG = bgElevated;
export const INPUT_BG = bg;
export const NAV_BG = bg;
export const EXPANDED_BG = bgSecondary;
export const TABLE_HOVER = bgTertiary;

export const PRIMARY = accentPrimary;
export const PRIMARY_HOVER = accentPrimaryHover;
export const PRIMARY_DISABLED = textMuted;
export const PRIMARY_BG20 = 'rgba(0, 117, 222, 0.2)';

export const CYAN = accentPrimary;
export const CYAN_BG20 = 'rgba(0, 117, 222, 0.2)';
export const CYAN_BG10 = accentSubtle;

export const TEXT_PRIMARY = textPrimary;
export const TEXT_SECONDARY = textSecondary;
export const TEXT_MUTED = textMuted;
export const TEXT_DIM = textTertiary;
export const TEXT_WHITE = textPrimary;

export const BORDER = borderDefault;
export const BORDER_LIGHT = borderStrong;
export const INPUT_BORDER = '1px solid #dddddd';

export const SUCCESS = success;
export const SUCCESS_BG20 = 'rgba(26, 174, 57, 0.2)';
export const SUCCESS_BG10 = successSubtle;

export const WARNING = warning;
export const WARNING_BG20 = 'rgba(221, 91, 0, 0.2)';
export const WARNING_BG10 = warningSubtle;
export const WARNING_BORDER30 = 'rgba(221, 91, 0, 0.3)';

export const ERROR = error;
export const ERROR_TEXT = error;
export const ERROR_BG20 = 'rgba(239, 68, 68, 0.2)';
export const ERROR_BG10 = errorSubtle;
export const ERROR_BORDER30 = 'rgba(239, 68, 68, 0.3)';

export const INFO = info;
export const INFO_BG20 = 'rgba(0, 117, 222, 0.2)';
export const INFO_BG10 = infoSubtle;

export const ORANGE = '#dd5b00';
export const ORANGE_BG20 = 'rgba(221, 91, 0, 0.2)';
export const ORANGE_BG10 = warningSubtle;

export const GOLD = '#fbbf24';
export const GOLD_BG20 = 'rgba(251, 191, 36, 0.2)';
export const GOLD_BG10 = 'rgba(251, 191, 36, 0.1)';

export const STATUS_PENDING = warning;
export const STATUS_ACCEPTED = success;
export const STATUS_REJECTED = error;
export const STATUS_CHECKED_IN = info;
```

- [ ] **Step 4: Update typography tokens**

Replace TYPO object. Display uses Inter 700, H1 uses Inter 700, etc. Remove `font-display` references (Space Grotesk).

- [ ] **Step 5: Update shadow tokens**

Replace SHADOW with soft light shadows:
```typescript
export const SHADOW = {
  sm: 'rgba(0, 0, 0, 0.04) 0px 4px 18px',
  md: 'rgba(0, 0, 0, 0.04) 0px 4px 18px, rgba(0, 0, 0, 0.027) 0px 2px 8px',
  lg: 'rgba(0, 0, 0, 0.01) 0px 1px 3px, rgba(0, 0, 0, 0.02) 0px 3px 7px, rgba(0, 0, 0, 0.02) 0px 7px 15px, rgba(0, 0, 0, 0.04) 0px 14px 28px, rgba(0, 0, 0, 0.05) 0px 23px 52px',
  glow: '0 0 20px rgba(0, 117, 222, 0.3)',
} as const;
```

- [ ] **Step 6: Remove dark-mode-only code**

Delete `getColors(mode)` and `ThemeMode` type. Remove orange/gold glow tokens from theme.ts.

- [ ] **Step 7: Verify build**

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors

- [ ] **Step 8: Commit**

```bash
git add frontend/src/theme.ts
git commit -m "feat(theme): rewrite theme.ts with Notion light tokens"
```

---

## Chunk 2: Layout Component

### Task 4: Restyle Layout.tsx for light theme

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Update ROLE_LABELS colors**

Replace lines 8-12:
```typescript
const ROLE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  organizer: { label: 'Organizer', color: '#0075de', bg: 'rgba(0, 117, 222, 0.12)' },
  judge: { label: 'Judge', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)' },
  participant: { label: 'Participant', color: '#1aae39', bg: 'rgba(26, 174, 57, 0.12)' },
};
```

- [ ] **Step 2: Update root layout background**

Line 234: change `background: 'var(--bg-base)'` → stays the same (CSS var handles it)
Line 234: change `color: 'var(--text-primary)'` → stays the same

- [ ] **Step 3: Update sidebar background**

Line 260: change `background: 'var(--bg-secondary)'` → `background: '#f6f5f4'`
Line 261: change `borderRight: '1px solid var(--border-subtle)'` → stays same

- [ ] **Step 4: Update logo colors**

Line 290-291: Remove the orange flame color and glow:
```typescript
color: '#0075de',
// remove filter: drop-shadow(...)
```

- [ ] **Step 5: Update search/command palette button**

Line 331: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`
Line 340: `background: 'var(--bg-elevated)'` → `background: 'rgba(0,0,0,0.08)'`
Line 344: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`

Line 351: `background: 'var(--bg-secondary)'` → `background: '#f6f5f4'`

- [ ] **Step 6: Update nav item hover/active states**

Lines 394-426, 488-496, 542-561: Update hover backgrounds from `var(--bg-tertiary)` to `rgba(0,0,0,0.05)` and active backgrounds similarly.

- [ ] **Step 7: Update user section**

Line 594: `background: 'var(--bg-secondary)'` → `background: '#f6f5f4'`
Line 602: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`

Line 678: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`
Line 688: `background: 'var(--bg-elevated)'` → `background: 'rgba(0,0,0,0.08)'`
Line 693: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`

- [ ] **Step 8: Update top bar (header)**

Line 718: `background: 'rgba(10, 15, 30, 0.8)'` → `background: 'rgba(255, 255, 255, 0.9)'`
Line 719: keep `backdropFilter: 'blur(12px)'`
Line 720: `borderBottom: '1px solid var(--border-subtle)'` → stays same

Line 733: `background: 'transparent'` → stays
Line 734: `border: '1px solid var(--border-default)'` → stays

Line 785: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`
Line 794: `background: 'var(--bg-elevated)'` → `background: 'rgba(0,0,0,0.08)'`
Line 799: `background: 'var(--bg-tertiary)'` → `background: 'rgba(0,0,0,0.05)'`

Line 810: `background: 'var(--bg-secondary)'` → `background: '#f6f5f4'`

- [ ] **Step 9: Verify sidebar renders light**

Run: Open http://localhost:5173
Expected: Sidebar is cream (#f6f5f4), top bar is white with blur, logo is blue, text is near-black

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat(theme): restyle Layout sidebar and top bar for light theme"
```

---

## Chunk 3: Page Spot-Fixes

### Task 5: Fix HomePage.tsx hardcoded colors

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Identify and replace hardcoded dark colors**

Search for hardcoded hex values in HomePage.tsx and replace with theme tokens or CSS vars. Common patterns:
- `background: '#060913'` → `background: 'var(--bg-base)'`
- `background: '#0f172a'` → `background: 'var(--bg-secondary)'`
- `background: '#1a2542'` → `background: 'var(--bg-elevated)'`
- `color: '#f97316'` → `color: 'var(--accent-primary)'` (or `#dd5b00` for warning context)
- `color: '#fbbf24'` → keep gold for winner highlights if appropriate, or map to theme
- `color: '#f1f5f9'` → `color: 'var(--text-primary)'`
- `color: '#94a3b8'` → `color: 'var(--text-secondary)'`
- `color: '#64748b'` → `color: 'var(--text-tertiary)'`
- `color: '#475569'` → `color: 'var(--text-muted)'`
- `borderColor: 'rgba(148, 163, 184, 0.15)'` → `borderColor: 'var(--border-default)'`

- [ ] **Step 2: Verify HomePage renders correctly**

Run: Open http://localhost:5173
Expected: White/cream hero, near-black text, blue CTA button, no dark backgrounds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "feat(theme): migrate HomePage to light theme"
```

---

### Task 6: Fix Dashboard.tsx hardcoded colors

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Replace hardcoded colors with theme tokens**

Same pattern as HomePage: search for `#` hex values and `rgba(...)` with dark colors, replace with CSS var references or theme imports.

- [ ] **Step 2: Verify Dashboard renders**

Run: Navigate to /dashboard
Expected: White cards with whisper borders, near-black text, blue actions

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(theme): migrate Dashboard to light theme"
```

---

### Task 7: Fix remaining pages

**Files:**
- Modify: `frontend/src/pages/ApplyPage.tsx`
- Modify: `frontend/src/pages/RegisterPage.tsx`
- Modify: `frontend/src/pages/HackathonDetailPage.tsx`
- Modify: `frontend/src/pages/JudgePortal.tsx`
- Modify: `frontend/src/pages/TracksPage.tsx`

- [ ] **Step 1: Batch replace hardcoded colors in all 5 files**

For each file, run a find-and-replace for the common dark hex patterns:
- `#060913` → remove or use `var(--bg-base)`
- `#0f172a` → `var(--bg-secondary)`
- `#131d35` → `var(--bg-tertiary)`
- `#1a2542` → `var(--bg-elevated)`
- `#0a0f1e` → `var(--bg-primary)`
- `#f1f5f9` → `var(--text-primary)`
- `#94a3b8` → `var(--text-secondary)`
- `#64748b` → `var(--text-tertiary)`
- `#475569` → `var(--text-muted)`
- `rgba(148, 163, 184, 0.08)` → `var(--border-subtle)`
- `rgba(148, 163, 184, 0.15)` → `var(--border-default)`
- `rgba(148, 163, 184, 0.25)` → `var(--border-strong)`
- `rgba(37, 99, 235` → `rgba(0, 117, 222` (if used for blue)
- `rgba(249, 115, 22` → `rgba(221, 91, 0` (if used for orange/warning)
- `#2563eb` → `#0075de`
- `#3b82f6` → `#005bab`
- `#f97316` → `#dd5b00`
- `#fb923c` → `#e07000`

- [ ] **Step 2: Verify each page renders**

Run: Navigate to each affected route:
- /apply
- /register
- /hackathons/:id
- /hackathons/:id/judging
- /tracks

Expected: All show light theme, no dark backgrounds remaining

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ApplyPage.tsx frontend/src/pages/RegisterPage.tsx frontend/src/pages/HackathonDetailPage.tsx frontend/src/pages/JudgePortal.tsx frontend/src/pages/TracksPage.tsx
git commit -m "feat(theme): migrate remaining pages to light theme"
```

---

## Chunk 4: Verification & Polish

### Task 8: Global verification

**Files:**
- Test: All frontend pages

- [ ] **Step 1: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: Zero errors

- [ ] **Step 2: Run dev build**

Run: `cd frontend && npx vite build --mode development`
Expected: Build succeeds, no CSS/JS errors

- [ ] **Step 3: Spot-check critical pages in browser**

Open and visually verify:
1. http://localhost:5173/ (HomePage) — white hero, blue CTA, cream sections
2. http://localhost:5173/dashboard — white cards, near-black text
3. http://localhost:5173/auth — white form, blue inputs
4. http://localhost:5173/assistant — light chat UI
5. http://localhost:5173/analyze — light report cards

- [ ] **Step 4: Check for remaining dark colors**

Run:
```bash
cd frontend/src
grep -rn "#060913\|#0f172a\|#131d35\|#1a2542\|#0a0f1e\|rgba(37,99,235\|rgba(249,115,22\|#2563eb\|#f97316" pages/ components/ --include="*.tsx" --include="*.ts" --include="*.css"
```
Expected: No matches (or only in intentionally preserved contexts like comments)

- [ ] **Step 5: Final commit**

```bash
git commit -m "feat(theme): complete Notion warm minimalism redesign" --allow-empty
```

---

## Rollback Plan

If anything breaks catastrophically, the original dark theme tokens are preserved in git history. To rollback:
```bash
git revert HEAD~N  # where N = number of commits made in this plan
```
