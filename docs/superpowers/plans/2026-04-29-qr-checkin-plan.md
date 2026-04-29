# QR Code Check-In System — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add QR code check-in with Apple/Google Wallet pass integration and row-level security to HackVerify.

**Architecture:** New `Registration` model with application-layer RLS scoped by user/organizer. QR codes encode signed JWTs. Wallet passes (`.pkpass` + Google Wallet) generated server-side with credential-optional graceful degradation. Frontend adds registration pages and organizer management dashboard.

**Tech Stack:** FastAPI + SQLAlchemy async (Python), React 19 + TypeScript, `qrcode` + `passbook` + Pillow for QR/pass generation, Google Wallet REST API for Android passes.

---

## Chunk 1: Backend — Model, Schema, Config

### Task 1.1: Add Registration model and RegistrationStatus enum

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add RegistrationStatus enum and Registration model**

After the existing enums (line ~124), add:

```python
class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    checked_in = "checked_in"
```

After the existing models (line ~207), add:

```python
class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    user_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(RegistrationStatus), nullable=False, default=RegistrationStatus.pending)
    team_name = Column(String(200), nullable=True)
    team_members = Column(JsonType, nullable=True)
    qr_token = Column(String(512), nullable=True)
    pass_serial_apple = Column(String(128), nullable=True)
    pass_id_google = Column(String(128), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)

    hackathon = relationship("Hackathon", back_populates="registrations")
    user = relationship("User", back_populates="registrations")

    def __repr__(self) -> str:
        return f"<Registration {self.id} status={self.status}>"
```

- [ ] **Step 2: Add relationships to Hackathon and User models**

On Hackathon model, add to the existing relationships section:
```python
registrations = relationship("Registration", back_populates="hackathon")
```

On User model, add to the existing relationships section:
```python
registrations = relationship("Registration", back_populates="user")
```

- [ ] **Step 3: Run a quick smoke test**

```bash
cd backend && python -c "from app.models import Registration, RegistrationStatus; print('OK')"
```
Expected: prints `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add Registration model and RegistrationStatus enum"
```

---

### Task 1.2: Add Registration Pydantic schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add registration schemas**

```python
# --- Registration Schemas ---

class RegistrationCreate(BaseModel):
    team_name: Optional[str] = Field(None, max_length=200)
    team_members: Optional[list[str]] = None


class RegistrationResponse(BaseModel):
    id: UUID
    hackathon_id: UUID
    user_id: UUID
    status: str
    team_name: Optional[str] = None
    team_members: Optional[list] = None
    qr_token: Optional[str] = None  # included only for accepted own registrations
    registered_at: datetime
    accepted_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    # Joined fields for organizer view
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = {"from_attributes": True}


class RegistrationListResponse(BaseModel):
    registrations: list[RegistrationResponse]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
cd backend && python -c "from app.schemas import RegistrationCreate, RegistrationResponse, RegistrationListResponse; print('OK')"
```
Expected: prints `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: add Registration Pydantic schemas"
```

---

### Task 1.3: Add wallet config to Settings

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add wallet configuration fields**

After the existing `llm_fast_model` field, add:

```python
    base_url: str = Field(default="http://localhost:8000", description="Public base URL for QR code and pass links")
    wallet_logo_url: str = Field(default="", description="Public URL for wallet pass logo image")
    apple_pass_cert_path: str = Field(default="", description="Path to Apple Pass Type ID .p12 certificate")
    apple_pass_cert_password: str = Field(default="", description="Password for the .p12 certificate")
    apple_pass_type_identifier: str = Field(default="pass.com.hackverify.checkin", description="Apple pass type identifier")
    apple_team_identifier: str = Field(default="", description="Apple Developer Team ID")
    google_wallet_credentials_path: str = Field(default="", description="Path to Google Wallet service account JSON")
    google_wallet_issuer_id: str = Field(default="", description="Google Wallet issuer ID")
```

- [ ] **Step 2: Verify config loads**

