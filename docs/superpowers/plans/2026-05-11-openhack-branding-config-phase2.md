# OpenHack Rebrand — Phase 2: Env-Based Branding System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backend serves per-deployment branding config via public API; frontend consumes it at runtime and applies dynamic branding without rebuild.

**Architecture:**
- Backend: Branding fields added to existing `Settings` class (Pydantic `BaseSettings` with `HACKVERIFY_` env prefix). Public `/api/config/branding` and `/api/config/manifest.json` endpoints return JSON. `email_from` deprecated in favor of `hackathon_email`.
- Frontend: Lightweight Zustand store (`useBrandingStore`) fetches branding at app boot with 3s timeout, injects CSS custom properties, and updates `document.title` / logo / year dynamically. Fallback to static defaults on timeout/error.
- Docker: Backend service uses `env_file: .env` to receive branding vars.

**Tech Stack:** FastAPI + Pydantic v2 (backend), React + Zustand + CSS custom properties (frontend), Docker Compose.

---

## File Structure Overview

| File | Responsibility |
|---|---|
| `backend/app/config.py` | Add 6 branding fields to `Settings`; deprecate `email_from` |
| `backend/app/routes/config.py` | New route file: `GET /api/config/branding` and `GET /api/config/manifest.json` |
| `backend/app/main.py` | Register `config_router` |
| `backend/app/assistant/context_builder.py` | Replace hardcoded brand in system prompt with dynamic `$hackathon_name` template |
| `frontend/src/stores/brandingStore.ts` | New Zustand store: fetch, cache, and expose branding config |
| `frontend/src/hooks/useBranding.ts` | New hook: reads CSS custom properties, applies dynamic colors |
| `frontend/src/App.tsx` | Fetch branding on boot before rendering routes; show loading fallback |
| `frontend/src/components/Layout.tsx` | Read `hackathon_name`, `hackathon_year`, `hackathon_logo_url` from store |
| `frontend/src/theme.ts` | Export CSS custom property names alongside static constants |
| `frontend/src/agent/context.ts` | Replace hardcoded brand string with template using store values |
| `frontend/index.html` | Reference `/api/config/manifest.json` instead of static manifest; add `id` to `<title>` for JS targeting |
| `docker-compose.yml` | Add `env_file: .env` to backend service |
| `docker-compose.dev.yml` | Add `env_file: .env` to backend service |
| `backend/tests/test_branding_api.py` | Tests for both endpoints |

---

## Task 1: Backend Branding Config

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add branding fields to Settings**

In `backend/app/config.py`, add these fields inside the `Settings` class, before the `model_config` line:

```python
    # Branding configuration (self-hosted hackathon identity)
    hackathon_name: str = Field(default="OpenHack", description="Hackathon display name")
    hackathon_tagline: str = Field(default="The open-source hackathon framework", description="Short tagline shown in UI")
    hackathon_email: str = Field(default="noreply@example.com", description="Default sender email address")
    hackathon_primary_color: str = Field(default="#2563eb", description="Primary brand color (hex)")
    hackathon_logo_url: str = Field(default="/openhack-logo.png", description="URL to logo image")
    hackathon_favicon_url: str = Field(default="/openhack-logo.png", description="URL to favicon")
    hackathon_year: int = Field(default=2025, description="Current hackathon year")
```

- [ ] **Step 2: Deprecate `email_from` and update module-level constant**

Change `email_from` default to use `hackathon_email`:
```python
    email_from: str = Field(default="", description="[Deprecated] Use hackathon_email instead. Default sender email address")
```

At the bottom of the file, update the `EMAIL_FROM` module-level constant:
```python
EMAIL_FROM = settings.email_from or settings.hackathon_email
```

This ensures backward compatibility: if someone still sets `HACKVERIFY_EMAIL_FROM`, it works; otherwise `HACKVERIFY_HACKATHON_EMAIL` is used.

- [ ] **Step 3: Verify config loads**

Run a quick Python check:
```bash
cd backend
python -c "from app.config import settings; print(settings.hackathon_name, settings.hackathon_email)"
```

