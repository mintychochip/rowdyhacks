# Mobile Responsive Design — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make HackVerify responsive on mobile (≤768px) and tablet (769-1024px) without a CSS framework.

**Architecture:** CSS media queries handle global typography and table scaling. A `useMediaQuery` hook (based on `window.matchMedia`) provides per-component `isMobile`/`isTablet` booleans for inline style overrides. Navigation gets a hamburger drawer on mobile. Tables get `overflow-x: auto` wrappers.

**Tech Stack:** React 19, TypeScript, vanilla CSS, no additional dependencies.

---

## Chunk 1: Responsive Infrastructure

### Task 1.1: Create useMediaQuery hook

**Files:**
- Create: `frontend/src/hooks/useMediaQuery.ts`

- [ ] **Step 1: Write the hook**

```typescript
import { useEffect, useState } from 'react';

export function useMediaQuery() {
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mobileQuery = window.matchMedia('(max-width: 768px)');
    const tabletQuery = window.matchMedia('(min-width: 769px) and (max-width: 1024px)');

    const update = () => {
      setIsMobile(mobileQuery.matches);
      setIsTablet(tabletQuery.matches);
    };

    update(); // set initial values

    mobileQuery.addEventListener('change', update);
    tabletQuery.addEventListener('change', update);

    return () => {
      mobileQuery.removeEventListener('change', update);
      tabletQuery.removeEventListener('change', update);
    };
  }, []);

  return { isMobile, isTablet };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useMediaQuery.ts
git commit -m "feat: add useMediaQuery hook for responsive breakpoints"
```

### Task 1.2: Add BREAKPOINTS to theme

**Files:**
- Modify: `frontend/src/theme.ts`

- [ ] **Step 1: Add BREAKPOINTS constant**

Add at end of `theme.ts`, before the last export:

```typescript
// ── Responsive Breakpoints ─────────────────────────────────
export const BREAKPOINTS = { mobile: 768, tablet: 1024 };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/theme.ts
git commit -m "feat: add BREAKPOINTS constant to theme"
```

### Task 1.3: Add CSS media queries

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add media query rules**

Replace `frontend/src/index.css` with:

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #080c1a; color: #e8e8f0; }
input, button, textarea, select { font-family: inherit; }
a { color: inherit; }

@media (max-width: 768px) {
  h1, [data-mobile-h1] { font-size: 22px !important; }
  h2, [data-mobile-h2] { font-size: 18px !important; }
  body { font-size: 14px; }
  th, td { padding: 8px 10px !important; }
}
```

The `[data-mobile-h1]`/`[data-mobile-h2]` attribute selectors handle inline-style overrides — components with hardcoded `TYPO.h1`/`TYPO.h2` set `data-mobile-h1`/`data-mobile-h2` on the element to opt into mobile scaling.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: add mobile typography and table CSS media queries"
```

---

## Chunk 2: Navigation

### Task 2.1: Add hamburger menu to Layout

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Rewrite Layout with hamburger nav**

Replace `Layout.tsx` with:

