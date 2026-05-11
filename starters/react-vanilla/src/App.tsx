import { useEffect, useState } from 'react'
import { SignInButton, SignOutButton, useUser } from '@clerk/clerk-react'

interface BrandingConfig {
  hackathon_name: string
  hackathon_tagline: string
  hackathon_logo_url: string
  hackathon_primary_color?: string
  hackathon_background_color?: string
  hackathon_accent_color?: string
  hackathon_favicon_url?: string
}

const DEFAULT_BRANDING: BrandingConfig = {
  hackathon_name: 'OpenHack',
  hackathon_tagline: 'The open-source hackathon framework',
  hackathon_logo_url: '/openhack-logo.png',
  hackathon_primary_color: '#2563eb',
  hackathon_background_color: '#0f172a',
  hackathon_accent_color: '#06b6d4',
}

function injectThemeCss() {
  const id = 'oh-theme-css'
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = '/api/config/theme.css'
  document.head.appendChild(link)
}

function setCssVariables(primary: string, background?: string, accent?: string) {
  const root = document.documentElement
  root.style.setProperty('--oh-primary', primary)
  root.style.setProperty('--oh-theme-color', background || '#060913')
  if (accent) root.style.setProperty('--oh-accent', accent)
}

function updateMeta(config: BrandingConfig) {
  document.title = config.hackathon_name
  const themeMeta = document.querySelector('meta[name="theme-color"]')
  if (themeMeta) {
    themeMeta.setAttribute('content', config.hackathon_primary_color || DEFAULT_BRANDING.hackathon_primary_color!)
  }
  const favicon = document.querySelector('link[rel="icon"]') as HTMLLinkElement | null
  if (favicon && config.hackathon_favicon_url) {
    favicon.href = config.hackathon_favicon_url
  }
}

function useBranding() {
  const [branding, setBranding] = useState<BrandingConfig>(DEFAULT_BRANDING)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 3000)
        const res = await fetch('/api/config', { signal: controller.signal })
        clearTimeout(timeout)

        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: Record<string, string> = await res.json()

        if (cancelled) return

        const config: BrandingConfig = {
          hackathon_name: data.hackathon_name || DEFAULT_BRANDING.hackathon_name,
          hackathon_tagline: data.hackathon_tagline || DEFAULT_BRANDING.hackathon_tagline,
          hackathon_logo_url: data.hackathon_logo_url || DEFAULT_BRANDING.hackathon_logo_url,
          hackathon_primary_color: data.hackathon_primary_color || DEFAULT_BRANDING.hackathon_primary_color,
          hackathon_background_color: data.hackathon_background_color || DEFAULT_BRANDING.hackathon_background_color,
          hackathon_accent_color: data.hackathon_accent_color || DEFAULT_BRANDING.hackathon_accent_color,
          hackathon_favicon_url: data.hackathon_favicon_url,
        }

        injectThemeCss()
        setCssVariables(
          config.hackathon_primary_color || '#2563eb',
          config.hackathon_background_color,
          config.hackathon_accent_color
        )
        updateMeta(config)
        setBranding(config)
      } catch {
        injectThemeCss()
        setCssVariables(DEFAULT_BRANDING.hackathon_primary_color!)
        updateMeta(DEFAULT_BRANDING)
        setBranding(DEFAULT_BRANDING)
      } finally {
        if (!cancelled) setLoaded(true)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  return { branding, loaded }
}

export default function App() {
  const { branding, loaded } = useBranding()
  const { isSignedIn, isLoaded: userLoaded } = useUser()

  if (!loaded || !userLoaded) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: branding.hackathon_background_color || '#0f172a',
          color: '#f1f5f9',
          fontFamily: "'Inter', -apple-system, sans-serif",
        }}
      >
        <div>Loading {branding.hackathon_name || 'OpenHack'}...</div>
      </div>
    )
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: branding.hackathon_background_color || '#0f172a',
        color: '#f1f5f9',
        fontFamily: "'Inter', -apple-system, sans-serif",
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
          background: 'rgba(6, 9, 19, 0.6)',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {branding.hackathon_logo_url && (
            <img
              src={branding.hackathon_logo_url}
              alt="logo"
              style={{ height: 32, width: 'auto' }}
            />
          )}
          <span style={{ fontWeight: 700, fontSize: 18 }}>
            {branding.hackathon_name}
          </span>
        </div>
        <div>
          {isSignedIn ? (
            <SignOutButton>
              <button className="btn btn-primary">Sign out</button>
            </SignOutButton>
          ) : (
            <SignInButton mode="modal">
              <button className="btn btn-primary">Sign in</button>
            </SignInButton>
          )}
        </div>
      </header>

      <main
        style={{
          maxWidth: 720,
          margin: '0 auto',
          padding: '64px 24px',
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            fontSize: 48,
            fontWeight: 700,
            lineHeight: 1.1,
            marginBottom: 16,
            letterSpacing: '-0.02em',
            fontFamily: "'Space Grotesk', -apple-system, sans-serif",
          }}
        >
          {branding.hackathon_name}
        </h1>
        <p
          style={{
            fontSize: 20,
            color: '#94a3b8',
            lineHeight: 1.5,
            marginBottom: 32,
          }}
        >
          {branding.hackathon_tagline}
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <a href="/dashboard" className="btn btn-primary" style={{ textDecoration: 'none' }}>
            Go to Dashboard
          </a>
          <a href="/apply" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            Register
          </a>
        </div>
      </main>
    </div>
  )
}
