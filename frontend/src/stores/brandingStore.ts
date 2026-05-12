import { create } from 'zustand';

export interface BrandingConfig {
  hackathon_name: string;
  hackathon_tagline: string;
  hackathon_email: string;
  hackathon_primary_color: string;
  hackathon_logo_url: string;
  hackathon_favicon_url: string;
  hackathon_year: number;
}

const DEFAULT_BRANDING: BrandingConfig = {
  hackathon_name: 'OpenHack',
  hackathon_tagline: 'The open-source hackathon framework',
  hackathon_email: 'noreply@example.com',
  hackathon_primary_color: '#2563eb',
  hackathon_logo_url: '/logo.png',
  hackathon_favicon_url: '/logo.png',
  hackathon_year: 2025,
};

interface BrandingState {
  branding: BrandingConfig;
  loaded: boolean;
  loadBranding: () => Promise<void>;
}

function setCssVariables(primary: string) {
  const root = document.documentElement;
  root.style.setProperty('--oh-primary', primary);
  root.style.setProperty('--oh-theme-color', '#060913');
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
      const res = await fetch('/api/config/branding', { signal: controller.signal });
      clearTimeout(timeout);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: BrandingConfig = await res.json();
      setCssVariables(data.hackathon_primary_color);
      updateMeta(data);
      set({ branding: data, loaded: true });
    } catch {
      setCssVariables(DEFAULT_BRANDING.hackathon_primary_color);
      updateMeta(DEFAULT_BRANDING);
      set({ branding: DEFAULT_BRANDING, loaded: true });
    }
  },
}));
