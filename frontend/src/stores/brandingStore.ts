import { create } from 'zustand';

export interface BrandingConfig {
  hackathon_name: string;
  hackathon_tagline: string;
  hackathon_email: string;
  hackathon_primary_color: string;
  hackathon_logo_url: string;
  hackathon_favicon_url: string;
  hackathon_year: number;
  hackathon_background_color?: string;
  hackathon_accent_color?: string;
  hackathon_font_heading?: string;
  hackathon_font_body?: string;
  registration_open?: string;
  judging_enabled?: string;
}

const DEFAULT_BRANDING: BrandingConfig = {
  hackathon_name: 'OpenHack',
  hackathon_tagline: 'The open-source hackathon framework',
  hackathon_email: 'noreply@example.com',
  hackathon_primary_color: '#2563eb',
  hackathon_logo_url: '/openhack-logo.png',
  hackathon_favicon_url: '/openhack-logo.png',
  hackathon_year: 2025,
  hackathon_background_color: '#0f172a',
  hackathon_accent_color: '#06b6d4',
};

interface BrandingState {
  branding: BrandingConfig;
  loaded: boolean;
  loadBranding: () => Promise<void>;
}

function setCssVariables(primary: string, background?: string, accent?: string) {
  const root = document.documentElement;
  root.style.setProperty('--oh-primary', primary);
  root.style.setProperty('--oh-theme-color', background || '#060913');
  if (accent) root.style.setProperty('--oh-accent', accent);
}

function injectThemeCss() {
  const id = 'oh-theme-css';
  if (document.getElementById(id)) return;
  const link = document.createElement('link');
  link.id = id;
  link.rel = 'stylesheet';
  link.href = '/api/config/theme.css';
  document.head.appendChild(link);
}

function updateMeta(config: BrandingConfig) {
  document.title = config.hackathon_name;
  const themeMeta = document.querySelector('meta[name="theme-color"]');
  if (themeMeta) {
    themeMeta.setAttribute('content', config.hackathon_primary_color);
  }
  const appleMeta = document.querySelector('meta[name="apple-mobile-web-app-title"]');
  if (appleMeta) {
    appleMeta.setAttribute('content', config.hackathon_name);
  }
  const favicon = document.querySelector('link[rel="icon"]') as HTMLLinkElement | null;
  if (favicon) {
    favicon.href = config.hackathon_favicon_url;
  }
}

export const useBrandingStore = create<BrandingState>((set) => ({
  branding: DEFAULT_BRANDING,
  loaded: false,
  loadBranding: async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const res = await fetch('/api/config', { signal: controller.signal });
      clearTimeout(timeout);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Record<string, string> = await res.json();

      const config: BrandingConfig = {
        hackathon_name: data.hackathon_name || DEFAULT_BRANDING.hackathon_name,
        hackathon_tagline: data.hackathon_tagline || DEFAULT_BRANDING.hackathon_tagline,
        hackathon_email: data.hackathon_email || DEFAULT_BRANDING.hackathon_email,
        hackathon_primary_color: data.hackathon_primary_color || DEFAULT_BRANDING.hackathon_primary_color,
        hackathon_logo_url: data.hackathon_logo_url || DEFAULT_BRANDING.hackathon_logo_url,
        hackathon_favicon_url: data.hackathon_favicon_url || DEFAULT_BRANDING.hackathon_favicon_url,
        hackathon_year: parseInt(data.hackathon_year || String(DEFAULT_BRANDING.hackathon_year), 10),
        hackathon_background_color: data.hackathon_background_color,
        hackathon_accent_color: data.hackathon_accent_color,
        hackathon_font_heading: data.hackathon_font_heading,
        hackathon_font_body: data.hackathon_font_body,
        registration_open: data.registration_open,
        judging_enabled: data.judging_enabled,
      };

      injectThemeCss();
      setCssVariables(config.hackathon_primary_color, config.hackathon_background_color, config.hackathon_accent_color);
      updateMeta(config);
      set({ branding: config, loaded: true });
    } catch {
      injectThemeCss();
      setCssVariables(DEFAULT_BRANDING.hackathon_primary_color);
      updateMeta(DEFAULT_BRANDING);
      set({ branding: DEFAULT_BRANDING, loaded: true });
    }
  },
}));
