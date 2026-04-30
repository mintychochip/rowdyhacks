"""Tests for OAuth state store, name fallbacks, and routes."""
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select

from app.models import User, OAuthAccount, UserRole
from app.auth import hash_password, create_access_token
from app.oauth import create_state, consume_state, build_name_fallback


# ── State Store ──────────────────────────────────────────────

def test_create_and_consume_state():
    state = create_state("google")
    payload = consume_state(state)
    assert payload == {"provider": "google", "link_user_id": None}


def test_create_and_consume_state_with_link_user():
    state = create_state("github", link_user_id="user-123")
    payload = consume_state(state)
    assert payload == {"provider": "github", "link_user_id": "user-123"}


def test_consume_nonexistent_state():
    assert consume_state("nonexistent") is None


def test_consume_state_twice_fails():
    state = create_state("discord")
    assert consume_state(state) is not None
    assert consume_state(state) is None


# ── Name Fallbacks ──────────────────────────────────────────

def test_build_name_fallback_uses_name():
    assert build_name_fallback("google", {"name": "Alice"}) == "Alice"


def test_build_name_fallback_uses_email_local_part():
    assert build_name_fallback("google", {"name": "", "email": "alice@example.com"}) == "alice"


def test_build_name_fallback_returns_hacker():
    assert build_name_fallback("google", {"name": "", "email": ""}) == "Hacker"


# ── Route Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unknown_provider_returns_400(client):
    response = await client.get(
        "/api/auth/oauth/unknown_provider/authorize", follow_redirects=False
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_callback_with_expired_state(client):
    response = await client.get(
        "/api/auth/oauth/google/callback?code=test&state=nonexistent",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=invalid_state" in response.headers["location"]


@pytest.mark.asyncio
async def test_list_linked_providers(db_session, client):
    user = User(
        id=uuid.uuid4(), email="linktest@test.com", name="LinkTest",
        password_hash=hash_password("pw"), role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.get(
        "/api/auth/me/oauth",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"linked": [], "has_password": True}


@pytest.mark.asyncio
async def test_unlink_last_auth_method_fails(db_session, client):
    user = User(
        id=uuid.uuid4(), email="oauthonly@test.com", name="OAuthUser",
        password_hash=None, role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(), provider="google", provider_user_id="g123",
        provider_email="oauthonly@test.com", user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.delete(
        "/api/auth/me/oauth/google",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "only login method" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unlink_succeeds_when_has_password(db_session, client):
    user = User(
        id=uuid.uuid4(), email="both@test.com", name="BothAuth",
        password_hash=hash_password("pw"), role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(), provider="google", provider_user_id="g456",
        provider_email="both@test.com", user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.delete(
        "/api/auth/me/oauth/google",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.user_id == user.id)
    )
    assert len(result.scalars().all()) == 0


# ── Callback integration tests (httpx mocked) ──────────────

@pytest.mark.asyncio
async def test_callback_creates_new_user(client, db_session):
    """Full callback flow: new user via Google OAuth."""
    state = create_state("google")
    token_response = {"access_token": "tok123", "token_type": "bearer"}

    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value=token_response),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "g-user-999",
                    "email": "newuser@gmail.com",
                    "name": "New User",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    location = response.headers["location"]
    assert "token=" in location and "error=" not in location

    # Verify user and OAuthAccount were created
    result = await db_session.execute(
        select(User).where(User.email == "newuser@gmail.com")
    )
    user = result.scalar_one()
    assert user.name == "New User"
    assert user.password_hash is None

    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.provider_user_id == "g-user-999")
    )
    oa = result.scalar_one()
    assert oa.provider == "google"
    assert oa.user_id == user.id


@pytest.mark.asyncio
async def test_callback_logs_in_existing_oauth_account(client, db_session):
    """Callback with existing OAuthAccount returns JWT for that user."""
    user = User(
        id=uuid.uuid4(),
        email="existing@test.com",
        name="Existing",
        password_hash=None,
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(),
        provider="google",
        provider_user_id="g-existing",
        provider_email="existing@test.com",
        user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    state = create_state("google")
    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value={"access_token": "tok"}),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "g-existing",
                    "email": "existing@test.com",
                    "name": "Existing",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "token=" in response.headers["location"]
    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.user_id == user.id)
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_callback_auto_links_by_email(client, db_session):
    """Callback auto-links when OAuth email matches existing user email."""
    user = User(
        id=uuid.uuid4(),
        email="alice@test.com",
        name="Alice",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    state = create_state("google")
    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value={"access_token": "tok"}),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "g-new-link",
                    "email": "alice@test.com",
                    "name": "Alice",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "token=" in response.headers["location"]
    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.provider_user_id == "g-new-link")
    )
    oa = result.scalar_one()
    assert oa.user_id == user.id


