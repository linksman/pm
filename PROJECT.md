# Kanban Studio

A full-stack project management application built as a Udemy course project.

## What it does

Kanban Studio is a web-based Kanban board where users can organize tasks across columns (e.g., To Do, In Progress, Done). It includes an AI chat sidebar that lets users describe changes in plain English — the AI interprets the request and updates the board automatically.

## Key features

- Login-protected Kanban board
- Drag-and-drop cards between columns
- AI assistant that can read and modify the board via chat
- Single Docker container deployment (backend serves the built frontend)

## Tech stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** FastAPI (Python), SQLite
- **AI:** OpenRouter API (GPT model) via the OpenAI SDK
- **Infra:** Docker, uv

## How it works

The FastAPI backend exposes a REST API under `/api/` and serves the statically-built Next.js frontend at `/`. When a user sends a chat message, the backend forwards the full board state plus the message to an LLM, which replies with a plain-text answer and an optional `board_update` payload that is validated and saved to the database.
