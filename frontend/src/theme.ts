// ============================================================
// OpenHack Design System — Linear-Inspired
// Dark-mode-native: information emerges from darkness like starlight
// ============================================================

// --------------------------------------------------------------
// Color Primitives — Backgrounds (luminance hierarchy)
// --------------------------------------------------------------
const bg = '#08090a';              // Deepest canvas — page background
const bgPrimary = '#0f1011';       // Sidebar / panel backgrounds
const bgSecondary = '#191a1b';      // Elevated surfaces, cards
const bgTertiary = '#28282c';      // Hover states, slightly lifted
const bgElevated = '#191a1b';      // Card backgrounds (same as secondary)
const bgOverlay = 'rgba(0, 0, 0, 0.85)';

// --------------------------------------------------------------
// Text Colors (cool grayscale with barely-warm cast)
// --------------------------------------------------------------
const textPrimary = '#f7f8f8';     // Near-white primary text
const textSecondary = '#d0d6e0';   // Cool silver-gray body
const textTertiary = '#8a8f98';    // Muted placeholders, metadata
const textMuted = '#62666d';       // Quaternary — timestamps, disabled
const textInverse = '#020617';

// --------------------------------------------------------------
// Brand & Accent — Indigo-Violet (the only chromatic color)
// --------------------------------------------------------------
const accentPrimary = '#5e6ad2';       // Brand indigo — CTAs, key surfaces
const accentPrimaryHover = '#828fff';  // Lighter hover
const accentSecondary = '#7170ff';     // Accent violet — links, active
const accentGlow = 'rgba(94, 106, 210, 0.35)';
const accentSubtle = 'rgba(94, 106, 210, 0.12)';

// --------------------------------------------------------------
// Semantic Colors (re-mapped to Linear's cool palette)
// --------------------------------------------------------------
const success = '#27a644';
const successSubtle = 'rgba(39, 166, 68, 0.12)';
const warning = '#eab308';
const warningSubtle = 'rgba(234, 179, 8, 0.12)';
const error = '#ef4444';
const errorSubtle = 'rgba(239, 68, 68, 0.12)';
const info = '#3b82f6';
const infoSubtle = 'rgba(59, 130, 246, 0.12)';

// --------------------------------------------------------------
// Borders — Semi-transparent white (Linear's signature)
// --------------------------------------------------------------
const borderSubtle = 'rgba(255, 255, 255, 0.05)';
const borderDefault = 'rgba(255, 255, 255, 0.08)';
const borderStrong = 'rgba(255, 255, 255, 0.12)';
const borderFocus = 'rgba(94, 106, 210, 0.5)';

// --------------------------------------------------------------
// Legacy orange/gold kept for specific contexts (status, winners)
// --------------------------------------------------------------
const orange = '#f97316';
const orangeHover = '#fb923c';
const orangePressed = '#ea580c';
const orangeGlow = 'rgba(249, 115, 22, 0.4)';
const orangeSubtle = 'rgba(249, 115, 22, 0.12)';

const gold = '#fbbf24';
const goldHover = '#f59e0b';
const goldGlow = 'rgba(251, 191, 36, 0.3)';

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
// Legacy exports — values updated to Linear palette
// ============================================================

export const PAGE_BG = bg;
export const CARD_BG = bgSecondary;
export const INPUT_BG = 'rgba(255, 255, 255, 0.02)';
export const NAV_BG = bgPrimary;
export const EXPANDED_BG = bgTertiary;
export const TABLE_HOVER = bgTertiary;

export const PRIMARY = accentPrimary;
export const PRIMARY_HOVER = accentPrimaryHover;
export const PRIMARY_DISABLED = textMuted;
export const PRIMARY_BG20 = 'rgba(94, 106, 210, 0.2)';

export const CYAN = accentSecondary;
export const CYAN_BG20 = 'rgba(113, 112, 255, 0.2)';
export const CYAN_BG10 = 'rgba(113, 112, 255, 0.1)';

export const TEXT_PRIMARY = textPrimary;
export const TEXT_SECONDARY = textSecondary;
export const TEXT_TERTIARY = textTertiary;
export const TEXT_MUTED = textMuted;
export const TEXT_DIM = textTertiary;
export const TEXT_WHITE = textPrimary;

export const BORDER = borderDefault;
export const BORDER_SUBTLE = borderSubtle;
export const BORDER_LIGHT = borderStrong;
export const INPUT_BORDER = borderDefault;

export const SUCCESS = success;
export const SUCCESS_BG20 = 'rgba(39, 166, 68, 0.2)';
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

// CSS custom property names for dynamic branding
export const CSS_PRIMARY = 'var(--oh-primary)';
export const CSS_THEME_COLOR = 'var(--oh-theme-color)';

// Status badge colors
export const STATUS_PENDING = warning;
export const STATUS_ACCEPTED = success;
export const STATUS_REJECTED = error;
export const STATUS_CHECKED_IN = info;

// ============================================================
// Linear Typography System
// Primary: Inter with geometric alternates
// Three-tier weight: 400 (read) / 500 (emphasis) / 600 (strong)
// ============================================================

export const FONT_FEATURE_SETTINGS = "'cv01', 'ss03'";