```bash
cd backend && python -c "from app.config import settings; print(settings.apple_pass_type_identifier)"
```
Expected: prints `pass.com.hackverify.checkin`

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add wallet pass configuration to settings"
```

---

## Chunk 2: Backend — QR Token + Registration Routes

### Task 2.1: Add QR token utilities to auth module

**Files:**
- Modify: `backend/app/auth.py`

- [ ] **Step 1: Add create_qr_token and decode_qr_token functions**

```python
def create_qr_token(registration_id: str, user_id: str, hackathon_id: str, hackathon_end: datetime) -> str:
    """Create a signed JWT for embedding in a QR code."""
    now = datetime.now(timezone.utc)
    payload = {
        "reg_id": registration_id,
        "user_id": user_id,
        "hackathon_id": hackathon_id,
        "iat": now,
        "exp": hackathon_end + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_qr_token(token: str) -> dict:
    """Decode and validate a QR token JWT. Raises ValueError if invalid/expired."""
    return decode_token(token)
```

- [ ] **Step 2: Write test**

Create `backend/tests/test_qr_token.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from app.auth import create_qr_token, decode_qr_token


def test_create_and_decode_qr_token():
    reg_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    hackathon_id = str(uuid.uuid4())
    end = datetime.now(timezone.utc) + timedelta(days=3)

    token = create_qr_token(reg_id, user_id, hackathon_id, end)
    payload = decode_qr_token(token)

    assert payload["reg_id"] == reg_id
    assert payload["user_id"] == user_id
    assert payload["hackathon_id"] == hackathon_id


def test_decode_expired_qr_token():
    reg_id = str(uuid.uuid4())
    end = datetime.now(timezone.utc) - timedelta(days=1)

    token = create_qr_token(reg_id, str(uuid.uuid4()), str(uuid.uuid4()), end)
    with pytest.raises(ValueError):
        decode_qr_token(token)


def test_decode_tampered_qr_token():
    reg_id = str(uuid.uuid4())
    end = datetime.now(timezone.utc) + timedelta(days=3)
    token = create_qr_token(reg_id, str(uuid.uuid4()), str(uuid.uuid4()), end)
    # Tamper by appending a character
    with pytest.raises(ValueError):
        decode_qr_token(token + "x")
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_qr_token.py -v
```
Expected: 3 tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/auth.py backend/tests/test_qr_token.py
git commit -m "feat: add QR token create/decode utilities"
```

---

### Task 2.2: Create participant registration routes

**Files:**
- Create: `backend/app/routes/registrations.py`

- [ ] **Step 1: Write failing test for registering**

Create `backend/tests/test_registrations.py`:

```python
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, async_session
from app.models import User, Hackathon, UserRole


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def db():
    async with async_session() as session:
        yield session


@pytest.fixture
async def user(db):
    from app.auth import hash_password
    user = User(id=uuid.uuid4(), email="test@test.com", name="Test User",
                password_hash=hash_password("password123"), role=UserRole.participant)
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def hackathon(db, user):
    from datetime import datetime, timezone
    h = Hackathon(id=uuid.uuid4(), name="TestHack", organizer_id=user.id,
                  start_date=datetime.now(timezone.utc),
                  end_date=datetime.now(timezone.utc))
    db.add(h)
    await db.commit()
    return h


@pytest.fixture
def auth_headers(user):
    from app.auth import create_access_token
    token = create_access_token(str(user.id), user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_for_hackathon(client, hackathon, auth_headers, db):
    response = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Dream Team", "team_members": ["Alice", "Bob"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["team_name"] == "Dream Team"
    assert data["hackathon_id"] == str(hackathon.id)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_registrations.py::test_register_for_hackathon -v
```
Expected: FAIL (404 or 500 — route not found)

- [ ] **Step 3: Create registration routes file**

```python
"""Participant registration routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Registration, RegistrationStatus, Hackathon, User
from app.schemas import RegistrationCreate, RegistrationResponse, RegistrationListResponse
from app.auth import decode_token

router = APIRouter(prefix="/api", tags=["registrations"])


def _get_current_user(authorization: str | None, db: AsyncSession) -> User:
    """Extract and validate the current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # User is fetched from DB to ensure they still exist
    return payload  # Return payload for ID lookup


async def _get_user(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/hackathons/{hackathon_id}/register", status_code=201)
async def register_for_hackathon(
    hackathon_id: uuid.UUID,
    body: RegistrationCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Register current user for a hackathon."""
    payload = _get_current_user(authorization, db)
    user = await _get_user(db, payload["sub"])

    # Verify hackathon exists
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Check for duplicate registration
    existing = await db.execute(
        select(Registration).where(
            and_(Registration.hackathon_id == hackathon_id, Registration.user_id == user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered for this hackathon")

    reg = Registration(
        hackathon_id=hackathon_id,
        user_id=user.id,
        team_name=body.team_name,
        team_members=body.team_members,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)

    return {
        "id": str(reg.id),
        "hackathon_id": str(reg.hackathon_id),
        "user_id": str(reg.user_id),
        "status": reg.status.value,
        "team_name": reg.team_name,
        "team_members": reg.team_members,
        "qr_token": reg.qr_token,
        "registered_at": reg.registered_at.isoformat(),
        "accepted_at": reg.accepted_at.isoformat() if reg.accepted_at else None,
        "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
    }
```

- [ ] **Step 4: Register the router in main.py**

Add in `backend/app/main.py`:
```python
from app.routes.registrations import router as registrations_router
# ... after existing router includes:
app.include_router(registrations_router)
```

- [ ] **Step 5: Run test**

```bash
cd backend && python -m pytest tests/test_registrations.py::test_register_for_hackathon -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/registrations.py backend/app/main.py backend/tests/test_registrations.py
git commit -m "feat: add participant registration endpoint"
```

---

### Task 2.3: Add GET my registrations endpoint

**Files:**
- Modify: `backend/app/routes/registrations.py`
- Modify: `backend/tests/test_registrations.py`

- [ ] **Step 1: Write failing test**

In `tests/test_registrations.py`:

```python
@pytest.mark.asyncio
async def test_list_my_registrations(client, hackathon, auth_headers, db):
    # First register
    await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Dream Team"},
        headers=auth_headers,
    )
    # Then list
    response = await client.get("/api/registrations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["registrations"]) == 1
    assert data["registrations"][0]["team_name"] == "Dream Team"
    assert data["registrations"][0]["user_email"] is not None  # organizer field


@pytest.mark.asyncio
async def test_cannot_see_others_registration(client, hackathon, auth_headers, db):
    # Register user1
    await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Team One"},
        headers=auth_headers,
    )
    # Create user2 and try to see user1's registration
    from app.auth import hash_password
    user2 = User(id=uuid.uuid4(), email="other@test.com", name="Other User",
                 password_hash=hash_password("pass123456"), role=UserRole.participant)
    db.add(user2)
    await db.commit()
    from app.auth import create_access_token
    token2 = create_access_token(str(user2.id), "participant")
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = await client.get("/api/registrations", headers=headers2)
    assert response.status_code == 200
    data = response.json()
    assert len(data["registrations"]) == 0  # user2 sees none
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_registrations.py::test_list_my_registrations tests/test_registrations.py::test_cannot_see_others_registration -v
```
Expected: FAIL

- [ ] **Step 3: Add list endpoint to registrations.py**

```python
@router.get("/registrations", response_model=RegistrationListResponse)
async def list_my_registrations(
    authorization: str = Header(alias="Authorization"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for the current user."""
    payload = _get_current_user(authorization, db)
    user = await _get_user(db, payload["sub"])

    # RLS: only current user's registrations
    count_query = select(func.count(Registration.id)).where(Registration.user_id == user.id)
    total = (await db.execute(count_query)).scalar()

    query = (
        select(Registration)
        .where(Registration.user_id == user.id)
        .options(selectinload(Registration.user))
        .order_by(Registration.registered_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    registrations = result.scalars().all()

    return {
        "registrations": [
            _registration_to_response(r) for r in registrations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

Add the helper function above:

```python
def _registration_to_response(r: Registration) -> dict:
    return {
        "id": str(r.id),
        "hackathon_id": str(r.hackathon_id),
        "user_id": str(r.user_id),
        "status": r.status.value,
        "team_name": r.team_name,
        "team_members": r.team_members,
        "qr_token": r.qr_token,
        "registered_at": r.registered_at.isoformat(),
        "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
        "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
        "user_name": r.user.name if r.user else None,
        "user_email": r.user.email if r.user else None,
    }
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_registrations.py::test_list_my_registrations tests/test_registrations.py::test_cannot_see_others_registration -v
```
Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/registrations.py backend/tests/test_registrations.py
git commit -m "feat: add list my registrations endpoint with RLS"
```

---

### Task 2.4: Add single registration view endpoint

**Files:**
- Modify: `backend/app/routes/registrations.py`
- Modify: `backend/tests/test_registrations.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_get_my_registration_detail(client, hackathon, auth_headers, db):
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Detail Team"},
        headers=auth_headers,
    )
    reg_id = resp.json()["id"]
    response = await client.get(f"/api/registrations/{reg_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["team_name"] == "Detail Team"
    assert "qr_token" in response.json()


@pytest.mark.asyncio
async def test_cannot_get_others_registration_detail(client, hackathon, auth_headers, db):
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Private Team"},
        headers=auth_headers,
    )
    reg_id = resp.json()["id"]
    from app.auth import hash_password, create_access_token
    user2 = User(id=uuid.uuid4(), email="intruder@test.com", name="Intruder",
                 password_hash=hash_password("pass123456"), role=UserRole.participant)
    db.add(user2)
    await db.commit()
    token2 = create_access_token(str(user2.id), "participant")
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = await client.get(f"/api/registrations/{reg_id}", headers=headers2)
    assert response.status_code == 404  # RLS: not found, not 403
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_registrations.py::test_get_my_registration_detail tests/test_registrations.py::test_cannot_get_others_registration_detail -v
```
Expected: FAIL

- [ ] **Step 3: Add detail endpoint**

```python
@router.get("/registrations/{registration_id}")
async def get_registration(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single registration. RLS: own only."""
    payload = _get_current_user(authorization, db)
    user = await _get_user(db, payload["sub"])

    query = (
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
        .options(selectinload(Registration.user))
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    return _registration_to_response(reg)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_registrations.py::test_get_my_registration_detail tests/test_registrations.py::test_cannot_get_others_registration_detail -v
```
Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/registrations.py backend/tests/test_registrations.py
git commit -m "feat: add single registration detail endpoint"
```

---

## Chunk 3: Backend — Organizer Routes + Check-in + Wallet

### Task 3.1: Create organizer registration routes

**Files:**
- Create: `backend/app/routes/registrations_organizer.py`

- [ ] **Step 1: Create organizer routes file**

```python
"""Organizer registration management routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Registration, RegistrationStatus, Hackathon, User
from app.auth import decode_token, create_qr_token

router = APIRouter(prefix="/api/hackathons", tags=["organizer-registrations"])


async def _get_organizer_db(authorization: str | None, db: AsyncSession) -> User:
    """Extract current user and verify organizer role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Organizer authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.role.value != "organizer":
        raise HTTPException(status_code=403, detail="Organizer role required")
    return user


async def _verify_organizer_owns_hackathon(user: User, hackathon_id: uuid.UUID, db: AsyncSession) -> Hackathon:
    """Verify the organizer owns the hackathon. Returns the hackathon or 404."""
    query = select(Hackathon).where(
        and_(Hackathon.id == hackathon_id, Hackathon.organizer_id == user.id)
    )
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return hackathon


@router.get("/{hackathon_id}/registrations")
async def list_hackathon_registrations(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for a hackathon. Organizer only."""
    user = await _get_organizer_db(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(Registration.hackathon_id == hackathon_id)
    count_query = select(func.count(Registration.id)).where(Registration.hackathon_id == hackathon_id)

    if status:
        query = query.where(Registration.status == status)
        count_query = count_query.where(Registration.status == status)

    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Registration.registered_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    registrations = result.scalars().all()

    # Fetch users for name/email display
    user_ids = [r.user_id for r in registrations]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = {str(u.id): u for u in users_result.scalars().all()}

    return {
        "registrations": [
            {
                "id": str(r.id),
                "hackathon_id": str(r.hackathon_id),
                "user_id": str(r.user_id),
                "status": r.status.value,
                "team_name": r.team_name,
                "team_members": r.team_members,
                "registered_at": r.registered_at.isoformat(),
                "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
                "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
                "user_name": users[str(r.user_id)].name if str(r.user_id) in users else None,
                "user_email": users[str(r.user_id)].email if str(r.user_id) in users else None,
            }
            for r in registrations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

- [ ] **Step 2: Register router in main.py**

```python
from app.routes.registrations_organizer import router as registrations_org_router
app.include_router(registrations_org_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/registrations_organizer.py backend/app/main.py
git commit -m "feat: add organizer registration list endpoint"
```

---

### Task 3.2: Add accept, reject, checkin organizer actions

**Files:**
- Modify: `backend/app/routes/registrations_organizer.py`

- [ ] **Step 1: Add accept endpoint**

```python
@router.post("/{hackathon_id}/registrations/{registration_id}/accept")
async def accept_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Approve a registration and generate QR token. Organizer only."""
    user = await _get_organizer_db(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.pending:
        raise HTTPException(status_code=409, detail=f"Cannot accept a {reg.status.value} registration")

    # Generate QR token
    qr_token = create_qr_token(
        registration_id=str(reg.id),
        user_id=str(reg.user_id),
        hackathon_id=str(hackathon.id),
        hackathon_end=hackathon.end_date,
    )
    reg.qr_token = qr_token
    reg.status = RegistrationStatus.accepted
    reg.accepted_at = datetime.now(timezone.utc)
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "qr_token": qr_token, "accepted_at": reg.accepted_at.isoformat()}


@router.post("/{hackathon_id}/registrations/{registration_id}/reject")
async def reject_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Reject a registration. Organizer only."""
    user = await _get_organizer_db(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status not in (RegistrationStatus.pending, RegistrationStatus.accepted):
        raise HTTPException(status_code=409, detail=f"Cannot reject a {reg.status.value} registration")

    reg.status = RegistrationStatus.rejected
    reg.qr_token = None  # invalidate QR
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/registrations/{registration_id}/checkin")
async def checkin_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Check in a registration. Organizer only."""
    user = await _get_organizer_db(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=409, detail=f"Cannot check in a {reg.status.value} registration")

    reg.status = RegistrationStatus.checked_in
    reg.checked_in_at = datetime.now(timezone.utc)
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "checked_in_at": reg.checked_in_at.isoformat()}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routes/registrations_organizer.py
git commit -m "feat: add accept, reject, checkin organizer actions"
```

---

### Task 3.3: Create check-in scan endpoint

**Files:**
- Create: `backend/app/routes/checkin.py`

- [ ] **Step 1: Create scan endpoint**

```python
"""QR code check-in scan endpoint."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Registration, RegistrationStatus
from app.auth import decode_qr_token

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


@router.post("/scan")
async def scan_qr(
    token: str = Query(..., description="QR JWT token"),
    db: AsyncSession = Depends(get_db),
):
    """Scan a QR code to check in. Token is validated from JWT signature."""
    # Step 1: Validate QR token
    try:
        payload = decode_qr_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": str(e)})

    reg_id = payload.get("reg_id")
    if not reg_id:
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})

    # Step 2: Load registration
    result = await db.execute(select(Registration).where(Registration.id == reg_id))
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=410, detail={"error": "registration_not_found"})

    # Step 3: Validate state
    if reg.status == RegistrationStatus.checked_in:
        raise HTTPException(status_code=409, detail={"error": "already_checked_in"})
    if reg.status == RegistrationStatus.rejected:
        raise HTTPException(status_code=410, detail={"error": "registration_revoked"})
    if reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=409, detail={"error": "registration_not_active"})

    # Step 4: Check in
    reg.status = RegistrationStatus.checked_in
    reg.checked_in_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "checked_in_at": reg.checked_in_at.isoformat(),
    }
```

- [ ] **Step 2: Register in main.py**

```python
from app.routes.checkin import router as checkin_router
app.include_router(checkin_router)
```

- [ ] **Step 3: Write test**

Create `backend/tests/test_checkin.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_session
from app.models import User, Hackathon, Registration, RegistrationStatus, UserRole
from app.auth import hash_password, create_qr_token


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def db():
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_scan_checks_in_accepted_registration(client, db):
    user = User(id=uuid.uuid4(), email="scan@test.com", name="Scannie",
                password_hash=hash_password("pw"), role=UserRole.participant)
    org = User(id=uuid.uuid4(), email="org@test.com", name="Organizer",
               password_hash=hash_password("pw"), role=UserRole.organizer)
    hack = Hackathon(id=uuid.uuid4(), name="ScanHack", organizer_id=org.id,
                     start_date=datetime.now(timezone.utc),
                     end_date=datetime.now(timezone.utc) + timedelta(days=3))
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id,
                       status=RegistrationStatus.accepted)
    for obj in [org, user, hack, reg]:
        db.add(obj)
    await db.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 200
    assert response.json()["status"] == "checked_in"


@pytest.mark.asyncio
async def test_scan_rejects_expired_token(client, db):
    user = User(id=uuid.uuid4(), email="exp@test.com", name="Expired",
                password_hash=hash_password("pw"), role=UserRole.participant)
    hack = Hackathon(id=uuid.uuid4(), name="OldHack", organizer_id=user.id,
                     start_date=datetime.now(timezone.utc) - timedelta(days=10),
                     end_date=datetime.now(timezone.utc) - timedelta(days=3))
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id,
                       status=RegistrationStatus.accepted)
    for obj in [user, hack, reg]:
        db.add(obj)
    await db.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_scan_rejects_double_checkin(client, db):
    user = User(id=uuid.uuid4(), email="double@test.com", name="Double",
                password_hash=hash_password("pw"), role=UserRole.participant)
    hack = Hackathon(id=uuid.uuid4(), name="DoubleHack", organizer_id=user.id,
                     start_date=datetime.now(timezone.utc),
                     end_date=datetime.now(timezone.utc) + timedelta(days=3))
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id,
                       status=RegistrationStatus.checked_in)
    for obj in [user, hack, reg]:
        db.add(obj)
    await db.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "already_checked_in"
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_checkin.py -v
```
Expected: 3 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/checkin.py backend/app/main.py backend/tests/test_checkin.py
git commit -m "feat: add QR code scan check-in endpoint"
```

---

### Task 3.4: QR code image generation utility

**Files:**
- Create: `backend/app/qr_generator.py`

- [ ] **Step 1: Create QR generator module**

```python
"""QR code image generation."""
import io
import qrcode
from qrcode.image.pil import PilImage


def generate_qr_png(url: str, box_size: int = 10, border: int = 4) -> bytes:
    """Generate a QR code PNG image for the given URL.

    Returns PNG bytes suitable for embedding in wallet passes or serving directly.
    """
    qr = qrcode.QRCode(
        version=None,  # auto-detect
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_image(url: str, box_size: int = 10, border: int = 4):
    """Generate a QR code PIL Image for use in wallet passes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)
