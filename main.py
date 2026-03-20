"""
Hopper Bot — FastAPI entry point.

Endpoint
--------
POST /message
    Receive a message from the offender, return the AI response.

POST /session/{session_id}/clear
    Reset a session (operator use only).

GET  /health
    Liveness check.
"""
import io
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import openai

from state import (
    append_message,
    get_history,
    mark_alerted,
    was_alerted,
    clear_session,
)
from trigger import detect_platform_switch
from persona import get_ai_response
from telegram_alert import send_operator_alert, build_redirect_reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hopper Bot",
    description="Law-enforcement undercover Roblox persona with platform-switch detection.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Request / Response models ─────────────────────────────────────────────────

class IncomingMessage(BaseModel):
    session_id: str = Field(..., description="Unique ID for this offender session.")
    platform: str = Field(
        default="Roblox",
        description="The platform on which the conversation is taking place.",
    )
    message: str = Field(..., max_length=2000, description="The offender's message text.")


class BotResponse(BaseModel):
    session_id: str
    reply: str
    platform_switch_detected: bool
    switch_platform: str | None = None


class SpeakRequest(BaseModel):
    text: str = Field(..., max_length=1000)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/message", response_model=BotResponse)
def handle_message(body: IncomingMessage) -> BotResponse:
    session_id = body.session_id
    platform = body.platform
    user_text = body.message.strip()

    if not user_text:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    logger.info("Session %s | Platform: %s | Incoming: %r", session_id, platform, user_text[:120])

    # 1. Detect platform-switch attempt (log only — no redirect while Telegram is inactive)
    detection = detect_platform_switch(user_text)

    if detection.detected:
        logger.warning(
            "Session %s | Platform-switch detected → %s (logging only)", session_id, detection.platform
        )
        if not was_alerted(session_id):
            send_operator_alert(
                session_id=session_id,
                platform=detection.platform,
                offender_message=user_text,
            )
            mark_alerted(session_id)

    # 2. All messages — forward to GPT-4.5 persona
    append_message(session_id, "user", user_text)
    history = get_history(session_id)

    try:
        reply = get_ai_response(history)
    except Exception:
        logger.exception("OpenAI call failed for session %s", session_id)
        raise HTTPException(status_code=502, detail="AI backend error. Try again.")

    append_message(session_id, "assistant", reply)
    logger.info("Session %s | Reply: %r", session_id, reply[:120])

    return BotResponse(
        session_id=session_id,
        reply=reply,
        platform_switch_detected=detection.detected,
        switch_platform=detection.platform,
    )


@app.post("/speak")
def speak(body: SpeakRequest) -> StreamingResponse:
    """Convert text to a child-like voice using OpenAI TTS and stream MP3 audio."""
    from config import OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",   # youngest / most neutral sounding OpenAI voice
            input=body.text,
            speed=1.1,      # slightly faster — kids talk quickly
        )
        audio = io.BytesIO(response.content)
        return StreamingResponse(audio, media_type="audio/mpeg")
    except Exception:
        logger.exception("TTS call failed")
        raise HTTPException(status_code=502, detail="TTS error.")


@app.post("/session/{session_id}/clear", status_code=204)
def clear(session_id: str) -> None:
    """Operator endpoint: wipe all state for a session."""
    clear_session(session_id)
    logger.info("Session %s cleared by operator.", session_id)


# ── Dev runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
