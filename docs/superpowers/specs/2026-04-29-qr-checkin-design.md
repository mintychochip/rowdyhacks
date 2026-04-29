# QR Code Check-In System — Design Spec

## Overview

Add a check-in system to HackVerify using QR codes with full Apple Wallet and Google Wallet pass integration. Participants get a QR code after organizer approval; organizers manage registrations and check attendees in. Row-level security ensures users can only see their own registration data.

## Data Model

### New table: `registrations`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (Guid) | PK |
| hackathon_id | UUID (Guid) | FK → hackathons, NOT NULL |
| user_id | UUID (Guid) | FK → users, NOT NULL |
| status | Enum(RegistrationStatus) | pending (default) |
| team_name | String(200) | nullable |
| team_members | JSONB | nullable, list of member name strings |
| qr_token | String(512) | nullable, signed JWT for QR code, set on acceptance |
| pass_serial_apple | String(128) | nullable, Apple Wallet pass serial for update tracking |
| pass_id_google | String(128) | nullable, Google Wallet object ID for update tracking |
| registered_at | DateTime(tz) | NOT NULL, default utcnow |
| accepted_at | DateTime(tz) | nullable |
| checked_in_at | DateTime(tz) | nullable |

### New enum: `RegistrationStatus`

- `pending` — registered, awaiting organizer approval
- `accepted` — approved by organizer, QR code generated and available
- `rejected` — declined by organizer
- `checked_in` — physically checked in at event (terminal state)

### QR Token Design

The QR code encodes a URL pointing to the check-in scan endpoint:

```
https://<domain>/api/checkin/scan?token=<jwt>
```

JWT payload:
- `reg_id` — registration UUID
- `user_id` — user UUID
- `hackathon_id` — hackathon UUID
- `exp` — hackathon end date + 24h buffer

This makes QR codes self-verifying: the token can be validated from its signature even without a database round-trip.

### Row-Level Security

Enforced at the application layer (route queries), not at the database level:

- **Participant:** queries filter by `user_id = current_user`, can only see own registrations
- **Organizer:** queries filter by `hackathon.organizer_id = current_user`, can only manage registrations for hackathons they own
- **Scan endpoint:** validates QR JWT signature + organizer Bearer token; rejects if either is invalid

Application-layer RLS is sufficient here: the query patterns are simple (single-owner or single-organizer), and DB-level RLS would add migration complexity without material security benefit given the ORM-level filtering.

## API Design

### Participant Endpoints

```
POST  /api/hackathons/{id}/register         — register for a hackathon
GET   /api/registrations                    — list current user's registrations
GET   /api/registrations/{id}               — view single registration (QR code included if accepted)
GET   /api/registrations/{id}/wallet/apple  — download Apple .pkpass file
GET   /api/registrations/{id}/wallet/google — redirect to Google Wallet "save" link
```

### Organizer Endpoints

```
GET    /api/hackathons/{hackathon_id}/registrations                          — list all registrations (paginated, filterable by status)
POST   /api/hackathons/{hackathon_id}/registrations/{registration_id}/accept     — approve (generates QR token + passes)
POST   /api/hackathons/{hackathon_id}/registrations/{registration_id}/reject     — reject a registration
POST   /api/hackathons/{hackathon_id}/registrations/{registration_id}/checkin    — mark as checked in
```

Pagination for the list endpoint: offset-based, default 20 items, max 100. Response includes `total`, `limit`, `offset`.

### Scan Endpoint

```
POST  /api/checkin/scan?token=<qr_jwt>    — validate QR, mark checked in, push pass update
```

Requires: valid organizer Bearer token + valid QR JWT. Both must pass validation.

### Error Responses

| Scenario | Status | Response |
|----------|--------|----------|
| QR token expired (`exp` passed) | 410 Gone | `{"error": "token_expired"}` |
| Registration not in `accepted` state (pending/rejected) | 409 Conflict | `{"error": "registration_not_active"}` |
| Already checked in (`checked_in` terminal state) | 409 Conflict | `{"error": "already_checked_in"}` |
| Invalid QR JWT signature | 401 Unauthorized | `{"error": "invalid_token"}` |
| Missing organizer auth | 401 Unauthorized | `{"error": "organizer_auth_required"}` |
| Registration revoked (accepted → rejected) | 410 Gone | `{"error": "registration_revoked"}`, wallet passes invalidated via push update |

