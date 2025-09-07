import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def create_app(monkeypatch):
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost/test_db"
    if "backend.app" in sys.modules:
        del sys.modules["backend.app"]
    import backend.app as app_module

    async def fake_generate_response(message: str) -> str:
        if "уточняющих" in message:
            return (
                "Вопрос: Срок? Ответ: 1 месяц\n"
                "Вопрос: Бюджет? Ответ: 1000"
            )
        return "Шаг 1\nШаг 2"

    monkeypatch.setattr(app_module, "generate_response", fake_generate_response)
    app_module.Base.metadata.drop_all(bind=app_module.engine)
    app_module.Base.metadata.create_all(bind=app_module.engine)
    return app_module.app


@pytest.fixture
def client(monkeypatch):
    app = create_app(monkeypatch)
    with TestClient(app) as client:
        yield client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_goal_flow(client):
    resp = client.post("/goals", json={"goal": "Учить тестирование"})
    assert resp.status_code == 200
    data = resp.json()
    assert "goal_id" in data
    assert len(data["clarifications"]) == 2
    assert len(data["steps"]) == 2

    goal_id = data["goal_id"]
    steps_resp = client.get(f"/goals/{goal_id}/steps")
    assert steps_resp.status_code == 200
    steps = steps_resp.json()
    assert len(steps) == 2
    first_step_id = steps[0]["id"]
    assert steps[0]["is_done"] is False

    update_resp = client.patch(
        f"/goals/{goal_id}/steps/{first_step_id}",
        json={"is_done": True},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_done"] is True
