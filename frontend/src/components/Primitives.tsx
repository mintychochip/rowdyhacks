import React from 'react';
import { CARD_BG, BORDER, TEXT_MUTED, TEXT_SECONDARY, TEXT_WHITE, PRIMARY, RADIUS, SHADOW } from '../theme';

// ── Card ────────────────────────────────────────────────────
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

// ── Badge ───────────────────────────────────────────────────
interface BadgeProps {
  children: React.ReactNode;
  color?: string;
  bgColor?: string;
  style?: React.CSSProperties;
}

export function Badge({ children, color = TEXT_SECONDARY, bgColor, style }: BadgeProps) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: RADIUS.full,
      fontSize: 12,
      fontWeight: 600,
      color,
      background: bgColor || `${color}18`,
      ...style,
    }}>
      {children}
    </span>
  );
}

// ── Button ──────────────────────────────────────────────────
interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  onClick?: () => void;
  disabled?: boolean;
  style?: React.CSSProperties;
  type?: 'button' | 'submit';
}

export function Button({ children, variant = 'primary', onClick, disabled, style, type = 'button' }: ButtonProps) {
  const base: React.CSSProperties = {
    padding: '8px 18px',
    fontSize: 13,
    fontWeight: 600,
    borderRadius: RADIUS.md,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.6 : 1,
    border: 'none',
    ...style,
  };

  const variants: Record<string, React.CSSProperties> = {
    primary: { background: PRIMARY, color: TEXT_WHITE },
    secondary: { background: 'none', border: `1px solid ${BORDER}`, color: TEXT_SECONDARY },
    ghost: { background: 'none', color: TEXT_MUTED },
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{ ...base, ...variants[variant] }}
    >
      {children}
    </button>
  );
}

// ── Table components ────────────────────────────────────────
interface TableProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export function Table({ children, style }: TableProps) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14, ...style }}>
      {children}
    </table>
  );
}

export function TableHeader({ children, style }: TableProps) {
  return (
    <thead>
      <tr style={{ borderBottom: `1px solid ${BORDER}`, textAlign: 'left' as const, ...style }}>
        {children}
      </tr>
    </thead>
  );
}

export function TableHeadCell({ children, align = 'left', style }: { children: React.ReactNode; align?: 'left' | 'right'; style?: React.CSSProperties }) {
  return (
    <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: align, ...style }}>
      {children}
    </th>
  );
}

export function TableRow({ children, style, onClick }: { children: React.ReactNode; style?: React.CSSProperties; onClick?: () => void }) {
  return (
    <tr
      onClick={onClick}
      style={{ borderBottom: `1px solid ${BORDER}`, cursor: onClick ? 'pointer' : undefined, ...style }}
    >
      {children}
    </tr>
  );
}

export function TableCell({ children, align = 'left', style, colSpan }: { children: React.ReactNode; align?: 'left' | 'right'; style?: React.CSSProperties; colSpan?: number }) {
  return (
    <td style={{ padding: '10px 16px', textAlign: align, ...style }} colSpan={colSpan}>
      {children}
    </td>
  );
}

// ── SectionTitle ────────────────────────────────────────────
export function SectionTitle({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      fontSize: 12,
      fontWeight: 700,
      lineHeight: 1,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: TEXT_MUTED,
      marginBottom: 16,
      ...style,
    }}>
      {children}
    </div>
  );
}