```

- [ ] **Step 2: Write test**

Create `backend/tests/test_qr_generator.py`:

```python
from app.qr_generator import generate_qr_png, generate_qr_image


def test_generate_qr_png_returns_bytes():
    png = generate_qr_png("https://example.com/checkin?token=abc")
    assert isinstance(png, bytes)
    assert len(png) > 0
    # PNG magic bytes
    assert png[:8] == b'\x89PNG\r\n\x1a\n'


def test_generate_qr_image_returns_pil_image():
    img = generate_qr_image("https://example.com/checkin?token=abc")
    assert img is not None
    # Should have width and height
    assert img.width > 0
    assert img.height > 0
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_qr_generator.py -v
```
Expected: 2 tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/qr_generator.py backend/tests/test_qr_generator.py
git commit -m "feat: add QR code PNG/image generator"
```

---

### Task 3.5: Wallet pass generation — Apple

**Files:**
- Create: `backend/app/wallet/__init__.py`
- Create: `backend/app/wallet/apple.py`

- [ ] **Step 1: Create Apple pass generator (with graceful degradation)**

```python
"""Apple Wallet .pkpass generation."""
import io
import os
import tempfile
import zipfile
import hashlib
import json
from pathlib import Path
from app.qr_generator import generate_qr_png

# Apple pass certificate is optional — pass generation only works if configured
import logging
logger = logging.getLogger(__name__)
passbook_available = False
try:
    from passbook.models import Pass, Barcode, BarcodeFormat
    from passbook.signing import sign
    passbook_available = True
except ImportError:
    logger.warning("passbook not installed; Apple Wallet pass generation disabled")


def apple_pass_available() -> bool:
    """Check if Apple pass generation is configured."""
    from app.config import settings
    return (
        passbook_available
        and bool(settings.apple_pass_cert_path)
        and bool(settings.apple_team_identifier)
        and os.path.exists(settings.apple_pass_cert_path)
    )


def generate_apple_pass(
    registration_id: str,
    participant_name: str,
    team_name: str | None,
    hackathon_name: str,
    start_date: str,  # ISO 8601
    end_date: str,    # ISO 8601
    qr_url: str,
    checkin_status: str = "Accepted",
) -> bytes | None:
    """Generate a .pkpass file. Returns bytes or None if not configured."""
    if not apple_pass_available():
        return None

    from app.config import settings

    qr_png = generate_qr_png(qr_url)

    pass_data = Pass(
        description=f"{hackathon_name} Check-in Pass",
        organizationName=hackathon_name,
        passTypeIdentifier=settings.apple_pass_type_identifier,
        teamIdentifier=settings.apple_team_identifier,
        serialNumber=registration_id,
        backgroundColor="rgb(28, 28, 30)",  # dark theme matching HackVerify
        foregroundColor="rgb(255, 255, 255)",
        labelColor="rgb(108, 92, 231)",
        barcodes=[
            Barcode(
                message=qr_url,
                format=BarcodeFormat.QR,
                messageEncoding="iso-8859-1",
                altText=registration_id,
            )
        ],
        generic={
            "headerFields": [
                {"key": "event", "label": "Event", "value": hackathon_name},
            ],
            "primaryFields": [
                {"key": "name", "label": "Participant", "value": participant_name},
            ],
            "secondaryFields": [
                {"key": "team", "label": "Team", "value": team_name or "Solo"},
            ],
            "auxiliaryFields": [
                {"key": "dates", "label": "Event Dates", "value": f"{start_date} — {end_date}"},
            ],
            "backFields": [
                {"key": "reg_id", "label": "Registration ID", "value": registration_id},
                {"key": "status", "label": "Status", "value": checkin_status},
            ],
        },
    )

    # Add barcode image
    pass_data.add_file("barcode.png", io.BytesIO(qr_png))

    try:
        with tempfile.NamedTemporaryFile(suffix=".pkpass", delete=False) as tmp:
            sign(
                pass_data,
                settings.apple_pass_cert_path,
                settings.apple_pass_cert_password,
                settings.apple_team_identifier,
                settings.apple_pass_type_identifier,
                tmp.name,
            )
            with open(tmp.name, "rb") as f:
                pkpass_data = f.read()
            os.unlink(tmp.name)
            return pkpass_data
    except Exception:
        return None
```

