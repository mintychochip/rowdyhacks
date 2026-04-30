# Mobile Responsive Design — Spec

## Overview

Make HackVerify responsive for mixed desktop + mobile use. Organizers use desktop, participants and judges use phones. The app should work well on both without a framework dependency.

## Approach

CSS-only responsive design — no component rewrites. Add breakpoint infrastructure, hamburger nav, scrollable tables, and responsive spacing/typography. Component structure stays intact.

## Breakpoints

- **Mobile**: ≤768px — gets mobile adaptations (hamburger nav, reduced padding, scrollable tables, scaled typography)
- **Tablet**: 769-1024px — mobile padding/spacing, but desktop-style navigation and typography
- **Desktop**: >1024px — full desktop layout

Only the ≤768px breakpoint triggers behavioral layout changes (nav collapse, stacked layouts). 769-1024px uses desktop nav and typography but benefits from intermediate spacing and the same scrollable table wrappers.

## Implementation

### 1. Responsive Infrastructure

**`frontend/src/hooks/useMediaQuery.ts`** — new hook:
- Uses `window.matchMedia('(max-width: 768px)')` and `window.matchMedia('(max-width: 1024px)')` with `change` event listeners (no manual resize debounce needed — the browser handles it)
- Returns `{ isMobile: boolean, isTablet: boolean }`
- Initialized from `matchMedia(...).matches` on first render
- SSR-safe: guard `window` access behind `typeof window !== 'undefined'` check (returns false defaults)

**`frontend/src/theme.ts`** — add `BREAKPOINTS` constant:
```typescript
export const BREAKPOINTS = { mobile: 768, tablet: 1024 };
```

**`frontend/src/index.css`** — add media query rules for:
- Typography scaling (h1, h2, body)
- Table cell padding
- Any other CSS-only adjustments

### 2. Navigation (Layout.tsx)

- Desktop: unchanged — horizontal links in nav bar
- Mobile (≤768px):
  - Logo stays left, hamburger button (24x24, three-line icon) appears right
  - Tapping hamburger opens full-width dropdown panel below nav with stacked nav links + auth button
  - Panel has CSS slide-down animation (max-height transition)
  - Tapping a link or the hamburger again closes the panel
  - Hamburger open/close state managed by local `useState<boolean>` in Layout.tsx — no context or router changes needed
  - Nav padding reduces to 12px on mobile

### 3. Layout Spacing (Layout.tsx + individual pages)

- Main content padding: 24px desktop → 14px mobile
- Page-level hardcoded padding (60px, 40px) → halved on mobile via `isMobile` hook
- Pages touched: AnalyzePage, RegistrationsPage, RegistrationDetailPage, AuthPage, RegisterPage, CheckInPage, ReportPage

### 4. Tables (Primitives.tsx + table-using pages)

- Every `<Table>` gets wrapped in `overflow-x: auto` with `-webkit-overflow-scrolling: touch`
- Add optional `scrollable` prop to `Card` component — when true, wraps children in scrollable div
- Table font-size drops to 13px on mobile (CSS media query)
- Table cell horizontal padding reduces from 16px to 10px on mobile (CSS media query)
- Pages using tables: JudgePortal, JudgingResultsPage, Dashboard, HackathonSetup, RubricBuilderPage, OrganizerRegistrationsPage

### 5. Typography Scaling (index.css)

Media query at 768px:
- `h1`: 28px → 22px
- `h2`: 22px → 18px
- Body text: 15px → 14px

Inline styles using `TYPO.h1`/`TYPO.h2` override CSS — for headers on JudgePortal, AnalyzePage, and JudgingResultsPage, use `isMobile` hook to pick appropriate size from TYPO.

### 6. Miscellaneous

- **UrlInput**: Already has responsive-friendly layout; ensure input + button stack vertically on mobile (≤768px)
- **ReportCard / CheckDetails**: Already use flex-wrap; verify they don't overflow on mobile
- **CheckResultRow**: Ensure expand/collapse target is large enough for touch (min 44px) on mobile

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/hooks/useMediaQuery.ts` | **New** — responsive hook |
| `frontend/src/theme.ts` | Add BREAKPOINTS constant |
| `frontend/src/index.css` | Add media query rules for typography and tables |
| `frontend/src/components/Layout.tsx` | Hamburger nav for mobile |
| `frontend/src/components/Primitives.tsx` | Add `scrollable` prop to Card |
| `frontend/src/pages/AnalyzePage.tsx` | Responsive padding |
| `frontend/src/pages/JudgePortal.tsx` | Scrollable tables, responsive header |
| `frontend/src/pages/JudgingResultsPage.tsx` | Scrollable tables, responsive header |
| `frontend/src/pages/RegistrationsPage.tsx` | Responsive padding |
| `frontend/src/pages/RegistrationDetailPage.tsx` | Responsive padding |
| `frontend/src/pages/Dashboard.tsx` | Scrollable tables |
| `frontend/src/pages/HackathonSetup.tsx` | Scrollable tables |
| `frontend/src/pages/OrganizerRegistrationsPage.tsx` | Scrollable tables |
| `frontend/src/pages/ReportPage.tsx` | Responsive padding |
| `frontend/src/pages/AuthPage.tsx` | Responsive padding |
| `frontend/src/pages/RegisterPage.tsx` | Responsive padding |
| `frontend/src/pages/CheckInPage.tsx` | Responsive padding |
| `frontend/src/pages/RubricBuilderPage.tsx` | Scrollable tables |
| `frontend/src/components/UrlInput.tsx` | Stack layout on mobile (≤768px) |
| `frontend/src/components/CheckResultRow.tsx` | Touch-friendly tap targets |

## Not in Scope

- Card-layout table replacements (horizontal scroll is acceptable)

## Testing

- Use Chrome DevTools device emulation (375px, 414px, 768px, 1024px) to verify layout on each page
- Verify hamburger nav opens/closes on mobile, links navigate and close the panel
- Verify all tables scroll horizontally on mobile without breaking the page width
- Verify touch targets are ≥44px for interactive elements (buttons, links, check expand/collapse)
- Existing Jest + React Testing Library tests continue to pass (no behavioral changes)
- Third-party CSS framework
- PWA manifest or service worker changes (already set up)
- Backend changes
