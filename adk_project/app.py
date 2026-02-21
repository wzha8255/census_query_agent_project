"""Minimal FastAPI frontend for the Census Query Agent.

Endpoints:
  GET  /              — serves frontend/index.html
  GET  /chart/{id}    — returns a PNG image stored in CHART_STORE
  POST /chat          — runs the ADK agent and returns the text response
  DELETE /session/{id} — clears a session from the session service

Run with:
  cd adk_project
  uvicorn app:app --reload --port 8080
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from census_query_agent.agent import root_agent, CHART_STORE

# ── Constants ────────────────────────────────────────────────────────────────
APP_NAME = "census_query_agent"
FRONTEND_DIR = Path(__file__).parent / "frontend"

# ── ADK plumbing ─────────────────────────────────────────────────────────────
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Census Query Agent")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the chat frontend."""
    html_path = FRONTEND_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/chart/{chart_id}")
async def get_chart(chart_id: str):
    """Return a PNG chart stored by create_chart."""
    png_bytes = CHART_STORE.get(chart_id)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="Chart not found")
    return Response(content=png_bytes, media_type="image/png")


@app.post("/chat")
async def chat(request: Request):
    """Run the agent and return its final text response.

    Request body (JSON):
      {
        "message":    "<user text>",
        "session_id": "<stable session id — reuse across turns for memory>"
      }

    Response (JSON):
      { "response": "<agent markdown text>" }
    """
    body = await request.json()
    user_message: str = body.get("message", "").strip()
    session_id: str = body.get("session_id", "default")
    user_id: str = "user"

    if not user_message:
        raise HTTPException(status_code=400, detail="'message' field is required")

    # Ensure the session exists (no-op if already created)
    existing = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    new_message = Content(role="user", parts=[Part(text=user_message)])

    response_parts: list[str] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    return JSONResponse({"response": "".join(response_parts)})


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Delete a session so the next message starts a fresh conversation."""
    await session_service.delete_session(
        app_name=APP_NAME, user_id="user", session_id=session_id
    )
    return JSONResponse({"status": "deleted", "session_id": session_id})
