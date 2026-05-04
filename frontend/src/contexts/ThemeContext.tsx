import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

type ThemeMode = 'dark' | 'light';

interface ThemeContextType {
  mode: ThemeMode;
  toggle: () => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType>({
  mode: 'dark',
  toggle: () => {},
  isDark: true,
});

export const useTheme = () => useContext(ThemeContext);

// Light mode overrides — CSS custom properties applied to :root
const LIGHT_VARS: Record<string, string> = {
  '--page-bg': '#f8fafc',
  '--card-bg': '#ffffff',
  '--input-bg': '#f1f5f9',
  '--nav-bg': '#ffffff',
  '--border': '#e2e8f0',
  '--input-border': '#cbd5e1',
  '--text-primary': '#0f172a',
  '--text-secondary': '#475569',
  '--text-muted': '#64748b',
  '--text-dim': '#94a3b8',
  '--table-hover': '#f1f5f9',
  '--shadow-card': '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
};

const DARK_VARS: Record<string, string> = {
  '--page-bg': '#0f172a',
  '--card-bg': '#1e293b',
  '--input-bg': '#334155',
  '--nav-bg': '#0f172a',
  '--border': '#1e293b',
  '--input-border': '#475569',
  '--text-primary': '#f1f5f9',
  '--text-secondary': '#94a3b8',
  '--text-muted': '#64748b',
  '--text-dim': '#475569',
  '--table-hover': '#334155',
  '--shadow-card': '0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)',
};

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('htv_theme');
    return (stored === 'light' || stored === 'dark') ? stored : 'dark';
  });

  const isDark = mode === 'dark';

  useEffect(() => {
    localStorage.setItem('htv_theme', mode);
    const vars = isDark ? DARK_VARS : LIGHT_VARS;
    const root = document.documentElement;
    Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    root.setAttribute('data-theme', mode);
  }, [mode, isDark]);

  const toggle = () => setMode(m => m === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider value={{ mode, toggle, isDark }}>
      {children}
    </ThemeContext.Provider>
  );
}
