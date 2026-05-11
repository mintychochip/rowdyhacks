# OpenHack Starter — Vanilla HTML/CSS/JS

A zero-build starter template for building custom frontends on top of the OpenHack backend API. No bundler, no dependencies — just open `index.html` in a browser (or serve with any static file server).

## Features

- Fetches `/api/config` on load and injects `theme.css` automatically
- Displays hackathon branding (name, tagline, logo)
- Clerk authentication (sign-in / sign-out) loaded from CDN
- Graceful loading states with default branding fallback

## Quick Start

### Option A: Open directly
Open `index.html` in your browser. For the API calls to work you may need to disable CORS or serve through a proxy.

### Option B: Serve with a static server
```bash
# Python 3
python -m http.server 8080

# Node (if npx is available)
npx serve .

# Or any static file server you prefer
```

Then open `http://localhost:8080`.

### Option C: Behind nginx (production)
Place these files in a directory served by nginx and proxy `/api` to the OpenHack backend.

```nginx
location /api {
    proxy_pass http://localhost:8000;
}
```

## Configuration

### Clerk Auth Key
The starter needs a **Clerk publishable key** to enable authentication. You can provide it in one of three ways:

1. **Query parameter** (quickest for testing):
   ```
   http://localhost:8080/?clerk_key=pk_test_...
   ```

2. **Global config object** (embed in HTML before `app.js`):
   ```html
   <script>
     window.OPENHACK_CONFIG = { clerkKey: 'pk_test_...' };
   </script>
   ```

3. **Edit `app.js` directly** (not recommended for production):
   Change the fallback return value in `getClerkKey()`.

## File Structure

```
index.html   Landing page shell
styles.css   Design system tokens + layout + button styles
app.js       Config fetch, theme injection, Clerk auth init
```

## Extending

- Add new pages by creating additional `.html` files and linking between them
- Call backend APIs with `fetch('/api/...')` — include the Clerk session token in the `Authorization: Bearer <token>` header if endpoints require auth
- Customize colors in `styles.css` `:root` or let the backend drive them via `theme.css`