export const TYPO = {
  display: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 36,
    fontWeight: 500,
    lineHeight: 1.0,
    letterSpacing: '-0.03em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  h1: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 28,
    fontWeight: 500,
    lineHeight: 1.1,
    letterSpacing: '-0.02em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  h2: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 20,
    fontWeight: 500,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  h3: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 16,
    fontWeight: 600,
    lineHeight: 1.4,
    letterSpacing: '-0.01em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  body: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 15,
    fontWeight: 400,
    lineHeight: 1.6,
    letterSpacing: '-0.01em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  small: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.5,
    letterSpacing: '-0.01em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  label: {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 11,
    fontWeight: 500,
    lineHeight: 1.0,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  mono: {
    fontFamily: "'JetBrains Mono', ui-monospace, SF Mono, Menlo, monospace",
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.5,
  },
  'mono-lg': {
    fontFamily: "'JetBrains Mono', ui-monospace, SF Mono, Menlo, monospace",
    fontSize: 20,
    fontWeight: 400,
    lineHeight: 1.3,
    letterSpacing: '-0.02em',
  },
  // Legacy aliases
  'body-lg': {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 16,
    fontWeight: 400,
    lineHeight: 1.6,
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  'body-sm': {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.5,
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  'mono-data': {
    fontFamily: "'JetBrains Mono', ui-monospace, SF Mono, Menlo, monospace",
    fontSize: 12,
    fontWeight: 500,
    lineHeight: 1.0,
    letterSpacing: '0.03em',
    fontVariantNumeric: 'tabular-nums' as const,
  },
  'label-caps': {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 11,
    fontWeight: 600,
    lineHeight: 1.0,
    letterSpacing: '0.08em',
    textTransform: 'uppercase' as const,
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
  'score-lg': {
    fontFamily: "'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif",
    fontSize: 28,
    fontWeight: 600,
    lineHeight: 1,
    letterSpacing: '-0.02em',
    fontFeatureSettings: FONT_FEATURE_SETTINGS,
  },
} as const;

// ============================================================
// Linear-Inspired Spacing (8px base, with micro-adjustments)
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
  '5xl': 64,
  '6xl': 80,
} as const;

// ============================================================
// Radius Scale
// ============================================================

export const RADIUS = {
  micro: 2,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

// ============================================================
// Shadows — Multi-layered for dark surfaces
// ============================================================

export const SHADOW = {
  sm: 'rgba(0, 0, 0, 0.03) 0px 1.2px 0px 0px',
  md: 'rgba(0, 0, 0, 0.4) 0px 2px 4px',
  lg: 'rgba(0, 0, 0, 0.5) 0px 8px 24px',
  card: 'rgba(0, 0, 0, 0.2) 0px 0px 0px 1px',
  elevated: 'rgba(0, 0, 0, 0.4) 0px 2px 4px',
  glow: '0 0 20px rgba(94, 106, 210, 0.35)',
  orangeGlow: '0 0 20px rgba(249, 115, 22, 0.4)',
  goldGlow: '0 0 20px rgba(251, 191, 36, 0.3)',
  dialog: 'rgba(0,0,0,0) 0px 8px 2px, rgba(0,0,0,0.01) 0px 5px 2px, rgba(0,0,0,0.04) 0px 3px 2px, rgba(0,0,0,0.07) 0px 1px 1px, rgba(0,0,0,0.08) 0px 0px 1px',
  inset: 'rgba(0, 0, 0, 0.2) 0px 0px 12px 0px inset',
} as const;

// ============================================================
// Breakpoints & Timing
// ============================================================

export const BREAKPOINTS = { mobile: 768, tablet: 1024 };

export const TIMING = {
  fast: '100ms',
  base: '150ms',
  slow: '250ms',
} as const;

// ============================================================
// Linear Button Presets
// ============================================================

export const BUTTON = {
  ghost: {
    background: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgb(36, 40, 44)',
    color: '#e2e4e7',
    borderRadius: RADIUS.sm,
    padding: '8px 16px',
  },
  subtle: {
    background: 'rgba(255, 255, 255, 0.04)',
    color: '#d0d6e0',
    borderRadius: RADIUS.sm,
    padding: '0px 6px',
  },
  primary: {
    background: accentPrimary,
    color: '#ffffff',
    borderRadius: RADIUS.sm,
    padding: '8px 16px',
    hoverBackground: accentPrimaryHover,
  },
  icon: {
    background: 'rgba(255, 255, 255, 0.03)',
    color: '#f7f8f8',
    borderRadius: '50%',
    border: '1px solid rgba(255, 255, 255, 0.08)',
  },
  pill: {
    background: 'transparent',
    color: '#d0d6e0',
    borderRadius: RADIUS.full,
    border: '1px solid rgb(35, 37, 42)',
    padding: '0px 10px 0px 5px',
  },
  toolbar: {
    background: 'rgba(255, 255, 255, 0.05)',
    color: '#62666d',
    borderRadius: RADIUS.micro,
    border: '1px solid rgba(255, 255, 255, 0.05)',
    shadow: 'rgba(0, 0, 0, 0.03) 0px 1.2px 0px 0px',
    fontSize: 12,
    fontWeight: 500,
  },
} as const;

// ============================================================
// Card Preset
// ============================================================

export const CARD = {
  background: 'rgba(255, 255, 255, 0.02)',
  backgroundHover: 'rgba(255, 255, 255, 0.04)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  borderSubtle: '1px solid rgba(255, 255, 255, 0.05)',
  borderRadius: RADIUS.md,
  borderRadiusLg: RADIUS.lg,
  shadow: SHADOW.card,
} as const;

// ============================================================
// Elevation Tokens
// ============================================================

export const ELEVATION = {
  flat: { background: '#010102' },
  subtle: { background: 'rgba(255, 255, 255, 0.02)' },
  surface: { background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.08)' },
  elevated: { background: 'rgba(255, 255, 255, 0.05)', shadow: SHADOW.md },
  dialog: { background: '#191a1b', shadow: SHADOW.dialog },
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
