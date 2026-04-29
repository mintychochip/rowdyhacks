import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_201(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "name": "New User",
        "password": "secure-password-123",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_409(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "dup@example.com", "name": "First", "password": "secure-password-123",
    })
    response = await client.post("/api/auth/register", json={
        "email": "dup@example.com", "name": "Second", "password": "another-password-456",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_200(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "login-test@example.com", "name": "Login Test", "password": "my-password-is-secure",
    })
    response = await client.post("/api/auth/login", json={
        "email": "login-test@example.com", "password": "my-password-is-secure",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password_401(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "wrong-pass@example.com", "name": "WP", "password": "correct-password-123",
    })
    response = await client.post("/api/auth/login", json={
        "email": "wrong-pass@example.com", "password": "wrong-password",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_200(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "me@example.com", "name": "Me User", "password": "my-password-123",
    })
    token = reg.json()["access_token"]
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["name"] == "Me User"
