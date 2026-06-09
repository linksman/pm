from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="PM MVP Backend")

# Serve static files (simple hello/demo) if present
static_dir = os.path.join(os.path.dirname(__file__), "static")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/echo")
def echo(q: str = "hello"):
    return {"echo": q}


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
