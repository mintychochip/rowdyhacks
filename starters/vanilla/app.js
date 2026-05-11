/**
 * OpenHack Vanilla Starter
 * Zero-build frontend that consumes the OpenHack backend API.
 */

/* ---------- Config ---------- */
function getClerkKey() {
  // 1. Try query param: ?clerk_key=pk_test_...
  const params = new URLSearchParams(window.location.search)
  const fromQuery = params.get('clerk_key')
  if (fromQuery) return fromQuery

  // 2. Try a simple config object injected by the host
  if (typeof window.OPENHACK_CONFIG !== 'undefined' && window.OPENHARK_CONFIG.clerkKey) {
    return window.OPENHACK_CONFIG.clerkKey
  }

  // 3. Fallback — set this in the HTML or here directly for development
  return ''
}

/* ---------- State ---------- */
const DEFAULT_BRANDING = {
  hackathon_name: 'OpenHack',
  hackathon_tagline: 'The open-source hackathon framework',
  hackathon_logo_url: '/openhack-logo.png',
  hackathon_primary_color: '#2563eb',
  hackathon_background_color: '#0f172a',
  hackathon_accent_color: '#06b6d4',
  hackathon_favicon_url: '/openhack-logo.png',
}

let branding = { ...DEFAULT_BRANDING }
let clerk = null

/* ---------- Branding / Theme ---------- */
function injectThemeCss() {
  const id = 'oh-theme-css'
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = '/api/config/theme.css'
  document.head.appendChild(link)
}

function setCssVariables(primary, background, accent) {
  const root = document.documentElement
  root.style.setProperty('--oh-primary', primary)
  root.style.setProperty('--oh-theme-color', background || '#060913')
  if (accent) root.style.setProperty('--oh-accent', accent)
}

function updateMeta(config) {
  document.title = config.hackathon_name || DEFAULT_BRANDING.hackathon_name
  const themeMeta = document.querySelector('meta[name="theme-color"]')
  if (themeMeta) {
    themeMeta.setAttribute('content', config.hackathon_primary_color || DEFAULT_BRANDING.hackathon_primary_color)
  }
  const favicon = document.querySelector('link[rel="icon"]')
  if (favicon && config.hackathon_favicon_url) {
    favicon.href = config.hackathon_favicon_url
  }
}

async function loadBranding() {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    const res = await fetch('/api/config', { signal: controller.signal })
    clearTimeout(timeout)

    if (!res.ok) throw new Error('HTTP ' + res.status)
    const data = await res.json()

    branding = {
      hackathon_name: data.hackathon_name || DEFAULT_BRANDING.hackathon_name,
      hackathon_tagline: data.hackathon_tagline || DEFAULT_BRANDING.hackathon_tagline,
      hackathon_logo_url: data.hackathon_logo_url || DEFAULT_BRANDING.hackathon_logo_url,
      hackathon_primary_color: data.hackathon_primary_color || DEFAULT_BRANDING.hackathon_primary_color,
      hackathon_background_color: data.hackathon_background_color || DEFAULT_BRANDING.hackathon_background_color,
      hackathon_accent_color: data.hackathon_accent_color || DEFAULT_BRANDING.hackathon_accent_color,
      hackathon_favicon_url: data.hackathon_favicon_url || DEFAULT_BRANDING.hackathon_favicon_url,
    }
  } catch (e) {
    console.warn('Failed to load branding, using defaults:', e)
    branding = { ...DEFAULT_BRANDING }
  }

  injectThemeCss()
  setCssVariables(branding.hackathon_primary_color, branding.hackathon_background_color, branding.hackathon_accent_color)
  updateMeta(branding)
}

/* ---------- UI ---------- */
function renderLanding() {
  document.getElementById('loader').style.display = 'none'
  document.getElementById('content').style.display = ''

  const nameEl = document.getElementById('hackathon-name')
  const titleEl = document.getElementById('title')
  const taglineEl = document.getElementById('tagline')
  const logoEl = document.getElementById('logo')

  if (nameEl) nameEl.textContent = branding.hackathon_name
  if (titleEl) titleEl.textContent = branding.hackathon_name
  if (taglineEl) taglineEl.textContent = branding.hackathon_tagline
  if (logoEl) logoEl.src = branding.hackathon_logo_url
}

/* ---------- Auth (Clerk) ---------- */
function renderAuthButton() {
  const container = document.getElementById('auth-container')
  if (!container) return

  const clerkKey = getClerkKey()
  if (!clerkKey) {
    container.innerHTML = '<span style="color:#94a3b8;font-size:12px;">Auth not configured</span>'
    return
  }

  // Load Clerk JS from CDN if not already loaded
  if (!window.Clerk) {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/@clerk/clerk-js@latest/dist/clerk.browser.js'
    script.async = true
    script.onload = () => initClerk(clerkKey)
    script.onerror = () => {
      container.innerHTML = '<span style="color:#ef4444;font-size:12px;">Failed to load auth</span>'
    }
    document.head.appendChild(script)
  } else {
    initClerk(clerkKey)
  }
}

async function initClerk(key) {
  const container = document.getElementById('auth-container')
  if (!container) return

  try {
    await window.Clerk.load({ publishableKey: key })
    clerk = window.Clerk

    const updateButton = () => {
      container.innerHTML = ''
      if (clerk.user) {
        const btn = document.createElement('button')
        btn.className = 'btn btn-primary'
        btn.textContent = 'Sign out'
        btn.addEventListener('click', () => clerk.signOut())
        container.appendChild(btn)
      } else {
        const btn = document.createElement('button')
        btn.className = 'btn btn-primary'
        btn.textContent = 'Sign in'
        btn.addEventListener('click', () => clerk.openSignIn())
        container.appendChild(btn)
      }
    }

    updateButton()
    clerk.addListener(updateButton)
  } catch (e) {
    console.error('Clerk init failed:', e)
    container.innerHTML = '<span style="color:#ef4444;font-size:12px;">Auth init failed</span>'
  }
}

/* ---------- Boot ---------- */
async function boot() {
  await loadBranding()
  renderLanding()
  renderAuthButton()
}

boot()
