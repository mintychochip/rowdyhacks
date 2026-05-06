// ============================================================
// Hack the Valley Design System - Linear Inspired
// Cinematic Minimalism: Deep layers, subtle glows, refined motion
// ============================================================

export type ThemeMode = 'light' | 'dark';

// Linear-inspired dark theme colors
const darkColors = {
  // Base backgrounds - layered depth
  bg: '#0e0e10',
  bgPrimary: '#0e0e10',
  bgSecondary: '#141416',
  bgTertiary: '#1a1a1c',
  bgElevated: '#1f1f22',
  bgOverlay: 'rgba(0, 0, 0, 0.8)',

  // Text colors - refined hierarchy
  textPrimary: '#f7f8f8',
  textSecondary: '#a1a1aa',
  textTertiary: '#71717a',
  textMuted: '#52525b',
  textInverse: '#09090b',

  // Accent colors - Muted slate/indigo (Linear's subtle style)
  accentPrimary: '#5e6ad2',
  accentPrimaryHover: '#4f58b3',
  accentSecondary: '#6b7280',
  accentGlow: 'rgba(94, 106, 210, 0.25)',
  accentSubtle: 'rgba(94, 106, 210, 0.08)',

  // Semantic colors
  success: '#22c55e',
  successSubtle: 'rgba(34, 197, 94, 0.1)',
  warning: '#f59e0b',
  warningSubtle: 'rgba(245, 158, 11, 0.1)',
  error: '#ef4444',
  errorSubtle: 'rgba(239, 68, 68, 0.1)',
  info: '#3b82f6',
  infoSubtle: 'rgba(59, 130, 246, 0.1)',

  // Borders - subtle definition
  borderSubtle: 'rgba(255, 255, 255, 0.06)',
  borderDefault: 'rgba(255, 255, 255, 0.1)',
  borderStrong: 'rgba(255, 255, 255, 0.15)',
  borderFocus: 'rgba(139, 92, 246, 0.5)',
} as const;

// Light theme - refined and airy
const lightColors = {
  bg: '#ffffff',
  bgPrimary: '#fafafa',
  bgSecondary: '#f4f4f5',
  bgTertiary: '#e4e4e7',
  bgElevated: '#ffffff',
  bgOverlay: 'rgba(0, 0, 0, 0.6)',

  textPrimary: '#18181b',
  textSecondary: '#52525b',
  textTertiary: '#71717a',
  textMuted: '#a1a1aa',
  textInverse: '#ffffff',

  accentPrimary: '#7c3aed',
  accentPrimaryHover: '#6d28d9',
  accentSecondary: '#6366f1',
  accentGlow: 'rgba(124, 58, 237, 0.2)',
  accentSubtle: 'rgba(124, 58, 237, 0.1)',

  success: '#16a34a',
  successSubtle: 'rgba(22, 163, 74, 0.1)',
  warning: '#d97706',
  warningSubtle: 'rgba(217, 119, 6, 0.1)',
  error: '#dc2626',
  errorSubtle: 'rgba(220, 38, 38, 0.1)',
  info: '#2563eb',
  infoSubtle: 'rgba(37, 99, 235, 0.1)',

  borderSubtle: 'rgba(0, 0, 0, 0.06)',
  borderDefault: 'rgba(0, 0, 0, 0.1)',
  borderStrong: 'rgba(0, 0, 0, 0.15)',
  borderFocus: 'rgba(124, 58, 237, 0.5)',
} as const;

// Export color getters based on theme
export const getColors = (mode: ThemeMode) => mode === 'light' ? lightColors : darkColors;

// Legacy exports for backward compatibility
export const PAGE_BG = darkColors.bg;
export const CARD_BG = darkColors.bgElevated;
export const INPUT_BG = darkColors.bgTertiary;
export const NAV_BG = darkColors.bgSecondary;
export const EXPANDED_BG = darkColors.bgTertiary;
export const TABLE_HOVER = darkColors.bgTertiary;

export const PRIMARY = darkColors.accentPrimary;
export const PRIMARY_HOVER = darkColors.accentPrimaryHover;
export const PRIMARY_DISABLED = '#52525b';
export const PRIMARY_BG20 = 'rgba(94, 106, 210, 0.2)';

export const CYAN = '#5e6ad2';
export const CYAN_BG20 = 'rgba(94, 106, 210, 0.2)';
export const CYAN_BG10 = darkColors.accentSubtle;

export const TEXT_PRIMARY = darkColors.textPrimary;
export const TEXT_SECONDARY = darkColors.textSecondary;
export const TEXT_MUTED = darkColors.textMuted;
export const TEXT_DIM = darkColors.textTertiary;
export const TEXT_WHITE = darkColors.textPrimary;

export const BORDER = darkColors.borderDefault;
export const BORDER_LIGHT = darkColors.borderStrong;
export const INPUT_BORDER = darkColors.borderDefault;

// Spacing - refined scale
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

// Radius - softer corners
export const RADIUS = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

// Status/Semantic colors (legacy compatibility)
export const SUCCESS = darkColors.success;
export const SUCCESS_BG20 = 'rgba(34, 197, 94, 0.2)';
export const SUCCESS_BG10 = darkColors.successSubtle;

export const WARNING = darkColors.warning;
export const WARNING_BG20 = 'rgba(245, 158, 11, 0.2)';
export const WARNING_BG10 = darkColors.warningSubtle;
export const WARNING_BORDER30 = 'rgba(245, 158, 11, 0.3)';

export const ERROR = darkColors.error;
export const ERROR_TEXT = darkColors.error;
export const ERROR_BG20 = 'rgba(239, 68, 68, 0.2)';
export const ERROR_BG10 = darkColors.errorSubtle;
export const ERROR_BORDER30 = 'rgba(239, 68, 68, 0.3)';

export const INFO = darkColors.info;
export const INFO_BG20 = 'rgba(59, 130, 246, 0.2)';
export const INFO_BG10 = darkColors.infoSubtle;

export const ORANGE = '#f97316';

// Status badge colors
export const STATUS_PENDING = darkColors.warning;
export const STATUS_ACCEPTED = darkColors.success;
export const STATUS_REJECTED = darkColors.error;
export const STATUS_CHECKED_IN = darkColors.info;
export const GOLD = '#fbbf24';
export const GOLD_BG20 = 'rgba(251, 191, 36, 0.2)';
export const GOLD_BG10 = 'rgba(251, 191, 36, 0.1)';

// Typography tokens - Inter + JetBrains Mono
export const TYPO = {
  h1: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 32,
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: '-0.02em',
  },
  h2: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 24,
    fontWeight: 600,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
  },
  h3: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: 18,
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
    letterSpacing: '0.05em',
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
  // Legacy typography
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

// Shadow tokens - subtle depth
export const SHADOW = {
  card: '0 1px 3px rgba(0, 0, 0, 0.3)',
  elevated: '0 4px 12px rgba(0, 0, 0, 0.4)',
  modal: '0 8px 32px rgba(0, 0, 0, 0.6)',
  glow: '0 0 30px rgba(139, 92, 246, 0.3)',
} as const;

// Breakpoints
export const BREAKPOINTS = { mobile: 768, tablet: 1024 };

// Animation timing
export const TIMING = {
  fast: '100ms',
  base: '150ms',
  slow: '250ms',
} as const;
