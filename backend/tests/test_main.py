import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from backend.main import app, DB_DIR, DB_PATH, load_dotenv_from_root, DEMO_USER_ID


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


def _demo_login(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200
    return response


def test_login_sets_cookie_and_auth_me(client):
    response = _demo_login(client)
    assert response.json() == {"authenticated": True}
    # Cookie now stores the user ID, not the literal string "true"
    assert response.cookies.get("pm_mvp_auth") == DEMO_USER_ID

    auth_response = client.get("/api/auth/me")
    assert auth_response.status_code == 200
    data = auth_response.json()
    assert data["authenticated"] is True
    assert data["name"] == "Demo User"
    assert data["email"] == "user"
    assert data["picture"] is None


def test_auth_me_without_cookie_returns_false(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_login_invalid_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "wrong", "password": "wrong"},
    )
    assert response.status_code == 401


def test_logout_clears_cookies(client):
    _demo_login(client)
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert logout.json() == {"authenticated": False}

    me_response = client.get("/api/auth/me")
    assert me_response.json() == {"authenticated": False}


def test_board_requires_auth(client):
    response = client.get("/api/board")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_get_board_after_login(client):
    _demo_login(client)
    response = client.get("/api/board")
    assert response.status_code == 200
    body = response.json()
    assert "columns" in body
    assert "cards" in body


def test_update_board_persists(client):
    _demo_login(client)

    response = client.get("/api/board")
    assert response.status_code == 200
    board = response.json()

    board["columns"][0]["title"] = "Backlog Updated"

    update_response = client.put("/api/board", json=board)
    assert update_response.status_code == 200
    assert update_response.json()["columns"][0]["title"] == "Backlog Updated"

    persisted_response = client.get("/api/board")
    assert persisted_response.json()["columns"][0]["title"] == "Backlog Updated"


def test_google_login_redirects_to_google(client):
    with patch("backend.main.get_google_credentials", return_value=("test-client-id", "test-secret")):
        with patch("backend.main.get_google_redirect_uri", return_value="http://localhost:8000/api/auth/google/callback"):
            response = client.get("/api/auth/google", follow_redirects=False)

    assert response.status_code in (302, 307)
    location = response.headers.get("location", "")
    assert "accounts.google.com" in location
    assert "client_id=test-client-id" in location
    assert "response_type=code" in location
    assert "scope=" in location


def test_google_login_missing_credentials(client):
    with patch(
        "backend.main.get_google_credentials",
        side_effect=HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not configured"),
    ):
        response = client.get("/api/auth/google", follow_redirects=False)
    assert response.status_code == 501


def test_google_callback_sets_auth_cookies(client):
    state_token = "test-state-xyz"
    client.cookies.set(OAUTH_STATE_COOKIE_NAME := "oauth_state", state_token)

    fake_token_resp = MagicMock()
    fake_token_resp.status_code = 200
    fake_token_resp.json.return_value = {"access_token": "fake-access-token"}

    fake_userinfo_resp = MagicMock()
    fake_userinfo_resp.status_code = 200
    fake_userinfo_resp.json.return_value = {
        "id": "google-user-123",
        "name": "Jane Doe",
        "email": "jane@example.com",
        "picture": "https://example.com/photo.jpg",
    }

    with patch("backend.main.get_google_credentials", return_value=("test-id", "test-secret")):
        with patch("backend.main.get_google_redirect_uri", return_value="http://localhost:8000/api/auth/google/callback"):
            with patch("httpx.post", return_value=fake_token_resp):
                with patch("httpx.get", return_value=fake_userinfo_resp):
                    response = client.get(
                        f"/api/auth/google/callback?code=fake-code&state={state_token}",
                        follow_redirects=False,
                    )

    assert response.status_code in (302, 307)
    assert response.headers.get("location") == "/"
    # Cookie is set via Set-Cookie header on the redirect response
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "pm_mvp_auth=google-user-123" in set_cookie_header


def test_google_callback_invalid_state(client):
    with patch("backend.main.get_google_credentials", return_value=("test-id", "test-secret")):
        response = client.get(
            "/api/auth/google/callback?code=fake-code&state=wrong-state",
            follow_redirects=False,
        )
    assert response.status_code in (302, 307)
    location = response.headers.get("location", "")
    assert "auth_error=invalid_state" in location


def test_google_callback_error_param(client):
    response = client.get(
        "/api/auth/google/callback?error=access_denied",
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    location = response.headers.get("location", "")
    assert "auth_error=access_denied" in location


def test_google_user_gets_own_board(client):
    state_token = "state-abc"
    client.cookies.set("oauth_state", state_token)

    fake_token_resp = MagicMock()
    fake_token_resp.status_code = 200
    fake_token_resp.json.return_value = {"access_token": "tok"}

    fake_userinfo_resp = MagicMock()
    fake_userinfo_resp.status_code = 200
    fake_userinfo_resp.json.return_value = {
        "id": "google-user-456",
        "name": "John Smith",
        "email": "john@example.com",
        "picture": None,
    }

    with patch("backend.main.get_google_credentials", return_value=("id", "secret")):
        with patch("backend.main.get_google_redirect_uri", return_value="http://localhost:8000/api/auth/google/callback"):
            with patch("httpx.post", return_value=fake_token_resp):
                with patch("httpx.get", return_value=fake_userinfo_resp):
                    client.get(
                        f"/api/auth/google/callback?code=code&state={state_token}",
                        follow_redirects=False,
                    )

    # Google user should get their own initial board
    board_response = client.get("/api/board")
    assert board_response.status_code == 200
    assert "columns" in board_response.json()

    # Me endpoint should reflect Google user info
    me_response = client.get("/api/auth/me")
    data = me_response.json()
    assert data["authenticated"] is True
    assert data["email"] == "john@example.com"
    assert data["name"] == "John Smith"


def test_ai_chat_returns_reply_and_board_update(client):
    previous_key = os.environ.get("OPENROUTER_API_KEY")
    os.environ["OPENROUTER_API_KEY"] = "test-key"
    _demo_login(client)

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
