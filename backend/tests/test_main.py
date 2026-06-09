import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app, DB_DIR, DB_PATH, load_dotenv_from_root


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    DB_DIR.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    yield
    if DB_PATH.exists():
        DB_PATH.unlink()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_login_sets_cookie_and_auth_me(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert response.cookies.get("pm_mvp_auth") == "true"

    auth_response = client.get("/api/auth/me")
    assert auth_response.status_code == 200
    assert auth_response.json() == {"authenticated": True}


def test_auth_me_without_cookie_returns_false(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_board_requires_auth(client):
    response = client.get("/api/board")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_get_board_after_login(client):
    login = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login.status_code == 200
    response = client.get("/api/board")
    assert response.status_code == 200
    body = response.json()
    assert "columns" in body
    assert "cards" in body


def test_update_board_persists(client):
    login = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login.status_code == 200

    response = client.get("/api/board")
    assert response.status_code == 200
    board = response.json()

    board["columns"][0]["title"] = "Backlog Updated"

    update_response = client.put(
        "/api/board",
        json=board,
    )
    assert update_response.status_code == 200
    assert update_response.json()["columns"][0]["title"] == "Backlog Updated"

    persisted_response = client.get("/api/board")
    assert persisted_response.json()["columns"][0]["title"] == "Backlog Updated"


def test_ai_chat_returns_reply_and_board_update(client):
    previous_key = os.environ.get("OPENROUTER_API_KEY")
    os.environ["OPENROUTER_API_KEY"] = "test-key"
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200

    fake_openrouter_response = {
        "choices": [
            {
                "message": {
                    "content": '{"reply": "Sure, 2+2 is 4.", "board_update": {"columns": [], "cards": {}}}'
                }
            }
        ]
    }

    class DummyCreate:
        def __call__(self, *args, **kwargs):
            return self

        def to_dict(self):
            return fake_openrouter_response

    class DummyCompletions:
        def __init__(self):
            self.create = DummyCreate()

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = DummyChat()

    try:
        with patch("backend.main.OpenAI", DummyOpenAI):
            chat_response = client.post(
                "/api/ai/chat",
                json={"question": "What is 2+2?", "history": []},
            )
    finally:
        if previous_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = previous_key

    assert chat_response.status_code == 200
    body = chat_response.json()
    assert body["reply"] == "Sure, 2+2 is 4."
    assert body["board"]["columns"] == []
    assert body["board"]["cards"] == {}


@pytest.mark.skipif(
    os.getenv("OPENROUTER_API_KEY") is None
    and not Path(__file__).resolve().parents[2].joinpath(".env").exists(),
    reason="LIVE OpenRouter API key not configured",
)
def test_openrouter_connectivity_live(client):
    load_dotenv_from_root()
    if os.getenv("OPENROUTER_API_KEY") is None:
        pytest.skip("OPENROUTER_API_KEY not configured")

    response = client.get("/api/ai/test")
    assert response.status_code == 200
    body = response.json()
    assert "result" in body
    assert body["result"].strip() != ""