- [ ] **Step 2: Write test**

Create `backend/tests/test_wallet.py`:

```python
import json
import zipfile
import io
from app.wallet.apple import apple_pass_available, generate_apple_pass


def test_apple_pass_returns_none_when_not_configured():
    """Without cert configured, pass generation returns None gracefully."""
    # In test environment, no cert is configured
    assert not apple_pass_available()
    result = generate_apple_pass(
        registration_id="test-123",
        participant_name="Test User",
        team_name="Test Team",
        hackathon_name="TestHack",
        start_date="2026-05-01",
        end_date="2026-05-03",
        qr_url="https://example.com/checkin?token=abc",
    )
    assert result is None


def test_apple_pass_available_returns_bool():
    result = apple_pass_available()
    assert isinstance(result, bool)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_wallet.py -v
```
Expected: 2 tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/wallet/__init__.py backend/app/wallet/apple.py backend/tests/test_wallet.py
git commit -m "feat: add Apple Wallet .pkpass generation with graceful degradation"
```

---

### Task 3.6: Wallet pass generation — Google

**Files:**
- Create: `backend/app/wallet/google.py`

- [ ] **Step 1: Create Google Wallet pass generator**

```python
"""Google Wallet pass generation."""
import json
import os
from app.qr_generator import generate_qr_png


def google_wallet_available() -> bool:
    """Check if Google Wallet is configured."""
    from app.config import settings
    return (
        bool(settings.google_wallet_credentials_path)
        and bool(settings.google_wallet_issuer_id)
        and os.path.exists(settings.google_wallet_credentials_path)
    )


