// ============================================================
// Hack the Valley Design System
// Raw Hacker Aesthetic: Monochrome, IBM Plex, Minimal
// ============================================================

// Theme type definition
export type ThemeMode = 'light' | 'dark';

// Color tokens for light mode
const lightColors = {
  bg: '#ffffff',
  bgSubtle: '#f7f7f7',
  bgElevated: '#ffffff',
  textPrimary: '#000000',
  textSecondary: '#444444',
  textMuted: '#666666',
  border: '#e0e0e0',
  borderStrong: '#000000',
  link: '#0066cc',
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#dc2626',
  codeBg: '#f5f5f5',
  codeText: '#444444',
  prompt: '#22c55e',
} as const;

// Color tokens for dark mode - softer dark gray (not jet black)
const darkColors = {
  bg: '#1a1a1a',
  bgSubtle: '#262626',
  bgElevated: '#2a2a2a',
  textPrimary: '#ffffff',
  textSecondary: '#a0a0a0',
  textMuted: '#737373',
  border: '#404040',
  borderStrong: '#555555',
  link: '#66b3ff',
  success: '#22c55e',
  warning: '#fbbf24',
  error: '#ef4444',
  codeBg: '#1f1f1f',
  codeText: '#a0a0a0',
  prompt: '#22c55e',
} as const;

// Export color getters based on theme
export const getColors = (mode: ThemeMode) => mode === 'light' ? lightColors : darkColors;

// Legacy exports for backward compatibility during migration
export const PAGE_BG = '#1a1a1a';
export const CARD_BG = '#262626';
export const INPUT_BG = '#2a2a2a';
export const NAV_BG = '#1a1a1a';
export const EXPANDED_BG = '#1a1a1a';
export const TABLE_HOVER = '#1a1a1a';
export const PRIMARY = '#ffffff';
export const PRIMARY_HOVER = '#e0e0e0';
export const PRIMARY_DISABLED = '#555555';
export const PRIMARY_BG20 = '#ffffff20';
export const CYAN = '#999999';
export const CYAN_BG20 = '#99999920';
export const CYAN_BG10 = '#99999910';
export const TEXT_PRIMARY = '#ffffff';
export const TEXT_SECONDARY = '#a0a0a0';
export const TEXT_MUTED = '#737373';
export const TEXT_DIM = '#444444';
export const TEXT_WHITE = '#ffffff';
export const BORDER = '#404040';
export const BORDER_LIGHT = '#444444';
export const INPUT_BORDER = '#333333';
export const RADIUS = { sm: 4, md: 4, lg: 4, full: 4 };
export const SPACE = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 };

// Status/Semantic colors (legacy compatibility)
export const SUCCESS = '#22c55e';
export const SUCCESS_BG20 = '#22c55e20';
export const SUCCESS_BG10 = '#22c55e10';
export const WARNING = '#fbbf24';
export const WARNING_BG20 = '#fbbf2420';
export const WARNING_BG10 = '#fbbf2410';
export const WARNING_BORDER30 = '#fbbf2430';
export const ERROR = '#ef4444';
export const ERROR_TEXT = '#ef4444';
export const ERROR_BG20 = '#ef444420';
export const ERROR_BG10 = '#ef444410';
export const ERROR_BORDER30 = '#ef444430';
export const INFO = '#3b82f6';
export const INFO_BG20 = '#3b82f620';
export const INFO_BG10 = '#3b82f610';
export const ORANGE = '#f97316';

// Status badge colors
export const STATUS_PENDING = '#f59e0b';
export const STATUS_ACCEPTED = '#22c55e';
export const STATUS_REJECTED = '#ef4444';
export const STATUS_CHECKED_IN = '#3b82f6';
export const GOLD = '#fbbf24';
export const GOLD_BG20 = '#fbbf2420';
export const GOLD_BG10 = '#fbbf2410';

// Typography tokens
export const TYPO = {
  h1: { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 42, fontWeight: 600, lineHeight: 1.1, letterSpacing: '-0.02em' },
  h2: { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 32, fontWeight: 600, lineHeight: 1.2, letterSpacing: '-0.01em' },
  h3: { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 20, fontWeight: 600, lineHeight: 1.3 },
  body: { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 16, fontWeight: 400, lineHeight: 1.6 },
  small: { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 14, fontWeight: 400, lineHeight: 1.5 },
  label: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, fontWeight: 500, lineHeight: 1.0, textTransform: 'uppercase' as const, letterSpacing: '0.05em' },
  mono: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 400, lineHeight: 1.5 },
  'mono-lg': { fontFamily: "'IBM Plex Mono', monospace", fontSize: 24, fontWeight: 400, lineHeight: 1.2, letterSpacing: '-0.02em' },
  // Legacy typography exports for backward compatibility
  'body-lg': { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 16, fontWeight: 400, lineHeight: 1.6 },
  'body-sm': { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 14, fontWeight: 400, lineHeight: 1.5 },
  'mono-data': { fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 500, lineHeight: 1.0, letterSpacing: '0.05em', fontVariantNumeric: 'tabular-nums' as const },
  'label-caps': { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 12, fontWeight: 700, lineHeight: 1.0, letterSpacing: '0.08em' },
  'score-lg': { fontFamily: "'IBM Plex Sans', -apple-system, sans-serif", fontSize: 32, fontWeight: 700, lineHeight: 1, letterSpacing: '-0.02em' },
} as const;

// Shadow tokens (flat design - minimal shadows)
export const SHADOW = {
  card: 'none',
  elevated: '0 1px 3px rgba(0,0,0,0.1)',
  modal: '0 4px 12px rgba(0,0,0,0.15)',
};

// Breakpoints
export const BREAKPOINTS = { mobile: 768, tablet: 1024 };