```tsx
import { useState } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PRIMARY, GOLD, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, PAGE_BG, NAV_BG, BORDER, INPUT_BORDER, STATUS_ACCEPTED, TYPO, SPACE, RADIUS, CARD_BG } from '../theme';

const NAV_LINKS = [
  { to: '/', label: 'Analyze' },
  { to: '/hackathons', label: 'Hackathons' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { isMobile } = useMediaQuery();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);
  const toggleMenu = () => setMenuOpen(!menuOpen);

  const authLink = user ? null : (
    <Link to="/auth" onClick={closeMenu} style={{
      background: PRIMARY, border: 'none', borderRadius: RADIUS.md,
      padding: `${SPACE.xs + 2}px ${SPACE.md}px`, color: TEXT_WHITE,
      textDecoration: 'none', ...TYPO['body-sm'],
    }}>
      Sign In
    </Link>
  );

  const authSection = user ? (
    <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.md }}>
      <span style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>{user.name}</span>
      <button onClick={() => { logout(); closeMenu(); }} style={{
        background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
        padding: `${SPACE.xs + 2}px ${SPACE.sm + 4}px`, color: TEXT_MUTED,
        cursor: 'pointer', ...TYPO['body-sm'],
      }}>
        Logout
      </button>
    </div>
  ) : authLink;

  const qrLink = user ? (
    <Link to="/registrations" onClick={closeMenu} style={{ ...TYPO['body-sm'], color: STATUS_ACCEPTED, textDecoration: 'none', fontWeight: 600 }}>
      My QR Codes
    </Link>
  ) : null;

  const dashboardLink = user ? (
    <Link to="/dashboard" onClick={closeMenu} style={{ ...TYPO['body-sm'], color: TEXT_MUTED, textDecoration: 'none' }}>
      Dashboard
    </Link>
  ) : null;

  return (
    <div style={{ minHeight: '100vh', background: PAGE_BG, color: TEXT_PRIMARY }}>
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: isMobile ? '12px 14px' : `${SPACE.sm + 4}px ${SPACE.lg}px`,
        borderBottom: `1px solid ${BORDER}`,
        background: NAV_BG,
        position: 'relative',
      }}>
        <Link to="/" style={{ ...TYPO.h2, color: GOLD, textDecoration: 'none', margin: 0 }} onClick={closeMenu}>
          HackVerify
        </Link>

        {isMobile ? (
          <>
            <button
              onClick={toggleMenu}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: 4, display: 'flex', flexDirection: 'column', gap: 5,
                width: 24, height: 24, justifyContent: 'center',
              }}
            >
              <span style={{
                display: 'block', height: 2, width: 20, background: TEXT_MUTED,
                borderRadius: 1, transition: 'transform 0.2s',
                transform: menuOpen ? 'rotate(45deg) translate(5px, 5px)' : 'none',
              }} />
              <span style={{
                display: 'block', height: 2, width: 20, background: TEXT_MUTED,
                borderRadius: 1, transition: 'opacity 0.2s',
                opacity: menuOpen ? 0 : 1,
              }} />
              <span style={{
                display: 'block', height: 2, width: 20, background: TEXT_MUTED,
                borderRadius: 1, transition: 'transform 0.2s',
                transform: menuOpen ? 'rotate(-45deg) translate(5px, -5px)' : 'none',
              }} />
            </button>
            {menuOpen && (
              <div
                role="navigation"
                onClick={closeMenu}
                style={{
                  position: 'absolute', top: '100%', left: 0, right: 0,
                  background: CARD_BG, borderBottom: `1px solid ${BORDER}`,
                  padding: '16px 14px',
                  display: 'flex', flexDirection: 'column', gap: 14,
                  zIndex: 100,
                  animation: 'slideDown 0.2s ease',
                  overflow: 'hidden',
                }}
              >
                {NAV_LINKS.map(link => (
                  <Link key={link.to} to={link.to} onClick={closeMenu}
                    style={{ ...TYPO['body-lg'], color: TEXT_MUTED, textDecoration: 'none' }}>
                    {link.label}
                  </Link>
                ))}
                {qrLink}
                {dashboardLink}
                <div style={{ paddingTop: 8, borderTop: `1px solid ${BORDER}` }}>
                  {authSection}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.lg }}>
              {NAV_LINKS.map(link => (
                <Link key={link.to} to={link.to} style={{ ...TYPO['body-sm'], color: TEXT_MUTED, textDecoration: 'none' }}>
                  {link.label}
                </Link>
              ))}
              {qrLink}
              {dashboardLink}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.md }}>
              {authSection}
            </div>
          </>
        )}
      </nav>
      <main style={{ padding: 14, maxWidth: 1200, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Add slideDown keyframe to index.css**

Add to `frontend/src/index.css`:

```css
@keyframes slideDown {
  from { max-height: 0; opacity: 0; }
  to { max-height: 400px; opacity: 1; }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/index.css
git commit -m "feat: add hamburger menu for mobile navigation"
```

---

## Chunk 3: Primitives — Scrollable Card

### Task 3.1: Add scrollable prop to Card

**Files:**
- Modify: `frontend/src/components/Primitives.tsx`

- [ ] **Step 1: Update Card component**

Change the `CardProps` interface and `Card` component:

```tsx
interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'elevated';
  scrollable?: boolean;
  style?: React.CSSProperties;
}