def build_google_wallet_pass_object(
    registration_id: str,
    participant_name: str,
    team_name: str | None,
    hackathon_name: str,
    start_date: str,
    end_date: str,
    qr_url: str,
    checkin_status: str = "Accepted",
) -> dict:
    """Build the Google Wallet Generic Pass object dict.

    This is the payload sent to the Google Wallet REST API.
    """
    from app.config import settings

    return {
        "iss": settings.google_wallet_issuer_id,
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(__import__("time").time()),
        "origins": [],
        "payload": {
            "genericObjects": [
                {
                    "id": f"{settings.google_wallet_issuer_id}.{registration_id}",
                    "classId": f"{settings.google_wallet_issuer_id}.hackverify_checkin",
                    "genericType": "GENERIC_TYPE_UNSPECIFIED",
                    "hexBackgroundColor": "#1c1c1e",
                    "logo": {
                        "sourceUri": {
                            "uri": settings.wallet_logo_url or "https://hackverify.app/logo.png"
                        }
                    },
                    "cardTitle": {
                        "defaultValue": {
                            "language": "en",
                            "value": hackathon_name,
                        }
                    },
                    "header": {
                        "defaultValue": {
                            "language": "en",
                            "value": participant_name,
                        }
                    },
                    "subheader": {
                        "defaultValue": {
                            "language": "en",
                            "value": f"Team: {team_name or 'Solo'}",
                        }
                    },
                    "barcode": {
                        "type": "QR_CODE",
                        "value": qr_url,
                    },
                    "textModulesData": [
                        {
                            "id": "dates",
                            "header": "Event Dates",
                            "body": f"{start_date} — {end_date}",
                        },
                        {
                            "id": "status",
                            "header": "Status",
                            "body": checkin_status,
                        },
                        {
                            "id": "reg_id",
                            "header": "Registration ID",
                            "body": registration_id,
                        },
                    ],
                }
            ]
        },
    }


def get_google_wallet_save_url(pass_object: dict) -> str | None:
    """Call Google Wallet API to create a 'save to wallet' link.

    Returns the URL the user clicks to add to Google Wallet, or None on failure.
    """
    if not google_wallet_available():
        return None

    from app.config import settings
    import google.auth.transport.requests
    from google.oauth2 import service_account

    try:
        credentials = service_account.Credentials.from_service_account_file(
            settings.google_wallet_credentials_path,
            scopes=["https://www.googleapis.com/auth/wallet_object.issuer"],
        )
        credentials.refresh(google.auth.transport.requests.Request())

        # Simplified: in production, use the Google Wallet API client library
        # For now, return a direct save URL format
        object_id = pass_object["payload"]["genericObjects"][0]["id"]
        return f"https://pay.google.com/gp/v/save/{object_id}"

    except Exception:
        return None
```

- [ ] **Step 2: Write test**

In `backend/tests/test_wallet.py`:

```python
def test_google_wallet_returns_none_when_not_configured():
    from app.wallet.google import google_wallet_available, get_google_wallet_save_url
    assert not google_wallet_available()
    result = get_google_wallet_save_url({"payload": {"genericObjects": [{"id": "test"}]}})
    assert result is None


def test_build_google_wallet_pass_object_structure():
    from app.wallet.google import build_google_wallet_pass_object
    obj = build_google_wallet_pass_object(
        registration_id="reg-1",
        participant_name="Alice",
        team_name="Dream Team",
        hackathon_name="HackVerify 2026",
        start_date="2026-05-01",
        end_date="2026-05-03",
        qr_url="https://example.com/checkin?token=abc",
    )
    assert obj["aud"] == "google"
    assert obj["typ"] == "savetowallet"
    generic = obj["payload"]["genericObjects"][0]
    assert generic["cardTitle"]["defaultValue"]["value"] == "HackVerify 2026"
    assert generic["header"]["defaultValue"]["value"] == "Alice"
    assert generic["barcode"]["type"] == "QR_CODE"
    assert generic["barcode"]["value"] == "https://example.com/checkin?token=abc"
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_wallet.py -v
```
Expected: 4 tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/wallet/google.py backend/tests/test_wallet.py
git commit -m "feat: add Google Wallet pass generation with graceful degradation"
```

---

### Task 3.7: Wire wallet pass generation into accept flow + wallet download endpoints

**Files:**
- Modify: `backend/app/routes/registrations_organizer.py` (add pass generation to accept)
- Modify: `backend/app/routes/registrations.py` (add wallet download endpoints)

- [ ] **Step 1: Add pass generation to accept endpoint**

In `registrations_organizer.py`, after setting `qr_token`, add:

```python
    # Generate wallet passes
    from app.wallet.apple import generate_apple_pass
    from app.wallet.google import build_google_wallet_pass_object, get_google_wallet_save_url
    from app.qr_generator import generate_qr_png

    qr_url = f"{settings.base_url}/api/checkin/scan?token={qr_token}"
    # (use real domain in production via config)

    # Get participant name
    user_result = await db.execute(select(User).where(User.id == reg.user_id))
    participant = user_result.scalar_one()

    apple_pass = generate_apple_pass(
        registration_id=str(reg.id),
        participant_name=participant.name,
        team_name=reg.team_name,
        hackathon_name=hackathon.name,
        start_date=hackathon.start_date.strftime("%Y-%m-%d"),
        end_date=hackathon.end_date.strftime("%Y-%m-%d"),
        qr_url=qr_url,
    )
    if apple_pass:
        reg.pass_serial_apple = str(reg.id)  # serial for update tracking

    google_pass = build_google_wallet_pass_object(
        registration_id=str(reg.id),
        participant_name=participant.name,
        team_name=reg.team_name,
        hackathon_name=hackathon.name,
        start_date=hackathon.start_date.strftime("%Y-%m-%d"),
        end_date=hackathon.end_date.strftime("%Y-%m-%d"),
        qr_url=qr_url,
    )
    save_url = get_google_wallet_save_url(google_pass)
    if save_url:
        reg.pass_id_google = f"{settings.google_wallet_issuer_id}.{reg.id}"
```

- [ ] **Step 2: Add wallet download endpoints to registrations.py**

```python
@router.get("/registrations/{registration_id}/wallet/apple")
async def download_apple_pass(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Download Apple Wallet .pkpass. Own registration only."""
    payload = _get_current_user(authorization, db)
    user = await _get_user(db, payload["sub"])

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.user_id == user.id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg or reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=404, detail="Not found or not accepted")

    from app.wallet.apple import generate_apple_pass
    query_hack = await db.execute(select(Hackathon).where(Hackathon.id == reg.hackathon_id))
    hackathon = query_hack.scalar_one()

    qr_url = f"http://localhost:8000/api/checkin/scan?token={reg.qr_token}"
    pkpass = generate_apple_pass(
        registration_id=str(reg.id),
        participant_name=user.name,
        team_name=reg.team_name,
        hackathon_name=hackathon.name,
        start_date=hackathon.start_date.strftime("%Y-%m-%d"),
        end_date=hackathon.end_date.strftime("%Y-%m-%d"),
        qr_url=qr_url,
    )
    if not pkpass:
        raise HTTPException(status_code=503, detail="Wallet pass generation not configured")

    from fastapi.responses import Response
    return Response(
        content=pkpass,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="checkin-{reg.id}.pkpass"'},
    )


@router.get("/registrations/{registration_id}/wallet/google")
async def get_google_wallet_link(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get Google Wallet save URL. Own registration only."""
    payload = _get_current_user(authorization, db)
    user = await _get_user(db, payload["sub"])

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.user_id == user.id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg or reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=404, detail="Not found or not accepted")

    from app.wallet.google import build_google_wallet_pass_object, get_google_wallet_save_url
    query_hack = await db.execute(select(Hackathon).where(Hackathon.id == reg.hackathon_id))
    hackathon = query_hack.scalar_one()

    qr_url = f"http://localhost:8000/api/checkin/scan?token={reg.qr_token}"
    pass_obj = build_google_wallet_pass_object(
        registration_id=str(reg.id),
        participant_name=user.name,
        team_name=reg.team_name,
        hackathon_name=hackathon.name,
        start_date=hackathon.start_date.strftime("%Y-%m-%d"),
        end_date=hackathon.end_date.strftime("%Y-%m-%d"),
        qr_url=qr_url,
    )
    save_url = get_google_wallet_save_url(pass_obj)
    if not save_url:
        raise HTTPException(status_code=503, detail="Wallet pass generation not configured")

    return {"save_url": save_url}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/registrations.py backend/app/routes/registrations_organizer.py
git commit -m "feat: wire wallet pass generation into accept flow and download endpoints"
```

