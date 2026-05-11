# OpenHack Rebrand — Design Spec

**Date:** 2026-05-10
**Project:** OpenHack (formerly RowdyHacks / Hack the Valley)
**Goal:** Transform the hackathon platform from a single-event branded product into a self-hosted, configurable, open-source hackathon framework.

---

## Overview

The current codebase is deeply branded for "Hack the Valley" / "RowdyHacks" — hardcoded names, URLs, logos, colors, and Docker image names. This spec defines a three-phase rebrand:

1. **Mechanical rename** — every instance of the old brand becomes `openhack` / `OpenHack` or a generic placeholder.
2. **Env-based branding system** — backend serves per-deployment config; frontend consumes it at runtime.
3. **TUI installer** — a `curl | bash` bootstrapper downloads a Rust TUI binary that walks users through setup and deploys the stack via Docker Compose.

---

## Phase 1: Mechanical Rename

**Scope:** Pure text replacement. No logic changes.

### Target Strings to Replace

| Old String | Replacement | Notes |
|---|---|---|
| `rowdyhacks` | `openhack` | Repo name, package names, container names, image names |
| `Hack the Valley` | `OpenHack` | Human-readable brand name |
| `RowdyHacks` | `OpenHack` | CamelCase variants |
| `rowdyhackin` | `openhack` | Lowercase / domain-style variants |
| `rowdyhackin` | `openhack` | Domain slug |
| `htv-logo` | `openhack-logo` | Asset filenames |
| `htv-dark` | `openhack-dark` | Monaco editor theme name |
| `rowdyhackin.duckdns.org` | `openhack.dev` | Email domain placeholder |
| `rowdyhackin.duckdns.org` | `localhost` | Default domain placeholder |
| `rowdyhackin.vercel.app` | `localhost:5173` | Default dev URL placeholder |
| `Hack. Build. Create.` | `The open-source hackathon framework` | Tagline placeholder |
| `HTV` | `OH` | Short name / abbreviation |
| `Hackathon verification platform` | `The open-source hackathon framework` | PWA description |
| `ghcr.io/mintychochip/rowdyhacks` | `ghcr.io/mintychochip/openhack` | Docker registry path (hardcoded for rename; `DOCKER_REGISTRY` env var support deferred to Phase 2) |
| `2026` | `2025` | Event-specific year in UI text (treated as static for rename; dynamic `hackathon_year` field deferred to Phase 2) |

### File Groups (representative targets)

> **Note:** This table lists known hotspots. The actual rename must cover the **entire** codebase. Use the verification grep commands below to ensure nothing is missed.

| Group | Files |
|---|---|
| **Repo meta** | `package.json` |
| **Docker infra** | `docker-compose.yml`, `docker-compose.dev.yml` |
| **CI/CD** | `.github/workflows/build-push.yml`, `.github/workflows/ci.yml` |
| **Nginx / SSL** | `nginx/docker-entrypoint.sh`, `nginx/nginx.conf` |
| **Scripts** | `scripts/dev.sh`, `scripts/dev.ps1`, `scripts/dev-docker.ps1`, `scripts/deploy.sh` |
| **Docs** | `README.md`, `CLAUDE.md`, `AGENTS.md`, `DEPLOY.md`, `PROJECT_JOURNAL.md`, `DESIGN.md` |
| **Frontend code** | `frontend/index.html`, `frontend/vite.config.ts`, `frontend/src/theme.ts`, `frontend/src/index.css`, `frontend/src/components/Layout.tsx`, `frontend/src/agent/context.ts`, `frontend/src/agent/WebContainer.ts`, `frontend/src/utils/languageConfig.ts`, `frontend/src/components/assistant/StandaloneEditor.tsx`, `frontend/public/sitemap.xml`, `frontend/.env.production`, and **all `frontend/src/pages/*.tsx` files** |
| **Backend code** | `backend/app/config.py`, `backend/app/assistant/__init__.py`, `backend/app/assistant/context_builder.py`, `backend/app/assistant/site_pages.py`, `backend/app/routes/assistant.py`, `backend/app/models.py`, `backend/app/models_assistant.py`, `backend/scripts/bulk_seed.py`, and **all `backend/app/routes/*.py` and `backend/app/checks/*.py` files** |
| **Static assets** | `frontend/public/htv-logo.png` → `frontend/public/openhack-logo.png` |
| **Design docs** | All `docs/superpowers/` specs and plans |
| **Root artifacts** | `assistant-*.md`, `dock-*.md`, `auth-check.md`, `auth_page.yml`, `current_state.yml`, `resources-page.yaml`, `signin_page.yml`, `final-state.md`, `linear-dock.md` |

