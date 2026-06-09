import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal
from urllib.parse import urlencode

import httpx
from fastapi import Body, Cookie, FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PM MVP Backend", lifespan=lifespan)

AUTH_COOKIE_NAME = "pm_mvp_auth"
USER_INFO_COOKIE_NAME = "pm_user_info"
OAUTH_STATE_COOKIE_NAME = "oauth_state"
DEMO_USER_ID = "user"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "kanban.db"
OPENROUTER_API_KEY_NAME = "OPENROUTER_API_KEY"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "openai/gpt-oss-120b"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

static_dir = os.path.join(os.path.dirname(__file__), "static")


class Card(BaseModel):
    id: str
    title: str
    details: str


class Column(BaseModel):
    id: str
    title: str
    cardIds: List[str]


class BoardData(BaseModel):
    columns: List[Column]
    cards: Dict[str, Card]


INITIAL_BOARD = BoardData(
    columns=[
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    cards={
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
)


def init_db() -> None:
    DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS board_state (
            user_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def load_dotenv_from_root() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    with env_path.open() as env_file:
        for line in env_file:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and os.getenv(key) is None:
                os.environ[key] = value


def get_google_credentials() -> tuple[str, str]:
    load_dotenv_from_root()
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.",
        )
    return client_id, client_secret


def get_google_redirect_uri() -> str:
    load_dotenv_from_root()
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")


def get_openrouter_api_key() -> str:
    load_dotenv_from_root()
    api_key = os.getenv(OPENROUTER_API_KEY_NAME)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{OPENROUTER_API_KEY_NAME} is not configured.",
        )
    return api_key


def get_board_state(user_id: str = DEMO_USER_ID) -> BoardData:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT state FROM board_state WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return BoardData.model_validate_json(row[0])

    return INITIAL_BOARD


def save_board_state(board: BoardData, user_id: str = DEMO_USER_ID) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO board_state (user_id, state, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state = excluded.state,
            updated_at = excluded.updated_at
        """,
        (user_id, board.model_dump_json(), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


class AIMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    question: str
    history: List[AIMessage] = []


def call_openrouter(messages: List[dict]) -> dict:
    api_key = get_openrouter_api_key()
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            temperature=0.2,
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-OpenRouter-Title": "PM MVP App",
            },
        )
        return response.to_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenRouter request failed: {exc}",
        )


def set_auth_cookies(response: Response, user_id: str, name: str, email: str, picture: str | None) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        user_id,
        httponly=True,
        samesite="lax",
        path="/",
    )
    user_info = json.dumps({"name": name, "email": email, "picture": picture})
    response.set_cookie(
        USER_INFO_COOKIE_NAME,
        user_info,
        httponly=True,
        samesite="lax",
        path="/",
    )


def validate_auth(auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME)) -> str:
    if not auth_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return auth_cookie


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/echo")
def echo(q: str = "hello"):
    return {"echo": q}


@app.post("/api/auth/login")
def login(
    response: Response,
    credentials: dict = Body(...),
):
    username = credentials.get("username")
    password = credentials.get("password")
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        set_auth_cookies(response, DEMO_USER_ID, "Demo User", VALID_USERNAME, None)
        return {"authenticated": True}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(USER_INFO_COOKIE_NAME, path="/")
    return {"authenticated": False}


@app.get("/api/auth/me")
def me(
    auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
    user_info_cookie: str | None = Cookie(None, alias=USER_INFO_COOKIE_NAME),
):
    if not auth_cookie:
        return {"authenticated": False}
    user_info: dict = {}
    if user_info_cookie:
        try:
            user_info = json.loads(user_info_cookie)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"authenticated": True, **user_info}


@app.get("/api/auth/google")
def google_login():
    client_id, _ = get_google_credentials()
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": client_id,
        "redirect_uri": get_google_redirect_uri(),
        "scope": "openid email profile",
        "response_type": "code",
        "state": state,
        "access_type": "online",
    }
    redirect = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")
    redirect.set_cookie(OAUTH_STATE_COOKIE_NAME, state, httponly=True, max_age=600, samesite="lax", path="/")
    return redirect


@app.get("/api/auth/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(None, alias=OAUTH_STATE_COOKIE_NAME),
):
    def _redirect_error(reason: str) -> RedirectResponse:
        r = RedirectResponse(f"/?auth_error={reason}")
        r.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/")
        return r

    if error:
        return _redirect_error(error)

    if not code or not state or state != oauth_state:
        return _redirect_error("invalid_state")

    client_id, client_secret = get_google_credentials()
    redirect_uri = get_google_redirect_uri()

    token_response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    if token_response.status_code != 200:
        return _redirect_error("token_exchange_failed")

    access_token = token_response.json().get("access_token")
    if not access_token:
        return _redirect_error("no_access_token")

    userinfo_response = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if userinfo_response.status_code != 200:
        return _redirect_error("userinfo_failed")

    user_info = userinfo_response.json()
    user_id = user_info.get("id") or user_info.get("sub")
    if not user_id:
        return _redirect_error("no_user_id")

    redirect = RedirectResponse("/")
    redirect.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/")
    set_auth_cookies(
        redirect,
        user_id=str(user_id),
        name=user_info.get("name", ""),
        email=user_info.get("email", ""),
        picture=user_info.get("picture"),
    )
    return redirect


@app.get("/api/board")
def get_board(auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME)):
    user_id = validate_auth(auth_cookie)
    return get_board_state(user_id)


@app.put("/api/board")
def update_board(
    board: BoardData,
    auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
):
    user_id = validate_auth(auth_cookie)
    save_board_state(board, user_id)
    return board


@app.post("/api/ai/chat")
def ai_chat(
    request: AIChatRequest,
    auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
):
    user_id = validate_auth(auth_cookie)
    board = get_board_state(user_id)

    system_prompt = (
        "You are a project management assistant. "
        "Return JSON only with two fields: reply and board_update. "
        "Reply should be a short, direct answer to the user's question. "
        "board_update should be either null or a full Kanban board object with columns and cards. "
        "If board_update is provided, it must match the current board schema exactly. "
        "Do not include any additional outside explanation unless it is inside the reply string."
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    for message in request.history:
        messages.append({"role": message.role, "content": message.content})

    messages.append(
        {
            "role": "user",
            "content": (
                f"The current board state is:\n{board.model_dump_json()}\n"
                f"User question: {request.question}\n"
                "If you decide to update the board, return a JSON object with reply and board_update. "
                "Otherwise return reply with board_update set to null."
            ),
        }
    )

    response_json = call_openrouter(messages)
    choices = response_json.get("choices") or []
    if not choices or not isinstance(choices, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter response did not include choices.",
        )

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter response did not include valid text.",
        )

    reply = content.strip()
    board_update = None
    try:
        parsed = json.loads(reply)
        if isinstance(parsed, dict):
            reply = str(parsed.get("reply", reply))
            board_update = parsed.get("board_update")
    except json.JSONDecodeError:
        pass

    if board_update is not None:
        board = BoardData.model_validate(board_update)
        save_board_state(board, user_id)
        return {"reply": reply, "board": board}

    return {"reply": reply}


@app.get("/api/ai/test")
def ai_test():
    response_json = call_openrouter(
        [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer the user's question with a single line.",
            },
            {"role": "user", "content": "What is 2 + 2?"},
        ]
    )
    choices = response_json.get("choices") or []
    if not choices or not isinstance(choices, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter response did not include choices.",
        )
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter response did not include valid text.",
        )
    return {"result": content.strip()}


@app.get("/api/hello", response_class=HTMLResponse)
def hello():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Hello from FastAPI backend</h1>")


@app.get("/", response_class=HTMLResponse)
def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>PM MVP Backend (no static files)</h1>")


if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