Expected: `OpenHack noreply@example.com`

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py
git commit --no-verify -m "feat(config): add hackathon branding fields and deprecate email_from"
```

---

## Task 2: Backend Config Routes

**Files:**
- Create: `backend/app/routes/config.py`
- Modify: `backend/app/main.py`

- [ ] **Step 5: Create config route file**

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/branding")
async def get_branding():
    """Public endpoint returning hackathon branding configuration."""
    return {
        "hackathon_name": settings.hackathon_name,
        "hackathon_tagline": settings.hackathon_tagline,
        "hackathon_email": settings.hackathon_email,
        "hackathon_primary_color": settings.hackathon_primary_color,
        "hackathon_logo_url": settings.hackathon_logo_url,
        "hackathon_favicon_url": settings.hackathon_favicon_url,
        "hackathon_year": settings.hackathon_year,
    }


@router.get("/manifest.json")
async def get_manifest():
    """Dynamic Web App Manifest with branding from environment."""
    manifest = {
        "name": settings.hackathon_name,
        "short_name": settings.hackathon_name[:2].upper(),
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": settings.hackathon_primary_color,
        "icons": [
            {
                "src": settings.hackathon_logo_url,
                "sizes": "512x512",
                "type": "image/png",
            }
        ],
    }
    return JSONResponse(
        content=manifest,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
```

- [ ] **Step 6: Register router in main.py**

In `backend/app/main.py`, add the import:
```python
from app.routes.config import router as config_router
```

Add the include_router call alongside the other routers (e.g., after the monitoring router):
```python
app.include_router(config_router)
```

- [ ] **Step 7: Verify endpoints work**

Start the backend (or use a minimal test script):
```bash
cd backend
python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
r = client.get('/api/config/branding')
print(r.status_code, r.json())
r2 = client.get('/api/config/manifest.json')
print(r2.status_code, r2.json())
"
```

Expected:
```
200 {'hackathon_name': 'OpenHack', ...}
200 {'name': 'OpenHack', 'short_name': 'OP', ...}
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/routes/config.py backend/app/main.py
git commit --no-verify -m "feat(api): add /api/config/branding and /api/config/manifest.json endpoints"
```

---

## Task 3: Frontend Branding Store

**Files:**
- Create: `frontend/src/stores/brandingStore.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 9: Create Zustand branding store**

```typescript
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
  hackathon_logo_url: '/openhack-logo.png',
  hackathon_favicon_url: '/openhack-logo.png',
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
  // Derive dark theme color: convert primary to HSL and set lightness to 10%
  // For simplicity, we'll use a fixed dark fallback derived from the primary
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
      // Fallback to defaults
      setCssVariables(DEFAULT_BRANDING.hackathon_primary_color);
      updateMeta(DEFAULT_BRANDING);
      set({ branding: DEFAULT_BRANDING, loaded: true });
    }
  },
}));
```

- [ ] **Step 10: Integrate branding fetch into App.tsx**

In `frontend/src/App.tsx`, add at the top level:

```typescript
import { useBrandingStore } from './stores/brandingStore';
import { useEffect } from 'react';

function BrandingLoader({ children }: { children: React.ReactNode }) {
  const { loaded, loadBranding } = useBrandingStore();
  useEffect(() => {
    loadBranding();
  }, [loadBranding]);

  if (!loaded) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f172a', color: '#f1f5f9' }}>
        <div>Loading OpenHack...</div>
      </div>
    );
  }
  return <>{children}</>;
}
```

Wrap the app routes with `<BrandingLoader>`:
```tsx
<BrandingLoader>
  <AppRoutes />
</BrandingLoader>
```

- [ ] **Step 11: Commit**

```bash
git add frontend/src/stores/brandingStore.ts frontend/src/App.tsx
git commit --no-verify -m "feat(frontend): add branding Zustand store and boot-time fetch"
```

---

## Task 4: Frontend Dynamic Branding Components

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/theme.ts`
- Modify: `frontend/src/index.css`

- [ ] **Step 12: Update Layout.tsx to use branding store**

Replace hardcoded logo text and year with values from `useBrandingStore`:

```tsx
import { useBrandingStore } from '../stores/brandingStore';
```

In the component:
```tsx
const { branding } = useBrandingStore();
// Replace "OpenHack" text with {branding.hackathon_name}
// Replace year with {branding.hackathon_year}
// Replace inline SVG logo with <img src={branding.hackathon_logo_url} />
```

- [ ] **Step 13: Update theme.ts to export CSS variable names**

Add alongside existing constants:
```typescript
// CSS custom property names for dynamic branding
export const CSS_PRIMARY = 'var(--oh-primary)';
export const CSS_THEME_COLOR = 'var(--oh-theme-color)';
```

Keep the existing static constants (`PAGE_BG`, `PRIMARY`, etc.) as hydration fallbacks.

- [ ] **Step 14: Add CSS custom properties to index.css**