### Special Cases (Phase 1 — text only)

| File | Required Change |
|---|---|
| `frontend/.env.production` | `VITE_API_URL=https://rowdyhackin.duckdns.org/api` → `VITE_API_URL=https://localhost/api` (placeholder domain, string replacement only) |

> **Note:** The `email_from` deprecation and `VITE_API_URL` functional routing change are addressed in Phase 2 as logic changes. Between Phase 1 and Phase 2 completion, the production build uses a placeholder domain that is non-functional but passes string verification.

### Database Table Names

SQLAlchemy `__tablename__` values and Alembic revision IDs are **not** in scope for the mechanical rename. Database schemas are functional, not branding. Table names like `users`, `hackathons`, `registrations` remain unchanged. Only human-readable strings inside model docstrings and comments are replaced.

### Verification

After Phase 1, the following grep commands must return **zero** results:

```bash
grep -ri "rowdyhacks" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ --exclude="package-lock.json" --exclude="*.lock" .
grep -ri "hack the valley" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ --exclude="package-lock.json" --exclude="*.lock" .
grep -ri "rowdyhackin" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ --exclude="package-lock.json" --exclude="*.lock" .
grep -ri "HTV" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ --exclude="package-lock.json" --exclude="*.lock" .
```

**Post-rename step:** Run `npm install` in `frontend/` to regenerate `package-lock.json` after `package.json` name change.

---

## Phase 2: Env-Based Branding System

### Backend

Add a `BrandingConfig` Pydantic model nested inside the existing `Settings` class in `backend/app/config.py`. It shares the same `model_config` (env prefix `HACKVERIFY_`) for consistent env var loading:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HACKVERIFY_",
        env_nested_delimiter="__",
    )
    # ... existing fields ...
    hackathon_name: str = Field(default="OpenHack")
    hackathon_tagline: str = Field(default="The open-source hackathon framework")
    hackathon_email: str = Field(default="noreply@example.com")
    hackathon_primary_color: str = Field(default="#2563eb")
    hackathon_logo_url: str = Field(default="/openhack-logo.png")
    hackathon_favicon_url: str = Field(default="/openhack-logo.png")
    hackathon_year: int = Field(default=2025)