export function Card({ children, variant = 'default', scrollable, style }: CardProps) {
  const baseStyle: React.CSSProperties = {
    background: CARD_BG,
    border: `1px solid ${BORDER}`,
    borderRadius: RADIUS.lg,
    boxShadow: variant === 'elevated' ? SHADOW.elevated : SHADOW.card,
    ...(scrollable ? { overflow: 'hidden' } : {}),
    ...style,
  };

  const content = scrollable ? (
    <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
      {children}
    </div>
  ) : children;

  return <div style={baseStyle}>{content}</div>;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Primitives.tsx
git commit -m "feat: add scrollable prop to Card for horizontal table overflow"
```

---

## Chunk 4: Table Pages — Scrollable Wrappers

### Task 4.1: JudgePortal — wrap tables

**Files:**
- Modify: `frontend/src/pages/JudgePortal.tsx`

This page has two `Card` components containing `Table` components (priority queue and completed list). No tables used directly outside of Cards.

- [ ] **Step 1: Add scrollable prop to both Cards**

Change both `<Card style={{ overflow: 'hidden', ... }}>` to `<Card scrollable style={{ ... }}>`:

1. Priority queue card (line ~317): `<Card style={{ overflow: 'hidden', marginBottom: SPACE.lg }}>` → `<Card scrollable style={{ marginBottom: SPACE.lg }}>`
2. Completed card (line ~397): `<Card style={{ overflow: 'hidden' }}>` → `<Card scrollable>`

- [ ] **Step 2: Make the scoring header responsive**

The scoring view header uses `display: 'flex', justifyContent: 'space-between'` with project title + timer side by side. On mobile, they should stack.

Import `useMediaQuery` and add at the top of the scoring view return:

```tsx
const { isMobile } = useMediaQuery();

// In the scoring header div, change to:
<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.lg, flexDirection: isMobile ? 'column' : 'row', gap: isMobile ? SPACE.md : 0 }}>
```

Also apply `data-mobile-h1` attribute to the `<h2>` in the scoring header:
```tsx
<h2 data-mobile-h1 style={{ ...TYPO.h1, marginBottom: SPACE.xs }}>{submission?.project_title || 'Untitled'}</h2>
```

And on the list view header:
```tsx
<h2 data-mobile-h1 style={{ ...TYPO.h1, margin: 0 }}>Judge Portal</h2>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/JudgePortal.tsx
git commit -m "fix: make JudgePortal responsive — scrollable tables, stacked header on mobile"
```

### Task 4.2: JudgingResultsPage — wrap tables

**Files:**
- Modify: `frontend/src/pages/JudgingResultsPage.tsx`

- [ ] **Step 1: Add scrollable prop and responsive header**

1. Rankings card: `<Card style={{ overflow: 'hidden', marginBottom: SPACE.lg }}>` → `<Card scrollable style={{ marginBottom: SPACE.lg }}>`
2. Judge stats card: `<Card style={{ overflow: 'hidden' }}>` → `<Card scrollable>`
3. Add `data-mobile-h1` to the page header: `<h2 data-mobile-h1 style={{ ...TYPO.h1, margin: 0 }}>Judging Results</h2>`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/JudgingResultsPage.tsx
git commit -m "fix: make JudgingResultsPage responsive with scrollable tables"
```

### Task 4.3: Dashboard — wrap table

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Wrap table in scrollable container**