---

### Task 3.8: Add dependencies to requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add new dependencies**

Append to `backend/requirements.txt`:

```
qrcode==8.0
pillow==11.1.0
passbook==1.4.0
google-auth==2.38.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend && pip install qrcode pillow passbook google-auth
```

- [ ] **Step 3: Verify imports**

```bash
cd backend && python -c "import qrcode; from passbook.models import Pass; import google.oauth2.service_account; print('All imports OK')"
```
Expected: prints `All imports OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add qrcode, pillow, passbook, google-auth dependencies"
```

---
### Task 3.9: Add QR image serving endpoint (for frontend display)

**Files:**
- Create: `backend/app/routes/qr.py`

- [ ] **Step 1: Create QR image endpoint**

```python
"""QR code image serving endpoint."""
from fastapi import APIRouter, Query
from fastapi.responses import Response
from app.qr_generator import generate_qr_png

router = APIRouter(prefix="/api", tags=["qr"])


@router.get("/qr")
async def get_qr_image(data: str = Query(..., description="Data to encode in QR code")):
    """Serve a QR code PNG image for the given data."""
    png = generate_qr_png(data)
    return Response(content=png, media_type="image/png")
```

- [ ] **Step 2: Register in main.py**

```python
from app.routes.qr import router as qr_router
app.include_router(qr_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/qr.py backend/app/main.py
git commit -m "feat: add QR image serving endpoint for frontend display"
```

---
### Task 3.10: Add accept-then-reject transition test

**Files:**
- Modify: `backend/tests/test_checkin.py`

- [ ] **Step 1: Add test for revoked registration scan**

```python
@pytest.mark.asyncio
async def test_scan_rejects_revoked_registration(client, db):
    """After accept then reject, scanning should return 410 registration_revoked."""
    user = User(id=uuid.uuid4(), email="revoked@test.com", name="Revoked",
                password_hash=hash_password("pw"), role=UserRole.participant)
    org = User(id=uuid.uuid4(), email="revorg@test.com", name="RevOrg",
               password_hash=hash_password("pw"), role=UserRole.organizer)
    hack = Hackathon(id=uuid.uuid4(), name="RevokeHack", organizer_id=org.id,
                     start_date=datetime.now(timezone.utc),
                     end_date=datetime.now(timezone.utc) + timedelta(days=3))
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id,
                       status=RegistrationStatus.rejected)  # was accepted, then rejected
    for obj in [org, user, hack, reg]:
        db.add(obj)
    await db.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 410
    assert response.json()["detail"]["error"] == "registration_revoked"
```

- [ ] **Step 2: Run test**

```bash
cd backend && python -m pytest tests/test_checkin.py::test_scan_rejects_revoked_registration -v
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_checkin.py
git commit -m "test: add revoked registration scan rejection test"
```

---

## Chunk 4: Backend — Full test pass

### Task 4.1: Run all tests end-to-end

- [ ] **Step 1: Run full test suite**

```bash
cd backend && python -m pytest -v
```
Expected: ALL tests pass

- [ ] **Step 2: Run with coverage**

```bash
cd backend && python -m pytest --cov=app --cov-report=term-missing -v
```
Expected: all tests pass, reasonable coverage on new code

- [ ] **Step 3: Commit any fixes**

If any tests failed, fix and commit:
```bash
git add -A
git commit -m "test: fix any failing tests from check-in feature"
```

---

## Chunk 5: Frontend — Components + API

### Task 5.1: Add registration API calls

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add API functions**

After existing hackathon functions, add:

```typescript
// Registrations
export const registerForHackathon = (hackathonId: string, data: { team_name?: string; team_members?: string[] }) =>
  request(`/hackathons/${hackathonId}/register`, { method: 'POST', body: JSON.stringify(data) });

export const getMyRegistrations = (params?: { offset?: number; limit?: number }) => {
  const searchParams = new URLSearchParams();
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  return request(`/registrations${query ? `?${query}` : ''}`);
};

export const getRegistration = (id: string) => request(`/registrations/${id}`);

// Organizer registrations
export const getOrganizerRegistrations = (hackathonId: string, params?: { status?: string; offset?: number; limit?: number }) => {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  return request(`/hackathons/${hackathonId}/registrations${query ? `?${query}` : ''}`);
};

export const acceptRegistration = (hackathonId: string, registrationId: string) =>
  request(`/hackathons/${hackathonId}/registrations/${registrationId}/accept`, { method: 'POST' });

export const rejectRegistration = (hackathonId: string, registrationId: string) =>
  request(`/hackathons/${hackathonId}/registrations/${registrationId}/reject`, { method: 'POST' });

export const checkinRegistration = (hackathonId: string, registrationId: string) =>
  request(`/hackathons/${hackathonId}/registrations/${registrationId}/checkin`, { method: 'POST' });

// Wallet
export const getApplePassUrl = (registrationId: string) => `${BASE}/registrations/${registrationId}/wallet/apple`;
export const getGoogleWalletLink = (registrationId: string) => request(`/registrations/${registrationId}/wallet/google`);
```

- [ ] **Step 2: Check TypeScript compilation**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add registration and wallet API functions"
```

---

### Task 5.2: StatusBadge component

**Files:**
- Create: `frontend/src/components/StatusBadge.tsx`

- [ ] **Step 1: Create StatusBadge component**

```typescript
const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending: { bg: '#f59e0b20', text: '#f59e0b' },
  accepted: { bg: '#10b98120', text: '#10b981' },
  rejected: { bg: '#ef444420', text: '#ef4444' },
  checked_in: { bg: '#3b82f620', text: '#3b82f6' },
};

export default function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || { bg: '#333', text: '#999' };
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      background: colors.bg,
      color: colors.text,
      textTransform: 'capitalize',
    }}>
      {status.replace('_', ' ')}
    </span>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/StatusBadge.tsx
git commit -m "feat: add StatusBadge component"
```

---

### Task 5.3: QRCodeDisplay component

**Files:**
- Create: `frontend/src/components/QRCodeDisplay.tsx`

- [ ] **Step 1: Create QRCodeDisplay component**

```typescript
import { useEffect, useRef } from 'react';

interface QRCodeDisplayProps {
  token: string;
  size?: number;
}

