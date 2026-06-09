import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import Body, Cookie, FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="PM MVP Backend")

AUTH_COOKIE_NAME = "pm_mvp_auth"
AUTH_COOKIE_VALUE = "true"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
USER_ID = "user"

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "kanban.db"

# Serve static files (simple hello/demo) if present
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


def get_board_state(user_id: str = USER_ID) -> BoardData:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT state FROM board_state WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return BoardData.parse_raw(row[0])

    return INITIAL_BOARD


def save_board_state(board: BoardData, user_id: str = USER_ID) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO board_state (user_id, state, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state = excluded.state,
            updated_at = excluded.updated_at
        """,
        (user_id, board.json(), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


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
        response.set_cookie(
            AUTH_COOKIE_NAME,
            AUTH_COOKIE_VALUE,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return {"authenticated": True}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return {"authenticated": False}


def validate_auth(auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME)):
    if auth_cookie != AUTH_COOKIE_VALUE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )


@app.get("/api/auth/me")
def me(auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME)):
    return {"authenticated": auth_cookie == AUTH_COOKIE_VALUE}


@app.get("/api/board")
def get_board(auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME)):
    validate_auth(auth_cookie)
    return get_board_state()


@app.put("/api/board")
def update_board(
    board: BoardData,
    auth_cookie: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
):
    validate_auth(auth_cookie)
    save_board_state(board)
    return board


@app.get("/api/hello", response_class=HTMLResponse)
def hello():
    # Serve index.html content for API check or fallback message
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Hello from FastAPI backend</h1>")


@app.get("/", response_class=HTMLResponse)
def root():
    # Serve the static index at root if present
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>PM MVP Backend (no static files)</h1>")


# Mount static files at root (after API routes) so asset paths like /_next/* resolve correctly
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