```

Env vars are loaded with the `HACKVERIFY_` prefix: `HACKVERIFY_HACKATHON_NAME`, `HACKVERIFY_HACKATHON_TAGLINE`, etc. Fields are inlined into `Settings` to avoid Pydantic v2 nested delimiter complexity.

> **Security note:** `hackathon_email` defaults to `noreply@example.com`. Production deployments MUST override this in `.env` to a domain they control. The TUI installer enforces this with a non-empty validation prompt.

> **Deprecation:** The existing `email_from` field in `Settings` is deprecated. All code referencing `settings.email_from` must read `settings.hackathon_email` instead. Remove `email_from` from `Settings` during Phase 2 after all references are migrated.

Add a new route file `backend/app/routes/config.py` and register it in `backend/app/main.py`. Expose two public (no-auth) endpoints:

```
GET /api/config/branding
GET /api/config/manifest.json
```

Response (FastAPI serializes Pydantic fields as-is; the frontend reads these keys directly):

```json
{
  "hackathon_name": "OpenHack",
  "hackathon_tagline": "The open-source hackathon framework",
  "hackathon_email": "noreply@example.com",
  "hackathon_primary_color": "#2563eb",
  "hackathon_logo_url": "/openhack-logo.png",
  "hackathon_favicon_url": "/openhack-logo.png",
  "hackathon_year": 2025
}
```

### Frontend

1. **Config fetch on boot**: Before rendering routes, call `GET /api/config/branding` with a 3-second timeout and store in a Zustand store (`useBrandingStore`). Show a minimal loading spinner/splash until the fetch resolves or times out. On timeout, fall back to static defaults immediately. This prevents a flash of unbranded content and avoids hanging if the backend is slow.
2. **Dynamic replacements**:
   - `document.title` updated from `hackathon_name`
   - `Layout.tsx` logo text from `hackathon_name`; the inline SVG logo is replaced with an `<img>` tag reading `hackathon_logo_url`
   - `Layout.tsx` year text from `hackathon_year`
   - **Theme colors**: The `useBrandingStore` hook injects CSS custom properties on `document.documentElement`:
     ```css
     :root {
       --oh-primary: #2563eb;
       --oh-theme-color: #060913;
     }
     ```
     The hook sets `--oh-primary` to `hackathon_primary_color`. `--oh-theme-color` is computed by converting the primary color to HSL and setting lightness to 10% (dark background). Components that currently import `PRIMARY` or `PAGE_BG` from `theme.ts` are updated to read `getComputedStyle(document.documentElement).getPropertyValue('--oh-primary')` at runtime, with `theme.ts` constants serving as hydration-time fallbacks only.
   - AI assistant system prompt templates use `hackathon_name` and `hackathon_tagline`. The hardcoded strings in `frontend/src/agent/context.ts` and `backend/app/assistant/context_builder.py` are replaced with Python `string.Template` style: `"You are an AI assistant for $hackathon_name, $hackathon_tagline."` (replaced via `.replace()` at runtime before passing to the LLM).
   - **PWA manifest**: The backend serves `GET /api/config/manifest.json` which returns a valid Web App Manifest:
     ```json
     {
       "name": "OpenHack",
       "short_name": "OH",
       "start_url": "/",
       "display": "standalone",
       "background_color": "#0f172a",
       "theme_color": "#2563eb",
       "icons": [{"src": "/openhack-logo.png", "sizes": "512x512", "type": "image/png"}]
     }
     ```
     Values are interpolated from `BrandingConfig`. The endpoint sets `Cache-Control: no-cache` so branding changes are picked up immediately (browsers aggressively cache `manifest.json`). The `index.html` references `/api/config/manifest.json` instead of a static file.
3. **Fallback**: If the backend is unreachable, use static defaults (`OpenHack`).
4. **`index.html` static meta**: The hardcoded `<title>`, favicon links, and `theme-color` in `index.html` are replaced with generic placeholders (`<title>OpenHack</title>`, `/openhack-logo.png`) that match the default config. The frontend JS immediately overwrites `theme-color`, `apple-mobile-web-app-title`, and `title` after the branding fetch. Server-side templating is not required for v1.

### Docker Compose

Both `docker-compose.yml` and `docker-compose.dev.yml` pass branding vars to the **backend container** via the `env_file:` directive pointing to `.env`. The backend `environment:` block remains explicit for non-branding vars (secrets, DB URLs, etc.).

```yaml
services:
  backend:
    env_file:
      - .env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      # ... other explicit env vars
```

The **frontend** fetches branding at runtime from `GET /api/config/branding` — no build-time replacement or build args are used. This satisfies the requirement that branding updates do not require a frontend rebuild.

---

## Phase 3: TUI Installer

### User Flow

```
$ curl -sSL https://get.openhack.dev | bash
  ↓
Bootstrapper (shell script):
  1. Detect OS / arch (uname -sm)
  2. Download openhack-installer binary from GitHub Releases
  3. Verify checksum (SHA-256, mandatory — abort on mismatch)
  4. Execute binary
  ↓
