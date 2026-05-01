# RowdyHacks

CSUB's hackathon platform — registration, check-in, judging, and everything in between. Built for California State University, Bakersfield.

## Features

### Hackathon Experience
- Full hackathon CRUD with deadlines, capacity caps, and waitlist auto-promotion
- Multi-organizer and co-organizer support
- Comprehensive registration wizard (team, experience, t-shirt, dietary restrictions, links)
- Bulk accept/reject/waitlist with CSV export for t-shirt and dietary planning
- Announcements system (organizer-to-participant messaging)
- Public homepage with schedule, WiFi info, and countdown timer

### Check-In & Wallet
- QR code generation and scan-based check-in
- Apple Wallet passes (.pkpass with PKCS7 signing)
- Google Wallet passes (REST API with JWT save URLs)
- Scan history tracking

### Judging Portal
- Custom rubric builder per hackathon
- ELO-based ranking system
- Conflict of interest declarations
- Public leaderboard and project gallery
- Judge redirect and scoring pages

### Submission Integrity
- **Timeline Analysis** — Git commit forensics to verify work was done during the hackathon window
- **Devpost Alignment** — AI-powered comparison of Devpost description vs. actual repository content
- **AI Detection** — Heuristic + perplexity-based AI-generated code detection
- **Code Similarity** — SimHash-based cross-team similarity scoring
- **Cross-Hackathon** — Duplicate submission detection across different hackathons
- **Repeat Offender** — Track users who submit suspicious projects repeatedly
- Plus: dead dependency check, commit quality, repo age, build verification, file timestamp analysis, contributor audit

### Infrastructure
- Discord bot with interactive Accept/Reject application components
- Stealth Devpost crawler (browser fingerprint rotation, WAF bypass, human-like delays)
- WebSocket real-time updates
- Prometheus metrics, Sentry error tracking, structured logging (structlog)
- PWA support (offline-capable, installable on mobile)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 8, React Router 7, vite-plugin-pwa |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL 15 (prod) / SQLite (dev) via SQLAlchemy 2.0 (async) |
| Cache | Redis 7 |
| Auth | JWT, OAuth (Google, GitHub, Discord, Apple Sign In) |
| Scraping | httpx, BeautifulSoup4, Playwright (stealth) |
| LLM | Anthropic Claude, DeepSeek, Poolside Laguna |
| Wallet | passbook (Apple), google-auth (Google) |
| Discord | discord.py |
| Monitoring | Sentry, Prometheus, structlog |

## Quick Start (Docker Compose)

```bash
git clone https://github.com/mintychochip/rowdyhacks.git
cd rowdyhacks
cp .env.example .env
# Edit .env with your SECRET_KEY, POSTGRES_PASSWORD, etc.
./scripts/init-ssl.sh
docker-compose up -d
```

This starts PostgreSQL, Redis, backend (port 8000), frontend (port 3000), and Nginx (ports 80/443).

Demo accounts are auto-seeded on startup (password `demo1234`):
- `alice@demo.com` — organizer
- `bob@demo.com` — participant
- `carol@demo.com` — organizer
- `dave@demo.com` — judge

## Development

**Frontend:**
```bash
cd frontend
npm install
npm run dev        # Vite dev server on port 5173
npm run build      # production build
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**Testing:**
```bash
cd backend
pytest              # 129+ tests
```

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key (32+ chars, required) |
| `POSTGRES_PASSWORD` | Database password |
| `LLM_API_KEY` | Optional, for AI-powered checks |
| `GITHUB_TOKEN` | Optional, for git analysis rate limits |
| `DISCORD_BOT_TOKEN` | Optional, for Discord bot |
| `REDIS_URL` | Redis connection URL |

All backend settings use the `HACKVERIFY_` prefix (loaded via pydantic-settings).

## Project Structure

```
rowdyhacks/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── analyzer.py       # Submission integrity pipeline
│   │   ├── routes/           # 16 route modules
│   │   ├── checks/           # 20+ integrity check modules
│   │   ├── crawler/          # Devpost bulk crawler
│   │   └── wallet/           # Apple/Google Wallet
│   └── tests/                # 129+ pytest tests
├── frontend/
│   ├── src/
│   │   ├── pages/            # 25 page components
│   │   ├── components/       # Shared UI components
│   │   └── theme.ts          # Design tokens (cosmic/space theme)
│   └── DESIGN.md             # Full design system docs
├── nginx/                    # Nginx config (SSL, WSS, rate limiting)
├── scripts/                  # Setup scripts
├── docker-compose.yml        # All services
└── .env.example              # Environment template
```

## License

MIT
