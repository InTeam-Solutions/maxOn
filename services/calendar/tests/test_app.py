import re
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models
from app.config import Settings, get_settings
from app.db import get_session
from app.main import create_app


USER_ID = 1111111111


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with session_factory() as session:
            yield session

    test_settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="http://testserver",
    )

    def override_settings():
        return test_settings

    app = create_app(override_settings=test_settings, skip_db_init=True)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = override_settings

    try:
        async with AsyncClient(app=app, base_url="http://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def create_calendar(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/calendars",
        json={"name": "Team", "user_id": USER_ID},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_calendar_returns_public_link(client: AsyncClient):
    payload = await create_calendar(client)
    assert payload["id"]
    assert payload["user_id"] == USER_ID
    assert payload["public_ics_url"].endswith(".ics")


@pytest.mark.asyncio
async def test_get_calendar_by_user(client: AsyncClient):
    first = await create_calendar(client)
    response = await client.get(f"/api/calendars/users/{USER_ID}/calendar")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == first["id"]
    assert payload["public_ics_url"] == first["public_ics_url"]


@pytest.mark.asyncio
async def test_ensure_calendar_returns_existing(client: AsyncClient):
    first = await create_calendar(client)
    response = await client.post(f"/api/calendars/users/{USER_ID}/calendar", json={"name": "Alt"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == first["id"]
    assert payload["name"] == first["name"]


@pytest.mark.asyncio
async def test_create_event_flow(client: AsyncClient):
    calendar = await create_calendar(client)
    calendar_id = calendar["id"]

    start = datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc)
    event_payload = {
        "title": "Planning",
        "brief_description": "Quarterly planning",
        "start_datetime": start.isoformat().replace("+00:00", "Z"),
        "duration_minutes": 60,
    }

    response = await client.post(f"/api/calendars/{calendar_id}/events", json=event_payload)
    assert response.status_code == 201
    event_data = response.json()
    assert event_data["title"] == "Planning"
    assert event_data["end_datetime"]

    list_response = await client.get(f"/api/calendars/{calendar_id}/events")
    assert list_response.status_code == 200
    events = list_response.json()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_ics_feed_contains_event(client: AsyncClient):
    calendar = await create_calendar(client)
    calendar_id = calendar["id"]
    start = datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc)
    await client.post(
        f"/api/calendars/{calendar_id}/events",
        json={
            "title": "Demo",
            "brief_description": "Sprint demo",
            "start_datetime": start.isoformat().replace("+00:00", "Z"),
            "duration_minutes": 30,
        },
    )

    match = re.search(r"/calendar/(.+)\.ics", calendar["public_ics_url"])
    assert match is not None
    token = match.group(1)

    response = await client.get(f"/calendar/{token}.ics")
    assert response.status_code == 200
    body = response.text
    assert "SUMMARY:Demo" in body
    assert "STATUS:CONFIRMED" in body