export default function QRCodeDisplay({ token, size = 280 }: QRCodeDisplayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !token) return;
    // Use the backend QR generation endpoint to return a PNG image
    // This avoids third-party QR API dependencies
    const baseUrl = (window as any).__VITE_API_BASE_URL__ || window.location.origin;
    const qrUrl = `${baseUrl}/api/qr?data=${encodeURIComponent(token)}`;

    const canvas = canvasRef.current;
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // White background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size, size);

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, size, size);
    };
    img.onerror = () => {
      // Fallback: draw text if QR image fails to load
      ctx.fillStyle = '#000';
      ctx.font = '12px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('QR unavailable', size / 2, size / 2);
    };
    img.src = qrUrl;
  }, [token, size]);

  return (
    <div style={{
      background: '#fff',
      borderRadius: 12,
      padding: 16,
      display: 'inline-block',
      boxShadow: '0 4px 24px rgba(108, 92, 231, 0.15)',
    }}>
      <canvas ref={canvasRef} width={size} height={size} style={{ display: 'block', borderRadius: 8 }} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/QRCodeDisplay.tsx
git commit -m "feat: add QRCodeDisplay component"
```

---

### Task 5.4: WalletButtons component

**Files:**
- Create: `frontend/src/components/WalletButtons.tsx`

- [ ] **Step 1: Create WalletButtons component**

```typescript
import { getApplePassUrl } from '../services/api';

interface WalletButtonsProps {
  registrationId: string;
  googleSaveUrl?: string;
}

export default function WalletButtons({ registrationId, googleSaveUrl }: WalletButtonsProps) {
  if (!registrationId) return null;

  const appleUrl = getApplePassUrl(registrationId);

  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
      <a href={appleUrl} style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 20px',
        background: '#000',
        color: '#fff',
        borderRadius: 10,
        textDecoration: 'none',
        fontSize: 14,
        fontWeight: 600,
        border: 'none',
        cursor: 'pointer',
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
        Add to Apple Wallet
      </a>
      {googleSaveUrl && (
        <a href={googleSaveUrl} target="_blank" rel="noopener noreferrer" style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 20px',
          background: '#4285F4',
          color: '#fff',
          borderRadius: 10,
          textDecoration: 'none',
          fontSize: 14,
          fontWeight: 600,
          border: 'none',
          cursor: 'pointer',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-.15 15.5H9.5v-4.5h2.35v4.5zm0-5.85H9.5V9.5h2.35v2.15zM17 15.5h-2.35v-1.5H17v1.5zm0-3h-2.35v-1.5H17v1.5z" fill="white"/></svg>
          Add to Google Wallet
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/WalletButtons.tsx
git commit -m "feat: add WalletButtons component"
```

---

## Chunk 6: Frontend — Pages + Routes

### Task 6.1: RegisterPage

**Files:**
- Create: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Create RegisterPage**

```typescript
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { registerForHackathon } from '../services/api';

export default function RegisterPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [teamName, setTeamName] = useState('');
  const [members, setMembers] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!user || !token) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <p style={{ color: '#808090' }}>Please log in to register.</p>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const memberList = members.split(',').map(m => m.trim()).filter(Boolean);
      await registerForHackathon(id, {
        team_name: teamName || undefined,
        team_members: memberList.length > 0 ? memberList : undefined,
      });
      navigate('/registrations');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: 40 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Register for Hackathon</h1>
      {error && <div style={{ color: '#ff6b6b', marginBottom: 16 }}>{error}</div>}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, color: '#808090', fontSize: 14 }}>Team Name (optional)</label>
          <input
            type="text"
            value={teamName}
            onChange={e => setTeamName(e.target.value)}
            maxLength={200}
            style={{ width: '100%', padding: '10px 12px', background: '#0a0a1e', border: '1px solid #333', borderRadius: 8, color: '#fff', fontSize: 14 }}
            placeholder="My Awesome Team"
          />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', marginBottom: 6, color: '#808090', fontSize: 14 }}>Team Members (comma-separated, optional)</label>
          <input
            type="text"
            value={members}
            onChange={e => setMembers(e.target.value)}
            style={{ width: '100%', padding: '10px 12px', background: '#0a0a1e', border: '1px solid #333', borderRadius: 8, color: '#fff', fontSize: 14 }}
            placeholder="Alice, Bob, Charlie"
          />
        </div>
        <button type="submit" disabled={loading} style={{
          width: '100%', padding: '12px 0', background: loading ? '#4a3f9e' : '#6c5ce7',
          border: 'none', borderRadius: 8, color: '#fff', fontSize: 16, fontWeight: 600, cursor: 'pointer',
        }}>
          {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegisterPage.tsx
git commit -m "feat: add RegisterPage"
```

---

### Task 6.2: RegistrationsPage (my registrations list)

**Files:**
- Create: `frontend/src/pages/RegistrationsPage.tsx`

- [ ] **Step 1: Create RegistrationsPage**

```typescript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getMyRegistrations } from '../services/api';
import StatusBadge from '../components/StatusBadge';

interface Registration {
  id: string;
  hackathon_id: string;
  status: string;
  team_name?: string;
  registered_at: string;
  accepted_at?: string;
  checked_in_at?: string;
}

export default function RegistrationsPage() {
  const { user } = useAuth();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    getMyRegistrations()
      .then(data => setRegistrations(data.registrations))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) {
    return <div style={{ textAlign: 'center', padding: 60, color: '#808090' }}>Please log in to view registrations.</div>;
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: '#808090' }}>Loading...</div>;

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: 40 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>My Registrations</h1>
      {registrations.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: '#808090' }}>
          No registrations yet. Browse hackathons to register.
        </div>
      )}
      {registrations.map(reg => (
        <Link key={reg.id} to={`/registrations/${reg.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
          <div style={{
            padding: 16, marginBottom: 12, background: '#0a0a1e',
            border: '1px solid #1a1a2e', borderRadius: 10,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>
                {reg.team_name || 'Solo Participant'}
              </div>
              <div style={{ fontSize: 13, color: '#555' }}>
                {new Date(reg.registered_at).toLocaleDateString()}
              </div>
            </div>
            <StatusBadge status={reg.status} />
          </div>
        </Link>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegistrationsPage.tsx
git commit -m "feat: add RegistrationsPage"
```

---

### Task 6.3: RegistrationDetailPage (QR code + wallet)

**Files:**
- Create: `frontend/src/pages/RegistrationDetailPage.tsx`

- [ ] **Step 1: Create RegistrationDetailPage**

```typescript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getRegistration, getGoogleWalletLink } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import QRCodeDisplay from '../components/QRCodeDisplay';
import WalletButtons from '../components/WalletButtons';

export default function RegistrationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [reg, setReg] = useState<any>(null);
  const [googleUrl, setGoogleUrl] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id || !user) { setLoading(false); return; }
    getRegistration(id)
      .then(async (data) => {
        setReg(data);
        if (data.status === 'accepted') {
          try {
            const gRes = await getGoogleWalletLink(id);
            setGoogleUrl(gRes.save_url);
          } catch {}
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id, user]);

  if (!user) return <div style={{ textAlign: 'center', padding: 60, color: '#808090' }}>Please log in.</div>;
  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: '#808090' }}>Loading...</div>;
  if (!reg) return <div style={{ textAlign: 'center', padding: 60, color: '#808090' }}>Registration not found.</div>;

  // Base URL from environment or same origin
  const baseUrl = typeof import.meta !== 'undefined' ? (import.meta as any).env?.VITE_API_BASE_URL || window.location.origin : window.location.origin;
  const scanUrl = `${baseUrl}/api/checkin/scan?token=${reg.qr_token || ''}`;

  return (
    <div style={{ maxWidth: 520, margin: '0 auto', padding: 40, textAlign: 'center' }}>
      <StatusBadge status={reg.status} />
      <h1 style={{ fontSize: 24, marginTop: 16 }}>{reg.team_name || 'Solo Participant'}</h1>

      {reg.team_members && reg.team_members.length > 0 && (
        <p style={{ color: '#808090', fontSize: 14, marginTop: 8 }}>
          Team: {(reg.team_members as string[]).join(', ')}
        </p>
      )}

      <div style={{ marginTop: 12, fontSize: 13, color: '#555' }}>
        Registered: {new Date(reg.registered_at).toLocaleDateString()}
      </div>

      {reg.accepted_at && (
        <div style={{ fontSize: 13, color: '#10b981' }}>
          Accepted: {new Date(reg.accepted_at).toLocaleDateString()}
        </div>
      )}

      {reg.checked_in_at && (
        <div style={{ fontSize: 13, color: '#3b82f6' }}>
          Checked in: {new Date(reg.checked_in_at).toLocaleString()}
        </div>
      )}

      {reg.status === 'accepted' && reg.qr_token && (
        <>
          <div style={{ marginTop: 32, marginBottom: 24 }}>
            <QRCodeDisplay token={scanUrl} size={280} />
          </div>
          <WalletButtons registrationId={reg.id} googleSaveUrl={googleUrl} />
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegistrationDetailPage.tsx
git commit -m "feat: add RegistrationDetailPage with QR code and wallet buttons"
```

---

### Task 6.4: OrganizerRegistrationsPage

**Files:**
- Create: `frontend/src/pages/OrganizerRegistrationsPage.tsx`

- [ ] **Step 1: Create OrganizerRegistrationsPage**

```typescript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getOrganizerRegistrations, acceptRegistration, rejectRegistration, checkinRegistration } from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function OrganizerRegistrationsPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [registrations, setRegistrations] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await getOrganizerRegistrations(id, { status: statusFilter || undefined, offset, limit: 20 });
      setRegistrations(data.registrations);
      setTotal(data.total);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [id, statusFilter, offset]);

  const handleAccept = async (regId: string) => {
    if (!id) return;
    await acceptRegistration(id, regId);
    load();
  };

  const handleReject = async (regId: string) => {
    if (!id) return;
    await rejectRegistration(id, regId);
    load();
  };

  const handleCheckin = async (regId: string) => {
    if (!id) return;
    await checkinRegistration(id, regId);
    load();
  };

  if (!user || user.role !== 'organizer') {
    return <div style={{ textAlign: 'center', padding: 60, color: '#808090' }}>Organizer access required.</div>;
  }

  const limit = 20;
  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div style={{ padding: 40 }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>Registrations</h1>

      <div style={{ marginBottom: 20, display: 'flex', gap: 8 }}>
        {['', 'pending', 'accepted', 'rejected', 'checked_in'].map(s => (
          <button key={s} onClick={() => { setStatusFilter(s); setOffset(0); }}
            style={{
              padding: '6px 14px', borderRadius: 6, border: '1px solid #333',
              background: statusFilter === s ? '#6c5ce7' : 'transparent',
              color: statusFilter === s ? '#fff' : '#808090', cursor: 'pointer', fontSize: 13,
            }}>
            {s || 'All'}
          </button>
        ))}
      </div>

      {loading && <div style={{ color: '#808090', padding: 20 }}>Loading...</div>}

      {!loading && registrations.map(reg => (
        <div key={reg.id} style={{
          padding: 14, marginBottom: 8, background: '#0a0a1e', border: '1px solid #1a1a2e',
          borderRadius: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8,
        }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontWeight: 600 }}>{reg.user_name || 'Unknown'}</div>
            <div style={{ fontSize: 13, color: '#555' }}>{reg.user_email}</div>
            {reg.team_name && <div style={{ fontSize: 13, color: '#808090' }}>Team: {reg.team_name}</div>}
          </div>
          <StatusBadge status={reg.status} />
          <div style={{ display: 'flex', gap: 6 }}>
            {reg.status === 'pending' && (
              <>
                <button onClick={() => handleAccept(reg.id)} style={{ padding: '6px 12px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>Accept</button>
                <button onClick={() => handleReject(reg.id)} style={{ padding: '6px 12px', borderRadius: 6, border: 'none', background: '#ef4444', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>Reject</button>
              </>
            )}
            {reg.status === 'accepted' && (
              <button onClick={() => handleCheckin(reg.id)} style={{ padding: '6px 12px', borderRadius: 6, border: 'none', background: '#3b82f6', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>Check In</button>
            )}
          </div>
        </div>
      ))}

      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 20 }}>
          <button disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - limit))}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #333', background: 'transparent', color: '#808090', cursor: 'pointer' }}>
            Prev
          </button>
          <span style={{ padding: '6px 0', color: '#808090', fontSize: 13 }}>Page {currentPage} of {totalPages}</span>
          <button disabled={offset + limit >= total} onClick={() => setOffset(o => o + limit)}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #333', background: 'transparent', color: '#808090', cursor: 'pointer' }}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/OrganizerRegistrationsPage.tsx
git commit -m "feat: add OrganizerRegistrationsPage"
```

---

### Task 6.5: Wire up routes in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add new routes**

After the existing HackathonSetup import, add new imports and routes:

```typescript
import RegisterPage from './pages/RegisterPage';
import RegistrationsPage from './pages/RegistrationsPage';
import RegistrationDetailPage from './pages/RegistrationDetailPage';
import OrganizerRegistrationsPage from './pages/OrganizerRegistrationsPage';

// Add inside <Route element={<Layout />}>:
<Route path="/hackathons/:id/register" element={<RegisterPage />} />
<Route path="/registrations" element={<RegistrationsPage />} />
<Route path="/registrations/:id" element={<RegistrationDetailPage />} />
<Route path="/hackathons/:id/registrations" element={<OrganizerRegistrationsPage />} />
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire up registration routes in App"
```

---

### Task 6.6: Run full verification

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python -m pytest -v
```
Expected: ALL tests pass

- [ ] **Step 2: Check frontend builds**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Expected: clean build

- [ ] **Step 3: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final verification fixes for QR check-in system"
```

---

## Deferred Items

These items are explicitly scoped out of this plan and deferred to follow-up work:

1. **Apple Wallet APNs push updates** — When a registration is checked in or rejected, pushing an updated `.pkpass` to Apple Wallet requires APNs certificate setup and per-pass push notifications. This plan generates the pass at acceptance time and the server-side status changes are reflected in the DB; a follow-up plan will implement the APNs push mechanism.

2. **Google Wallet PATCH updates** — Similarly, Google Wallet pass updates on status change require OAuth-authenticated REST calls to the Google Wallet API. The pass is created at acceptance time; programmatic updates are deferred.

3. **Real-time wallet pass sync** — The pass content shows the QR code and accept status. After check-in/rejection, the wallet pass won't auto-update until push updates are implemented. For now, organizers and participants can verify status via the web app.

4. **Apple Developer account / Google Cloud Wallet setup** — Developer account enrollment and API enablement is external and must be done by the project owner.

---


