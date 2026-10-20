"""
Integration and API endpoint tests using httpx AsyncClient.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage.database import init_db


@pytest.fixture
async def client():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_and_health(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["sovereign_mode"] is True

    health_resp = await client.get("/api/health")
    assert health_resp.status_code == 200


@pytest.mark.asyncio
async def test_sessions_lifecycle(client: AsyncClient) -> None:
    # 1. Create session
    create_resp = await client.post("/api/sessions", json={"title": "Refinery Unit 101 Overhaul"})
    assert create_resp.status_code == 201
    sess_data = create_resp.json()
    sess_id = sess_data["id"]
    assert sess_data["title"] == "Refinery Unit 101 Overhaul"

    # 2. List sessions
    list_resp = await client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert any(s["id"] == sess_id for s in sessions)

    # 3. Get session details
    detail_resp = await client.get(f"/api/sessions/{sess_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == sess_id
    assert "messages" in detail

    # 4. Delete session
    del_resp = await client.delete(f"/api/sessions/{sess_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_skills_listing(client: AsyncClient) -> None:
    resp = await client.get("/api/skills")
    assert resp.status_code == 200
    skills = resp.json()
    assert len(skills) >= 7
    skill_names = [s["name"] for s in skills]
    assert "inspection_report" in skill_names
    assert "pid_analysis" in skill_names
    assert "approval_note" in skill_names


@pytest.mark.asyncio
async def test_audit_and_sovereignty(client: AsyncClient) -> None:
    sov_resp = await client.get("/api/audit/sovereignty")
    assert sov_resp.status_code == 200
    sov_data = sov_resp.json()
    assert sov_data["sovereign_mode"] is True
    assert sov_data["external_calls_allowed"] == 0

    events_resp = await client.get("/api/audit/events")
    assert events_resp.status_code == 200


@pytest.mark.asyncio
async def test_chat_endpoint_string_payload(client: AsyncClient) -> None:
    # Test with raw string payload (the exact format sent by Next.js frontend)
    resp = await client.post("/api/chat", json={"message": "hi", "stream": False})
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert data["category"] == "casual"


@pytest.mark.asyncio
async def test_chat_endpoint_stream_payload(client: AsyncClient) -> None:
    # Test streaming SSE response
    resp = await client.post("/api/chat", json={"message": "hi", "stream": True})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
