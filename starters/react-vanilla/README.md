# OpenHack Starter — React + Vite + TypeScript

A minimal starter template for building custom frontends on top of the OpenHack backend API.

## Features

- Fetches `/api/config` on load and injects `theme.css` automatically
- Displays hackathon branding (name, tagline, logo)
- Clerk authentication (sign-in / sign-out)
- Graceful loading states with default branding fallback
- Proxy configured for local dev against `http://localhost:8000`

## Quick Start

```bash
npm install
# Copy env and add your Clerk key
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## Build

```bash
npm run build
```

Output goes to `dist/` — serve with any static host.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_CLERK_PUBLISHABLE_KEY` | Yes | Clerk frontend API key |
| `VITE_API_URL` | No | Backend base URL (default `/api`) |

## Project Structure

```
src/
  main.tsx    Entry point — sets up ClerkProvider
  App.tsx     Branding loader + landing page layout
  index.css   Design system tokens + button styles
```

## Extending

- Add routes with `react-router-dom`
- Call backend APIs with `fetch('/api/...')` — Clerk tokens are sent automatically if you wire `getToken` into request headers (see the main `frontend/src/services/api.ts` for a full example)
- Replace the landing page in `App.tsx` with your custom experience
