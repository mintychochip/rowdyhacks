# HackVerify Project Journal

**Repository:** mintychochip/rowdyhacks  
**Started:** 2026-04-30  
**Status:** Active development

## Project Overview

HackVerify is a PWA that detects cheating in hackathon submissions. It accepts Devpost/GitHub URLs, runs integrity checks, and produces risk reports. Includes QR check-in with Apple/Google Wallet integration and a judging portal.

## Current Status

### Backend (FastAPI + SQLAlchemy)
- **Models:** All tables defined (users, hackathons, submissions, check_results, registrations, crawled_hackathons, crawled_projects, judging system)
- **Routes:** Auth, checks, dashboard, hackathons, registrations, checkin, QR, crawler, judging
- **Checks:** 16 checks implemented across categories: timeline, devpost_alignment, submission_history, asset_integrity, ai_detection, cross_hackathon, repeat_offender
- **Tests:** 105 passing, 2 failing
  - `test_check_commits_clean` - git log parsing issue
  - `test_full_judging_flow` - demo user email collision
- **Wallet:** Apple/Google pass generation stubs present
- **Crawler:** Devpost bulk crawler with scheduler

### Frontend (React + Vite + TypeScript)
- **Routes:** All pages scaffolded (Analyze, Report, Dashboard, Auth, Register, Registrations, CheckIn, Judging)
- **Components:** Layout, QRCodeDisplay, WalletButtons, StatusBadge, ScoreCircle, CheckResultRow
- **Services:** API client configured

## Known Issues

1. **test_check_commits_clean** - Timeline check returns score 50 when git log fails (should handle gracefully)
2. **test_full_judging_flow** - Email uniqueness collision with demo seed data
3. **requirements.txt** - passbook version fixed (1.4.0 → 1.0.2)
4. **Missing dependencies** - scikit-learn, bcrypt not in requirements.txt

## Milestones

### Milestone 1: Backend Stabilization (Current)
- Fix failing tests
- Add missing dependencies to requirements.txt
- Verify all check implementations

### Milestone 2: Frontend Completion
- Build and verify all page components
- Integrate with backend APIs
- PWA manifest and service worker

### Milestone 3: Wallet Integration
- Apple Wallet .pkpass generation
- Google Wallet API integration
- QR token validation

### Milestone 4: Crawler & Cross-Hackathon
- Verify Devpost crawler scheduler
- Cross-hackathon duplicate detection
- Repeat offender tracking

### Milestone 5: Judging Portal
- Rubric builder
- Judge assignments
- Scoring interface

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-30 | Fixed passbook 1.4.0 → 1.0.2 | 1.4.0 doesn't exist on PyPI |
| 2026-04-30 | Added scikit-learn, bcrypt to deps | Required for tests to run |

## Blockers

None currently.

## Next Actions

1. Fix 2 failing tests
2. Update requirements.txt with all missing deps
3. Verify frontend builds
4. Run full integration test