TUI Binary (Rust + ratatui):
  1. Splash screen with OpenHack ASCII logo
  2. Step wizard:
     - Hackathon Name
     - Domain
     - Email (validated non-empty, must contain @)
     - Primary Color (hex input + 6 preset swatches)
     - Logo path (optional, default OpenHack logo)
     - Review summary
  3. Clone the application repo into `./openhack` (or use existing if present)
  4. Write `.env` file inside `./openhack`
  5. Run `docker compose up -d` (modern Docker plugin; falls back to `docker-compose` if unavailable) (live progress bar + compose stdout)
  6. Done screen with access URLs and next steps
```

### Bootstrapper Script (`install.sh`)

The bootstrapper is a POSIX-compatible shell script (~80 lines) served at `https://get.openhack.dev`:

```bash
#!/bin/sh
set -e

REPO="mintychochip/openhack"
VERSION="latest"
ARCH=$(uname -sm | tr '[:upper:]' '[:lower:]' | sed 's/ /-/')
BINARY="openhack-installer-${ARCH}"
URL="https://github.com/${REPO}/releases/latest/download/${BINARY}"
CHECKSUM_URL="${URL}.sha256"

# Determine writable directory (handle noexec /tmp)
if [ -d "$HOME" ] && [ -w "$HOME" ]; then
  WORKDIR="$HOME/.openhack/tmp"
  mkdir -p "$WORKDIR"
else
  WORKDIR="/tmp"
fi

# Download binary + checksum
curl -sSL "$URL" -o "$WORKDIR/openhack-installer"
curl -sSL "$CHECKSUM_URL" -o "$WORKDIR/openhack-installer.sha256"

# Verify checksum (mandatory, portable across GNU/BSD)
EXPECTED=$(cat "$WORKDIR/openhack-installer.sha256" | awk '{print $1}')
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL=$(sha256sum "$WORKDIR/openhack-installer" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL=$(shasum -a 256 "$WORKDIR/openhack-installer" | awk '{print $1}')
else
  echo "Error: sha256sum or shasum required for checksum verification" >&2
  exit 1
fi
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "Error: checksum mismatch — download may be corrupted" >&2
  exit 1
fi

chmod +x "$WORKDIR/openhack-installer"
exec "$WORKDIR/openhack-installer"
```

> **Note:** The `VERSION` env var cannot be passed through `curl | bash`. To install a specific version, download the bootstrapper first: `curl -o install.sh https://get.openhack.dev && VERSION=1.2.3 bash install.sh`.

### Asset Acquisition

The TUI binary does **not** embed the full application. Instead it:

1. Checks if `./openhack/` exists (from a previous install)
2. If not, runs `git clone https://github.com/mintychochip/openhack.git ./openhack`
3. All subsequent operations (`docker-compose`, `.env` writing) happen inside `./openhack/`

This keeps the installer binary small (~2 MB) and ensures users always get the latest application code.

### Project Structure

```
installer/
  Cargo.toml
  src/
    main.rs          # Entry point
    app.rs           # ratatui App state machine
    ui.rs            # Draw functions (widgets, layout, styling)
    wizard.rs        # Wizard step logic and validation
    docker.rs        # docker-compose wrapper (tokio::process)
    config.rs        # .env file generation
  assets/
    openhack-logo.png
```

### Distribution

- **GitHub Actions** builds the Rust binary for:
  - `linux-x86_64`
  - `linux-arm64`
  - `darwin-x86_64`
  - `darwin-arm64`
  - `windows-x86_64`
- **GitHub Releases** hosts the binaries with checksums
- **Linux/macOS**: Bootstrapper script served from `get.openhack.dev` (or `raw.githubusercontent.com` as fallback) via `curl | bash`
- **Windows**: Users download `openhack-installer-windows-x86_64.exe` directly from GitHub Releases and run it. No PowerShell bootstrapper for v1.

### Error Handling

