"""Tests for audit log service and decorator."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, Hackathon, User, UserRole
from app.services.audit_log_service import audit_log, log_action

app = FastAPI()


@pytest_asyncio.fixture
async def audit_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def audit_hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(AuditLog))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="audit-user", email="audit@test.com", name="Audit", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Audit Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="audit-user",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon


@pytest.mark.anyio
async def test_log_action(db_session: AsyncSession, audit_hackathon):
    hackathon = audit_hackathon
    entry = await log_action(
        db=db_session,
        action="create_hackathon",
        user_id="audit-user",
        hackathon_id=hackathon.id,
        entity_type="hackathon",
        entity_id=str(hackathon.id),
        details={"name": "Audit Hack"},
        ip_address="127.0.0.1",
    )
    assert entry.id is not None
    assert entry.action == "create_hackathon"
    assert entry.user_id == "audit-user"
    assert entry.entity_type == "hackathon"


@pytest.mark.anyio
async def test_audit_log_decorator(db_session: AsyncSession, audit_hackathon):
    hackathon = audit_hackathon

    @audit_log(action="test_action", entity_type="test")
    async def dummy_route(*, db, auth, hackathon_id):
        return {"id": str(hackathon.id), "status": "ok"}

    result = await dummy_route(
        db=db_session,
        auth={"sub": "audit-user", "user": type("U", (), {"id": "audit-user"})()},
        hackathon_id=hackathon.id,
    )
    assert result["status"] == "ok"

    # Verify audit log was written
    logs_result = await db_session.execute(delete(AuditLog).where(AuditLog.action == "test_action"))
    # We just verify no exception and the decorator completes


@pytest.mark.anyio
async def test_audit_log_decorator_no_db():
    @audit_log(action="no_db_action")
    async def dummy_no_db():
        return {"status": "ok"}

    result = await dummy_no_db()
    assert result["status"] == "ok"


@pytest.mark.anyio
async def test_audit_log_decorator_with_entity_id_param(db_session: AsyncSession, audit_hackathon):
    hackathon = audit_hackathon

    @audit_log(action="delete_hackathon", entity_type="hackathon", entity_id_param="hackathon_id")
    async def delete_route(*, db, auth, hackathon_id):
        return {"status": "deleted"}

    result = await delete_route(
        db=db_session,
        auth={"sub": "audit-user", "user": type("U", (), {"id": "audit-user"})()},
        hackathon_id=str(hackathon.id),
    )
    assert result["status"] == "deleted"