@pytest.mark.asyncio
async def test_callback_apple_no_name_fallback(client, db_session):
    """Apple callback where name is absent (subsequent auth)."""
    state = create_state("apple")
    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value={"access_token": "tok", "id_token": "x"}),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "apple-sub-1",
                    "email": "justin@example.com",
                    "name": "",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/apple/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "token=" in response.headers["location"]
    result = await db_session.execute(
        select(User).where(User.email == "justin@example.com")
    )
    user = result.scalar_one()
    assert user.name == "justin"
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_callback_provider_error_redirects_with_error(client):
    """When exchange_code raises, redirect with provider_error."""
    state = create_state("google")
    with patch(
        "app.routes.oauth.exchange_code",
        new=AsyncMock(side_effect=ValueError("fail")),
    ):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert "error=provider_error" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_no_provider_user_id(client):
    """When provider returns no provider_user_id, redirect with provider_error."""
    state = create_state("github")
    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value={"access_token": "tok"}),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "",
                    "email": "",
                    "name": "",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/github/callback?code=test&state={state}",
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert "error=provider_error" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_no_email_redirects_with_error(client):
    """When provider returns a user ID but no email, redirect with no_email."""
    state = create_state("github")
    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value={"access_token": "tok"}),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "gh-valid-id",
                    "email": "",
                    "name": "NoEmail",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/github/callback?code=test&state={state}",
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert "error=no_email" in response.headers["location"]


@pytest.mark.asyncio
async def test_link_endpoint_without_client_id_returns_503(client, db_session):
    """GET /me/oauth/link/{provider} returns 503 when provider not configured."""
    user = User(
        id=uuid.uuid4(),
        email="linker@test.com",
        name="Linker",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.get(
        "/api/auth/me/oauth/link/google",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_link_callback_existing_oauth_logs_in_as_original_user(
    client, db_session
):
    """When an OAuth account is already linked, the callback logs in as that user (not the link requester)."""
    user_a = User(
        id=uuid.uuid4(),
        email="a@test.com",
        name="UserA",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    db_session.add(user_a)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(),
        provider="google",
        provider_user_id="g-shared",
        provider_email="shared@test.com",
        user_id=user_a.id,
    )
    db_session.add(oa)
    await db_session.commit()

    user_b = User(
        id=uuid.uuid4(),
        email="b@test.com",
        name="UserB",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    db_session.add(user_b)
    await db_session.commit()

    state = create_state("google", link_user_id=str(user_b.id))
    with (
        patch(
            "app.routes.oauth.exchange_code",
            new=AsyncMock(return_value={"access_token": "tok"}),
        ),
        patch(
            "app.routes.oauth.fetch_user_info",
            new=AsyncMock(
                return_value={
                    "provider_user_id": "g-shared",
                    "email": "shared@test.com",
                    "name": "Shared",
                }
            ),
        ),
    ):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert "token=" in response.headers["location"]

    # Verify user_b did NOT get the OAuthAccount linked
    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.provider_user_id == "g-shared")
    )
    accounts = result.scalars().all()
    assert len(accounts) == 1
    assert accounts[0].user_id == user_a.id


@pytest.mark.asyncio
async def test_concurrent_link_unique_constraint(client, db_session):
    """The DB unique constraint prevents duplicate OAuthAccount rows."""
    user = User(
        id=uuid.uuid4(),
        email="unique@test.com",
        name="Unique",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    oa = OAuthAccount(
        id=uuid.uuid4(),
        provider="google",
        provider_user_id="g-unique",
        provider_email="unique@test.com",
        user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    duplicate = OAuthAccount(
        id=uuid.uuid4(),
        provider="google",
        provider_user_id="g-unique",
        provider_email="other@test.com",
        user_id=user.id,
    )
    db_session.add(duplicate)
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()