The TUI handles the following error states gracefully with user-friendly messages and recovery paths:

| Error | Behavior |
|---|---|
| Docker not installed | Fatal — print install instructions and exit with code 1 |
| Docker Compose not found | Fatal — print install instructions and exit with code 1 |
| Ports already bound (80, 443, 5432, 6379, 6333, 9000, 9001) | Warning prompt — instruct user to free ports or manually edit `.env`/compose before retry |
| Existing `.env` file | Prompt — overwrite, merge, or abort |
| `docker compose up` fails | Show last 50 lines of stderr, offer retry or abort |
| Git clone fails | Retry once with `--depth 1`, then fatal with manual clone instructions |
| Invalid hex color | Re-prompt with inline validation error |
| Invalid email | Re-prompt with inline validation error |

### Dependencies

- `ratatui` — TUI framework
- `crossterm` — Cross-platform terminal control
- `tokio` — Async runtime (for running docker-compose)
- `color-eyre` — Error handling with pretty backtraces
- `serde` — Config serialization

---

## OAuth Reconfiguration Note

The current OAuth provider configurations (Google, GitHub, Discord, Apple) contain old-brand strings in application names and authorized redirect URLs. These **must be manually reconfigured** by each self-hosting organization:

1. Create new OAuth apps with the organization's name (not `OpenHack`)
2. Set redirect URLs to the organization's domain (e.g., `https://hack.myuni.edu/api/auth/callback`)
3. Update `CLERK_SECRET_KEY`, `VITE_CLERK_PUBLISHABLE_KEY`, and OAuth client secrets in `.env`

This is out of scope for the mechanical rebrand but must be documented in `README.md` for self-hosters.

## Out of Scope (for this spec)

- Frontend dynamic theming (dark/light toggle, full CSS variable swap) — deferred to a future vibecoding pass
- Multi-language support in the installer — English only for v1
- Cloud deployment options (AWS, GCP, DigitalOcean) — Docker-only for v1
- Logo generation / AI theming — manual upload only for v1

## Implementation Plan Scope

This spec covers three sequential phases. Each phase will receive its own independent `PLAN.md` to keep review cycles focused:

1. **Plan 1:** Phase 1 — Mechanical Rename (pure string replacement, no logic changes)
2. **Plan 2:** Phase 2 — Env-Based Branding System (backend config API + frontend runtime fetch)
3. **Plan 3:** Phase 3 — TUI Installer (Rust binary + bootstrapper + GitHub Actions release matrix)

---

## Test Strategy

### Phase 1
- All existing tests must pass after the mechanical rename.
- Tests that assert on brand strings (e.g., `test_auth.py`, `test_models.py`) must be updated to reference `OpenHack`.
- `grep` verification excludes lockfiles; run `npm install` in `frontend/` to regenerate `package-lock.json` post-rename, then verify the lockfile no longer contains the old package name.

### Phase 2
- New test: `test_branding_api.py` — asserts `GET /api/config/branding` returns default values when no `.env` overrides are set, and correct overrides when `.env` is populated.
- Frontend integration test: verifies `useBrandingStore` hydrates correctly and updates `document.title`.
- Backend test: verifies `Settings` loads env vars with `HACKVERIFY_` prefix.

### Phase 3
- CI test: GitHub Actions builds the installer for all 5 targets and uploads artifacts.
- E2E test (manual): `curl | bash` on a fresh Ubuntu VM produces a reachable stack at `http://localhost`.
- Windows test: PowerShell download + manual execution of `.exe` installer works.

## Acceptance Criteria

1. `grep` for old brand strings returns zero results after Phase 1 (excluding lockfiles)
2. All tests pass after Phase 1
3. `GET /api/config/branding` returns correct values from `.env`
4. Frontend title, logo text, year, and primary color update from config without rebuild
5. Installer binary runs on Linux/macOS/Windows and produces a working Docker Compose stack
6. `curl | bash` flow works end-to-end on a fresh Ubuntu VM