Dashboard uses a raw `<table>` inside a `<div>` (not the `Card`/`Table` primitives). Add `overflowX: 'auto'` to the table wrapper div:

Change:
```tsx
<div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
```
to:
```tsx
<div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
  <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
```
And close the inner `</div>` just before the pagination div.

Also make the filters row stack-friendly — add `data-mobile-h1` to the heading:
```tsx
<h2 data-mobile-h1 style={{ fontSize: 24, fontWeight: 700 }}>Dashboard</h2>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "fix: make Dashboard table scrollable on mobile"
```

### Task 4.4: HackathonSetup — wrap table

**Files:**
- Modify: `frontend/src/pages/HackathonSetup.tsx`

- [ ] **Step 1: Wrap table in scrollable div and add responsive heading**

Two edits:

**Edit 1 — heading (line 45):** Change:
```tsx
<h2 style={{ fontSize: 24, marginBottom: 20 }}>Hackathons</h2>
```
to:
```tsx
<h2 data-mobile-h1 style={{ fontSize: 24, marginBottom: 20 }}>Hackathons</h2>
```

**Edit 2 — table wrapper (lines 87-142):** The table is inside `<div style={{ background: CARD_BG, border: ...borderRadius: 12, overflow: 'hidden' }}>`. Add an inner scrollable wrapper around the `<table>`:

Change:
```tsx
<div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
```
to:
```tsx
<div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
  <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
```

And close the inner `</div>` just before the outer `</div>` — add `</div>` before `</div>` on line 142. So the final lines are:
```tsx
        </table>
      </div>
    </div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/HackathonSetup.tsx
git commit -m "fix: make HackathonSetup table scrollable on mobile"
```

---

## Chunk 5: Spacing Pages — Responsive Padding

### Task 5.1: AnalyzePage — responsive padding

**Files:**
- Modify: `frontend/src/pages/AnalyzePage.tsx`

- [ ] **Step 1: Make padding and headers responsive**

Import `useMediaQuery`:
```tsx
import { useMediaQuery } from '../hooks/useMediaQuery';
```

Add hook call at top of component:
```tsx
const { isMobile } = useMediaQuery();
```

Changes:
1. Idle/loading/polling containers: `padding: 60` → `padding: isMobile ? 30 : 60`
2. Polling container: `padding: '60px 20px'` → `padding: isMobile ? '30px 14px' : '60px 20px'`
3. Error container: `padding: 60` → `padding: isMobile ? 30 : 60`
4. "Analyzing Submission" header: add `data-mobile-h1`
5. "Submitting..." header: add `data-mobile-h1`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AnalyzePage.tsx
git commit -m "fix: responsive padding on AnalyzePage"
```

### Task 5.2: RegistrationsPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/RegistrationsPage.tsx`

- [ ] **Step 1: Responsive padding and layout**

Import and use `useMediaQuery`.

Changes:
1. Container padding: `padding: 40` → `padding: isMobile ? 14 : 40`
2. Header: make it stack on mobile (`flexDirection: isMobile ? 'column' : 'row'`)
3. Empty state padding: `padding: 60` → `padding: isMobile ? 30 : 60`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegistrationsPage.tsx
git commit -m "fix: responsive padding on RegistrationsPage"
```

### Task 5.3: RegistrationDetailPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/RegistrationDetailPage.tsx`

- [ ] **Step 1: Responsive padding**

Import and use `useMediaQuery`.

Changes:
1. Container padding: `padding: 40` → `padding: isMobile ? 14 : 40`
2. Empty/loading/error containers: `padding: 60` → `padding: isMobile ? 30 : 60`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegistrationDetailPage.tsx
git commit -m "fix: responsive padding on RegistrationDetailPage"
```

### Task 5.4: AuthPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/AuthPage.tsx`

- [ ] **Step 1: Responsive margin/padding**

Import and use `useMediaQuery`.

