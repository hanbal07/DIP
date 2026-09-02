"""Tests for authentication and authorization endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_login_me(client):
    # Register
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123", "full_name": "Test User"},
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]

    # Duplicate register
    r2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert r2.status_code == 409

    # Login
    r3 = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert r3.status_code == 200
    token = r3.json()["access_token"]
    assert token

    # Me
    r4 = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r4.status_code == 200
    assert r4.json()["id"] == user_id


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "password123"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client):
    r = await client.post(
        "/api/v1/auth/register", json={"email": "b@example.com", "password": "short"}
    )
    assert r.status_code == 422