### RLS Query Patterns

```python
# Participant: scoped to current user
stmt = select(Registration).where(Registration.user_id == current_user.id)

# Organizer: scoped to hackathons they own
stmt = (
    select(Registration)
    .join(Hackathon)
    .where(Hackathon.organizer_id == current_user.id)
)
```

## Wallet Pass Generation

### Apple Wallet (.pkpass)

**Prerequisites (user provides):**
- Apple Developer account ($99/yr)
- Pass Type ID certificate + private key (exported as .p12 or PEM)
- Team identifier + pass type identifier

**Library:** `passbook` (Python) — assembles pass JSON, images, and signs with certificate.

**Pass structure:**
- `pass.json` — layout fields, barcode config, locations, relevant date
- `manifest.json` — SHA-1 hashes of all pass files
- `signature` — PKCS#7 detached signature
- Images: `icon.png`, `icon@2x.png`, `logo.png`

**Pass layout:**
- **Header:** hackathon name
- **Primary:** participant name + team name
- **Secondary:** event date range
- **Barcode:** QR code image, format `PKBarcodeFormatQR`
- **Back fields:** registration ID, acceptance date, check-in status
- **Relevant date:** hackathon start date (puts pass on lock screen)

**Generation flow:**
```
Participant accepted → QR JWT created → QR PNG rendered (qrcode lib)
  → passbook assembles pass → .pkpass served as download
  → pass_serial_apple stored for push updates
```

**Push updates (APNs):**
When check-in status changes, push an update to Apple's APNs servers targeting the pass type. The pass JSON is re-assembled with updated fields. The participant's device receives the update and the pass shows "Checked In" with timestamp.

### Google Wallet

**Prerequisites (user provides):**
- Google Cloud project with Google Wallet API enabled
- Service account key (JSON)

**Library:** Direct Google Wallet REST API calls (no dedicated Python library needed).

**Pass class:** Generic pass with:
- Card title: hackathon name
- Header: participant name
- Subheader: team name
- Barcode: QR code (type `qrCode`)
- Text modules: registration ID, event dates, check-in status

**Generation flow:**
```
Participant accepted → Google Wallet API called to create pass object
  → "Add to Google Wallet" link returned → stored → served as redirect
  → pass_id_google (object ID) stored for push updates
```

**Push updates:**
On check-in status change, call Google Wallet API PATCH endpoint to update the pass object. The participant's device fetches the updated pass automatically.

### Credential Management

All wallet credentials are configured via environment variables:

```
APPLE_PASS_CERT_PATH=/path/to/certificate.p12
APPLE_PASS_CERT_PASSWORD=...
APPLE_PASS_TYPE_IDENTIFIER=pass.com.hackverify.checkin
APPLE_TEAM_IDENTIFIER=ABC123
GOOGLE_WALLET_CREDENTIALS_PATH=/path/to/service-account.json
GOOGLE_WALLET_ISSUER_ID=1234567890
```

Pass generation is skipped gracefully if credentials are not configured (QR codes still work without wallet passes).

### Pass Revocation

When a registration is rejected after previously being accepted:
- Apple: push an updated pass with `voided: true` in `pass.json`, which invalidates the pass on the device
- Google: call the Wallet API to expire the pass object, removing it from the user's wallet
- The QR token itself remains valid until its `exp` claim — but the scan endpoint will reject it with `registration_revoked` (410 Gone)

## QR Code Generation

**Library:** `qrcode` (Python) with Pillow for PNG output.

- Version: auto-detect based on URL length
- Error correction: M (medium, ~15%) — good scan reliability without excessive density
- Box size: 10px per module (generates ~250-400px image, crisp on smartphones)
- Border: 4 modules (standard)