Change:
```tsx
<div style={{ maxWidth: 400, margin: '60px auto', padding: 24 }}>
```
to:
```tsx
<div style={{ maxWidth: 400, margin: isMobile ? '30px auto' : '60px auto', padding: isMobile ? 14 : 24 }}>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AuthPage.tsx
git commit -m "fix: responsive padding on AuthPage"
```

### Task 5.5: RegisterPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Responsive padding**

Import and use `useMediaQuery`:
```tsx
import { useMediaQuery } from '../hooks/useMediaQuery';
```

Add hook call at top of component render (before the `if (!user)` guard):
```tsx
const { isMobile } = useMediaQuery();
```

Change the container padding (line 49):
```tsx
<div style={{ maxWidth: 480, margin: '0 auto', padding: 40 }}>
```
to:
```tsx
<div style={{ maxWidth: 480, margin: '0 auto', padding: isMobile ? 14 : 40 }}>
```

Change the "not logged in" state padding (line 18):
```tsx
<div style={{ textAlign: 'center', padding: 60 }}>
```
to:
```tsx
<div style={{ textAlign: 'center', padding: isMobile ? 30 : 60 }}>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegisterPage.tsx
git commit -m "fix: responsive padding on RegisterPage"
```

### Task 5.6: CheckInPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/CheckInPage.tsx`

- [ ] **Step 1: Responsive padding**

Import and use `useMediaQuery`.

Changes:
1. Container margin: `margin: '40px auto'` → `margin: isMobile ? '20px auto' : '40px auto'`
2. Input + button: stack on mobile (`flexDirection: isMobile ? 'column' : 'row'`)

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/CheckInPage.tsx
git commit -m "fix: responsive padding and stacked input on CheckInPage"
```

### Task 5.7: ReportPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/ReportPage.tsx`

- [ ] **Step 1: Responsive padding**

Import and use `useMediaQuery`.

Change loading/error padding:
```tsx
padding: 40 → padding: isMobile ? 20 : 40
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ReportPage.tsx
git commit -m "fix: responsive padding on ReportPage"
```

### Task 5.8: OrganizerRegistrationsPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/OrganizerRegistrationsPage.tsx`

Note: This page uses card layouts (not tables), so it only needs padding adjustments — no scrollable wrapper.

- [ ] **Step 1: Responsive padding**

Import and use `useMediaQuery`:
```tsx
import { useMediaQuery } from '../hooks/useMediaQuery';
```

Add hook call at top of component (after hooks):
```tsx
const { isMobile } = useMediaQuery();
```

Change the container padding (line 113):
```tsx
<div style={{ maxWidth: 900, margin: '0 auto', padding: 40 }}>
```
to:
```tsx
<div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? 14 : 40 }}>
```

Change the "organizer access required" and "no registrations" padding (lines 95, 212-213):
```tsx
padding: 60 → padding: isMobile ? 30 : 60
padding: 40 → padding: isMobile ? 20 : 40
```

Add `data-mobile-h1` to the heading (line 130):
```tsx
<h1 data-mobile-h1 style={{ fontSize: 24, marginBottom: 4 }}>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/OrganizerRegistrationsPage.tsx
git commit -m "fix: responsive padding on OrganizerRegistrationsPage"
```

### Task 5.9: RubricBuilderPage — responsive padding

**Files:**
- Modify: `frontend/src/pages/RubricBuilderPage.tsx`

Note: This page uses a form with flex-wrap rows (not tables), so it only needs padding and heading adjustments.

- [ ] **Step 1: Responsive padding and heading**

Import and use `useMediaQuery`:
```tsx
import { useMediaQuery } from '../hooks/useMediaQuery';
```

Add hook call at top of component (after existing hooks):
```tsx
const { isMobile } = useMediaQuery();
```

Add `data-mobile-h1` to the heading (line 92):
```tsx
<h2 data-mobile-h1 style={{ fontSize: 24, marginBottom: 20 }}>Judging Setup</h2>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RubricBuilderPage.tsx
git commit -m "fix: responsive heading on RubricBuilderPage"
```

