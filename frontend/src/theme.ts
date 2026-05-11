// ============================================================
// OpenHack Design System — Rocket Theme
// Space Launch: Deep layers, flame accents, star highlights
// ============================================================

// Dark mode only — light theme deprecated

// Space Backgrounds (Layered Depth)
const bg = '#060913';
const bgPrimary = '#0a0f1e';
const bgSecondary = '#0f172a';
const bgTertiary = '#131d35';
const bgElevated = '#1a2542';
const bgOverlay = 'rgba(0, 0, 0, 0.75)';

// Text colors
const textPrimary = '#f1f5f9';
const textSecondary = '#94a3b8';
const textTertiary = '#64748b';
const textMuted = '#475569';
const textInverse = '#020617';

// Brand Blue (Primary Actions)
const accentPrimary = '#2563eb';
const accentPrimaryHover = '#3b82f6';
const accentSecondary = '#1d4ed8';
const accentGlow = 'rgba(37, 99, 235, 0.35)';
const accentSubtle = 'rgba(37, 99, 235, 0.12)';

// Flame Orange (CTA / Launch)
const orange = '#f97316';
const orangeHover = '#fb923c';
const orangePressed = '#ea580c';
const orangeGlow = 'rgba(249, 115, 22, 0.4)';
const orangeSubtle = 'rgba(249, 115, 22, 0.12)';

// Star Gold (Highlights / Winners)
const gold = '#fbbf24';
const goldHover = '#f59e0b';
const goldGlow = 'rgba(251, 191, 36, 0.3)';

// Semantic colors
const success = '#22c55e';
const successSubtle = 'rgba(34, 197, 94, 0.1)';
const warning = '#eab308';
const warningSubtle = 'rgba(234, 179, 8, 0.1)';
const error = '#ef4444';
const errorSubtle = 'rgba(239, 68, 68, 0.1)';
const info = '#3b82f6';
const infoSubtle = 'rgba(59, 130, 246, 0.1)';

// Borders
const borderSubtle = 'rgba(148, 163, 184, 0.08)';
const borderDefault = 'rgba(148, 163, 184, 0.15)';
const borderStrong = 'rgba(148, 163, 184, 0.25)';
const borderFocus = 'rgba(37, 99, 235, 0.5)';

// ============================================================
// CSS Variables export (for inline styles)
// ============================================================

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

  '--orange': orange,
  '--orange-hover': orangeHover,
  '--orange-pressed': orangePressed,
  '--orange-glow': orangeGlow,
  '--orange-subtle': orangeSubtle,

  '--gold': gold,
  '--gold-hover': goldHover,
  '--gold-glow': goldGlow,

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

// ============================================================
// Legacy exports — preserved for backward compatibility
// ============================================================

export const PAGE_BG = bg;
export const CARD_BG = bgElevated;
export const INPUT_BG = bgTertiary;
export const NAV_BG = bgSecondary;
export const EXPANDED_BG = bgTertiary;
export const TABLE_HOVER = bgTertiary;

export const PRIMARY = accentPrimary;
export const PRIMARY_HOVER = accentPrimaryHover;
export const PRIMARY_DISABLED = textMuted;
export const PRIMARY_BG20 = 'rgba(37, 99, 235, 0.2)';

export const CYAN = accentPrimary;
export const CYAN_BG20 = 'rgba(37, 99, 235, 0.2)';
export const CYAN_BG10 = accentSubtle;

export const TEXT_PRIMARY = textPrimary;
export const TEXT_SECONDARY = textSecondary;
export const TEXT_MUTED = textMuted;
export const TEXT_DIM = textTertiary;
export const TEXT_WHITE = textPrimary;

export const BORDER = borderDefault;
export const BORDER_LIGHT = borderStrong;
export const INPUT_BORDER = borderDefault;

export const SUCCESS = success;
export const SUCCESS_BG20 = 'rgba(34, 197, 94, 0.2)';
export const SUCCESS_BG10 = successSubtle;

export const WARNING = warning;
export const WARNING_BG20 = 'rgba(234, 179, 8, 0.2)';
export const WARNING_BG10 = warningSubtle;
export const WARNING_BORDER30 = 'rgba(234, 179, 8, 0.3)';