QR code is generated at acceptance time and embedded into both wallet passes and displayed in the web app.

## Frontend Design

### New Routes

| Route | Who | Purpose |
|-------|-----|---------|
| `/hackathons/:id/register` | Participant | Registration form (team name, team members) |
| `/registrations` | Participant | List of my registrations with status badges |
| `/registrations/:id` | Participant | Registration detail: status, QR code, wallet buttons |
| `/hackathons/:id/registrations` | Organizer | Registration management table |

### New Components

- **`QRCodeDisplay`** — renders QR code via `<canvas>` or SVG. Large, scannable, white background for max contrast
- **`WalletButtons`** — "Add to Apple Wallet" (downloads .pkpass) + "Add to Google Wallet" (opens in new tab) buttons side by side
- **`RegistrationCard`** — status, team info, dates, QR code + wallet buttons when accepted
- **`RegistrationTable`** — organizer table with columns: name, email, team, status, registered date; row actions: accept, reject, check in, view detail
- **`StatusBadge`** — colored pill: yellow=pending, green=accepted, red=rejected, blue=checked_in

### UI Flow

```
Participant:
  Dashboard → Browse Hackathons → "Register" button
  → Fill registration form → Submit → "Pending" badge shown
  → (Later) Registrations page → Tap accepted registration
  → See QR code + "Add to Wallet" buttons

Organizer:
  Dashboard → Select Hackathon → "Registrations" tab
  → See table filtered by status → Approve/reject pending entries
  → Search by name/email → Open registration detail
  → "Check In" action → Status changes → Wallet passes update via push
```

### Styling

- Follow existing HackVerify dark theme
- QR code rendered on white card for maximum scan contrast
- Wallet buttons use platform-relevant colors (Apple: #000, Google: #4285F4)
- Wallet buttons should show an icon + text on each

## Files Changed / Added

### Backend

```
backend/app/models.py                          — add Registration model + RegistrationStatus enum
backend/app/schemas.py                         — add registration Pydantic schemas
backend/app/routes/registrations.py            — new: registration endpoints
backend/app/routes/checkin.py                  — new: scan endpoint
backend/app/wallet/__init__.py                 — new: wallet pass generation module
backend/app/wallet/apple.py                    — new: Apple .pkpass generation + APNs push
backend/app/wallet/google.py                   — new: Google Wallet pass generation + updates
backend/app/main.py                            — register new routers
backend/requirements.txt                       — add qrcode, pillow, passbook, cryptography
backend/tests/test_registrations.py            — new: registration route tests
backend/tests/test_checkin.py                  — new: scan endpoint tests
backend/tests/test_wallet.py                   — new: wallet pass generation tests
```

### Frontend

```
frontend/src/pages/RegisterPage.tsx            — new: registration form page
frontend/src/pages/RegistrationsPage.tsx       — new: my registrations list
frontend/src/pages/RegistrationDetailPage.tsx  — new: QR code + wallet buttons
frontend/src/pages/OrganizerRegistrationsPage.tsx — new: organizer management table
frontend/src/components/QRCodeDisplay.tsx      — new: QR code renderer
frontend/src/components/WalletButtons.tsx      — new: Apple/Google wallet buttons
frontend/src/components/StatusBadge.tsx        — new: colored status pill
frontend/src/services/api.ts                   — add registration API calls
frontend/src/App.tsx                           — add new routes
```

## Testing Strategy

- **Unit tests** for QR token generation/validation, pass assembly, registration state machine
- **Route tests** for RLS enforcement (participant can't see others' data, organizer scoped to own hackathons)
- **Wallet tests** for pass generation (mock certificates, verify ZIP structure for .pkpass, verify JWT payload for Google Wallet)
- **Integration tests** for full flow: register → accept → check in

## Deferred Items

- Apple Developer account setup and Pass Type ID certificate acquisition (user must do this)
- Google Cloud Wallet API enablement (user must do this)
- Risk score display in organizer registration view (can be added later)
- Automatic acceptance (can be added later)
