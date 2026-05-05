# UI Modernization Implementation Plan

> For agentic workers: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Modernize the Hack the Valley UI with a raw, minimal hacker aesthetic using IBM Plex fonts, monochrome colors, and sharp geometry.

**Architecture:** Replace the existing navy/blue theme with a monochrome system supporting light and dark modes.

**Tech Stack:** React + Vite + TypeScript, IBM Plex fonts

---

## Chunk 1: Theme System Foundation

### Task 1: Update index.html with IBM Plex fonts

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Replace font imports (lines 12-15)**

Replace with:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

Remove Material Symbols Outlined import.

- [ ] **Step 2: Update theme-color meta tag (line 7)**

Change to: `<meta name="theme-color" content="#0a0a0a" />`

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add IBM Plex fonts"
```

---

### Task 2: Rewrite theme.ts with new design tokens

**Files:**
- Modify: `frontend/src/theme.ts`

- [ ] **Step 1: Replace entire file with new theme**

New theme includes:
- Light and dark color tokens
- IBM Plex typography
- Updated spacing (4px base unit)
- Flat shadows (no glows)

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/theme.ts
git commit -m "feat: new monochrome theme system"
```

---

## Chunk 2: Global Styles

### Task 3: Update index.css

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Replace with new base styles**

New styles include:
- IBM Plex font family
- Dark mode default (#0a0a0a background)
- Minimal scrollbar styling
- Selection styling

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build completes

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: update global styles"
```

---

## Chunk 3: Layout Component

### Task 4: Simplify Layout.tsx

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Update navigation styling**

Changes:
- Replace mascot with simple logo
- Simplify nav links (no icons)
- Square user avatars (not circles)
- Monochrome colors

- [ ] **Step 2: Test navigation**

Verify all links work.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: simplify navigation layout"
```

---

## Chunk 4: HomePage

### Task 5: Redesign HomePage hero

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Update unauthenticated hero**

New design:
- Mono pretitle (Feb 15-17, 2026)
- Large headline
- Minimal stats grid
- Simple CTA buttons

- [ ] **Step 2: Test rendering**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "feat: redesign HomePage hero"
```

---

## Chunk 5: Testing

### Task 6: Final verification

- [ ] Test mobile viewport (375px)
- [ ] Test tablet viewport (768px)
- [ ] Run lint: `npm run lint`
- [ ] Run type check: `npx tsc --noEmit`
- [ ] Build: `npm run build`

- [ ] Final commit

```bash
git add -A
git commit -m "feat: complete UI modernization"
```