export const ERROR = error;
export const ERROR_TEXT = error;
export const ERROR_BG20 = 'rgba(239, 68, 68, 0.2)';
export const ERROR_BG10 = errorSubtle;
export const ERROR_BORDER30 = 'rgba(239, 68, 68, 0.3)';

export const INFO = info;
export const INFO_BG20 = 'rgba(59, 130, 246, 0.2)';
export const INFO_BG10 = infoSubtle;

export const ORANGE = orange;
export const ORANGE_BG20 = 'rgba(249, 115, 22, 0.2)';
export const ORANGE_BG10 = orangeSubtle;

export const GOLD = gold;
export const GOLD_BG20 = 'rgba(251, 191, 36, 0.2)';
export const GOLD_BG10 = 'rgba(251, 191, 36, 0.1)';

// Status badge colors
export const STATUS_PENDING = warning;
export const STATUS_ACCEPTED = success;
export const STATUS_REJECTED = error;
export const STATUS_CHECKED_IN = info;

// ============================================================
// Spacing — unchanged
// ============================================================

export const SPACE = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
  '3xl': 40,
  '4xl': 48,
} as const;

// ============================================================
// Radius — unchanged
// ============================================================

export const RADIUS = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

// ============================================================
// Typography tokens
// ============================================================

export const TYPO = {
  display: {
    fontFamily: "'Space Grotesk', -apple-system, sans-serif",
    fontSize: 36,
    fontWeight: 700,
    lineHeight: 1.2,
    letterSpacing: '-0.02em',
  },
  h1: {
    fontFamily: "'Space Grotesk', -apple-system, sans-serif",
    fontSize: 28,
    fontWeight: 700,
    lineHeight: 1.2,
    letterSpacing: '-0.01em',
  },
  h2: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 20,
    fontWeight: 600,
    lineHeight: 1.3,
  },
  h3: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 16,
    fontWeight: 600,
    lineHeight: 1.4,
  },
  body: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 15,
    fontWeight: 400,
    lineHeight: 1.6,
  },
  small: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.5,
  },
  label: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 11,
    fontWeight: 500,
    lineHeight: 1.0,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
  },
  mono: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.5,
  },
  'mono-lg': {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 20,
    fontWeight: 400,
    lineHeight: 1.3,
    letterSpacing: '-0.02em',
  },
  // Legacy typography aliases
  'body-lg': {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 16,
    fontWeight: 400,
    lineHeight: 1.6,
  },
  'body-sm': {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.5,
  },
  'mono-data': {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12,
    fontWeight: 500,
    lineHeight: 1.0,
    letterSpacing: '0.03em',
    fontVariantNumeric: 'tabular-nums' as const,
  },
  'label-caps': {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 11,
    fontWeight: 600,
    lineHeight: 1.0,
    letterSpacing: '0.08em',
    textTransform: 'uppercase' as const,
  },
  'score-lg': {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 28,
    fontWeight: 700,
    lineHeight: 1,
    letterSpacing: '-0.02em',
  },
} as const;

// ============================================================
// Shadow tokens
// ============================================================

export const SHADOW = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  md: '0 4px 12px rgba(0, 0, 0, 0.4)',
  lg: '0 8px 24px rgba(0, 0, 0, 0.5)',
  glow: '0 0 20px rgba(37, 99, 235, 0.35)',
  orangeGlow: '0 0 20px rgba(249, 115, 22, 0.4)',
  goldGlow: '0 0 20px rgba(251, 191, 36, 0.3)',
} as const;

// ============================================================
// Breakpoints & Timing — unchanged
// ============================================================

export const BREAKPOINTS = { mobile: 768, tablet: 1024 };

export const TIMING = {
  fast: '100ms',
  base: '150ms',
  slow: '250ms',
} as const;

// ============================================================
// Deprecated — kept for compatibility but same values
// ============================================================

export type ThemeMode = 'dark';
export const getColors = (_mode: ThemeMode) => ({
  bg, bgPrimary, bgSecondary, bgTertiary, bgElevated, bgOverlay,
  textPrimary, textSecondary, textTertiary, textMuted, textInverse,
  accentPrimary, accentPrimaryHover, accentSecondary,
  accentGlow, accentSubtle,
  success, successSubtle,
  warning, warningSubtle,
  error, errorSubtle,
  info, infoSubtle,
  borderSubtle, borderDefault, borderStrong, borderFocus,
});
