// ============================================================
// RowdyHacks Design System — CSUB Dark Theme
// Inspired by Stitch design principles: typographic hierarchy,
// surface layering, spacing scale, and consistent radius/shadows.
//
// Brand: CSUB Deep Blue (#001e40 / #003366) + Gold (#fecb00)
// ============================================================

// ── Color Tokens (surface layering, darkest → lightest) ─────
export const PAGE_BG = '#080c1a';
export const CARD_BG = '#0d1433';
export const INPUT_BG = '#111a3e';
export const NAV_BG = '#080c1a';
export const EXPANDED_BG = '#080c1a';
export const TABLE_HOVER = '#0d1433';

// Primary accent (CSUB Blue, brightened for dark backgrounds)
export const PRIMARY = '#1a5ce7';
export const PRIMARY_HOVER = '#003db8';
export const PRIMARY_DISABLED = '#0a2266';
export const PRIMARY_BG20 = '#1a5ce720';

// CSUB Gold
export const GOLD = '#FFC72C';
export const GOLD_BG20 = '#FFC72C20';
export const GOLD_BG10 = '#FFC72C10';

// Text hierarchy
export const TEXT_PRIMARY = '#e8e8f0';
export const TEXT_SECONDARY = '#b0b8d0';
export const TEXT_MUTED = '#8088a0';
export const TEXT_DIM = '#556';
export const TEXT_WHITE = '#fff';

// Borders
export const BORDER = '#1a2040';
export const BORDER_LIGHT = '#2a3050';
export const INPUT_BORDER = '#334';

// Semantic
export const SUCCESS = '#00c853';
export const SUCCESS_BG20 = '#00c85320';
export const SUCCESS_BG10 = '#00c85310';
export const WARNING = '#FFC72C';
export const WARNING_BG20 = '#FFC72C20';
export const WARNING_BG10 = '#FFC72C10';
export const WARNING_BORDER30 = '#FFC72C30';
export const ERROR = '#ff4444';
export const ERROR_TEXT = '#ff6b6b';
export const ERROR_BG20 = '#ff444420';
export const ERROR_BG10 = '#ff444410';
export const ERROR_BORDER30 = '#ff444430';
export const INFO = '#3b82f6';
export const INFO_BG20 = '#3b82f620';
export const ORANGE = '#ff9800';

// Status badge colors
export const STATUS_PENDING = '#f59e0b';
export const STATUS_ACCEPTED = '#10b981';
export const STATUS_REJECTED = '#ef4444';
export const STATUS_CHECKED_IN = '#3b82f6';

// ── Typography Tokens ───────────────────────────────────────
// Font family: Space Grotesk (system fallback)
const font = (size: number, weight: number, lineHeight: number, letterSpacing = 'normal') => ({
  fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  fontSize: size,
  fontWeight: weight,
  lineHeight,
  letterSpacing,
});

export const TYPO = {
  h1: font(32, 700, 1.2, '-0.02em'),
  h2: font(24, 600, 1.3, '-0.01em'),
  h3: font(20, 600, 1.4),
  'body-lg': font(16, 400, 1.6),
  'body-sm': font(14, 400, 1.5),
  'mono-data': {
    fontFamily: "'Space Mono', 'JetBrains Mono', 'Fira Code', monospace",
    fontSize: 13,
    fontWeight: 500,
    lineHeight: 1.0,
    letterSpacing: '0.05em',
    fontVariantNumeric: 'tabular-nums' as const,
  },
  'label-caps': font(12, 700, 1.0, '0.08em'),
  'score-lg': font(32, 700, 1, '-0.02em'),
};

// ── Spacing Scale (4px base) ────────────────────────────────
export const SPACE = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 48,
};

// ── Radius Tokens ───────────────────────────────────────────
export const RADIUS = {
  sm: 4,
  md: 8,
  lg: 12,
  full: 9999,
};

// ── Responsive Breakpoints ─────────────────────────────────
export const BREAKPOINTS = { mobile: 768, tablet: 1024 };

// ── Shadow Tokens ───────────────────────────────────────────
export const SHADOW = {
  card: '0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)',
  elevated: '0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)',
  modal: '0 8px 32px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.4)',
};