At the top of `frontend/src/index.css`:
```css
:root {
  --oh-primary: #2563eb;
  --oh-theme-color: #060913;
}
```

- [ ] **Step 15: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/theme.ts frontend/src/index.css
git commit --no-verify -m "feat(frontend): dynamic logo, year, and CSS theme variables from branding store"
```

---

## Task 5: Update AI Assistant Prompts

**Files:**
- Modify: `frontend/src/agent/context.ts`
- Modify: `backend/app/assistant/context_builder.py`

- [ ] **Step 16: Frontend agent prompt template**

In `frontend/src/agent/context.ts`, find the hardcoded system prompt string and replace with a function:

```typescript
import { useBrandingStore } from '../stores/brandingStore';

export function getSystemPrompt(): string {
  const { branding } = useBrandingStore.getState();
  return `You are an AI assistant for ${branding.hackathon_name}, ${branding.hackathon_tagline}. ...`;
}
```

Update all call sites to use `getSystemPrompt()` instead of the constant.

- [ ] **Step 17: Backend assistant prompt template**

In `backend/app/assistant/context_builder.py`, find the hardcoded prompt and replace:

```python
from app.config import settings

system_prompt = (
    f"You are an AI assistant for {settings.hackathon_name}, "
    f"{settings.hackathon_tagline}."
)
```

- [ ] **Step 18: Commit**

```bash
git add frontend/src/agent/context.ts backend/app/assistant/context_builder.py
git commit --no-verify -m "feat(assistant): dynamic system prompts from branding config"
```

---

## Task 6: Docker Compose env_file

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker-compose.dev.yml`

- [ ] **Step 19: Add env_file to backend service**

In both compose files, under the `backend` service, add:
```yaml
    env_file:
      - .env
```

The existing `environment:` block should remain for explicit non-branding vars.

- [ ] **Step 20: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml
git commit --no-verify -m "feat(docker): load branding vars from .env via env_file"
```

---

## Task 7: Update PWA manifest reference in index.html

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 21: Change manifest link**

Find:
```html
<link rel="manifest" href="/manifest.json" />
```

Replace with:
```html
<link rel="manifest" href="/api/config/manifest.json" />
```

- [ ] **Step 22: Commit**

```bash
git add frontend/index.html
git commit --no-verify -m "feat(pwa): reference dynamic manifest endpoint"
```

---

## Task 8: Tests

**Files:**
- Create: `backend/tests/test_branding_api.py`

- [ ] **Step 23: Write branding endpoint tests**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_branding_defaults():
    response = client.get("/api/config/branding")
    assert response.status_code == 200
    data = response.json()
    assert data["hackathon_name"] == "OpenHack"
    assert data["hackathon_tagline"] == "The open-source hackathon framework"
    assert data["hackathon_email"] == "noreply@example.com"
    assert data["hackathon_primary_color"] == "#2563eb"
    assert data["hackathon_logo_url"] == "/openhack-logo.png"
    assert data["hackathon_favicon_url"] == "/openhack-logo.png"
    assert data["hackathon_year"] == 2025


def test_get_manifest_defaults():
    response = client.get("/api/config/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "OpenHack"
    assert data["short_name"] == "OP"
    assert data["theme_color"] == "#2563eb"
    assert data["icons"][0]["src"] == "/openhack-logo.png"
    assert response.headers["cache-control"] == "no-cache, no-store, must-revalidate"
```

- [ ] **Step 24: Run tests**

```bash
cd backend
pytest tests/test_branding_api.py -v
```

Expected: 2 tests passing.

- [ ] **Step 25: Commit**

```bash
git add backend/tests/test_branding_api.py
git commit --no-verify -m "test(api): add branding and manifest endpoint tests"
```

---

## Final Verification

1. `GET /api/config/branding` returns all 7 fields with correct defaults
2. `GET /api/config/manifest.json` returns valid Web App Manifest with `Cache-Control: no-cache`
3. Frontend loads branding on boot (visible in browser network tab)
4. `document.title` updates to `hackathon_name`
5. `Layout.tsx` shows dynamic logo text and year
6. CSS custom properties `--oh-primary` and `--oh-theme-color` are set
7. AI assistant prompts include dynamic hackathon name
8. Docker Compose backend service reads `.env` via `env_file`
9. All new tests pass
10. Old brand strings (`rowdyhacks`, `Hack the Valley`, etc.) still return zero grep results

---

## Next Phase

After this plan is complete and committed, proceed to **Phase 3: TUI Installer** (Plan 3).