---

## Chunk 6: Final Polish — UrlInput, CheckResultRow, Verification

### Task 6.1: UrlInput — stack on mobile

**Files:**
- Modify: `frontend/src/components/UrlInput.tsx`

- [ ] **Step 1: Stack input + button on mobile**

Import `useMediaQuery` and add hook call. Change the input+button container:

```tsx
<div style={{ display: 'flex', gap: SPACE.sm, maxWidth: 600, margin: '0 auto', flexDirection: isMobile ? 'column' : 'row' }}>
```

Also make the heading responsive by adding `data-mobile-h1`:
```tsx
<h2 data-mobile-h1 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>Check a Submission</h2>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/UrlInput.tsx
git commit -m "fix: stack UrlInput on mobile"
```

### Task 6.2: CheckResultRow — larger touch targets

**Files:**
- Modify: `frontend/src/components/CheckResultRow.tsx`

- [ ] **Step 1: Ensure minimum 44px tap target**

The clickable row header currently has `padding: '${SPACE.sm + 4}px ${SPACE.md}px'` which is 12px vertical. Combined with content, the total row height is already above 44px. No change needed beyond verification.

However, on mobile make the padding slightly larger for easier tapping:

```tsx
import { useMediaQuery } from '../hooks/useMediaQuery';

// Inside component:
const { isMobile } = useMediaQuery();

// On the clickable header div:
padding: isMobile ? '14px 12px' : `${SPACE.sm + 4}px ${SPACE.md}px`,
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CheckResultRow.tsx
git commit -m "fix: larger touch targets on CheckResultRow for mobile"
```

### Task 6.3: Build verification

**Files:**
- None (verification only)

- [ ] **Step 1: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: PASS (no type errors)

- [ ] **Step 2: Run existing tests**

```bash
cd frontend && npm test -- --run
```

Expected: All existing tests PASS. No behavioral changes should break any tests.

### Task 6.4: Manual visual verification

- [ ] **Step 1: Desktop (1920px / 1440px)**
  - All pages look identical to before
  - Nav is unchanged (horizontal links)

- [ ] **Step 2: Tablet (768-1024px)**
  - Content has reduced padding
  - Tables scroll horizontally if needed
  - Nav is still horizontal (no hamburger)
  - Text sizes are comfortable

- [ ] **Step 3: Mobile (375px / 414px)**
  - Hamburger menu appears, links open/close correctly
  - All pages fit in viewport width (no horizontal scroll except inside table wrappers)
  - Tables scroll horizontally with touch
  - Typography is smaller but readable
  - Touch targets are easy to tap

- [ ] **Step 4: Check all pages at 375px**
  - `/` (AnalyzePage) — URL input stacks, results readable; ReportCard and CheckDetails components do not overflow
  - `/auth` (AuthPage) — form fits screen
  - `/hackathons` — list readable
  - `/registrations` — cards fit screen
  - `/registrations/:id` — QR code visible
  - `/dashboard` — table scrolls
  - `/report/:id` — check rows tappable, ReportCard hero section fits, CheckDetails expanded content doesn't overflow
  - `/hackathons/:id/judging` — priority queue scrollable
  - `/hackathons/:id/judging/results` — rankings scrollable
  - `/hackathons/:id/judging/setup` — rubric form fits viewport

- [ ] **Step 5: Commit final verification notes**

```bash
git commit -m "docs: add mobile responsive verification checklist" --allow-empty
```

---

## Order of Execution

Chunks should be executed in order (1 → 2 → 3 → 4 → 5 → 6) because:
- Chunk 1 (infrastructure) is needed by everything else
- Chunk 2 (nav) needs the hook from Chunk 1
- Chunks 3-5 are independent of each other and could technically be parallelized
- Chunk 6 (polish) should come last to avoid conflicts
