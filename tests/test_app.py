import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_event():
    data = {
        "time": "2023-12-25T10:00:00",
        "description": "Holiday",
        "cron": "0 9 * * *",
        "skipped_dates": ["2023-12-31"],
    }
    response = client.post("/events", json=data)
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == data["description"]
    assert body["cron"] == data["cron"]
    assert "2023-12-31" in body["skipped_dates"]


def test_skip_event_date():
    event = {
        "time": "2023-12-25T12:00:00",
        "description": "Lunch",
    }
    create = client.post("/events", json=event)
    event_id = create.json()["id"]
    skip_resp = client.post(f"/events/{event_id}/skip", json={"date": "2023-12-25"})
    assert skip_resp.status_code == 200
    assert "2023-12-25" in skip_resp.json()["skipped_dates"]
