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
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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


# ── Routes ────────────────────────────────────────────────────────────────────

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

    # 1. Detect platform-switch attempt
    detection = detect_platform_switch(user_text)

    if detection.detected:
        logger.warning(
            "Session %s | Platform-switch detected → %s", session_id, detection.platform
        )

        # Alert the operator once per session
        if not was_alerted(session_id):
            send_operator_alert(
                session_id=session_id,
                platform=detection.platform,
                offender_message=user_text,
            )
            mark_alerted(session_id)

        # Return the scripted redirect reply (no LLM call needed here)
        redirect_reply = build_redirect_reply(current_platform=platform)

        # Still log the exchange in history for continuity
        append_message(session_id, "user", user_text)
        append_message(session_id, "assistant", redirect_reply)

        return BotResponse(
            session_id=session_id,
            reply=redirect_reply,
            platform_switch_detected=True,
            switch_platform=detection.platform,
        )

    # 2. Normal conversation — forward to GPT-4o persona
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
        platform_switch_detected=False,
    )


@app.post("/session/{session_id}/clear", status_code=204)
def clear(session_id: str) -> None:
    """Operator endpoint: wipe all state for a session."""
    clear_session(session_id)
    logger.info("Session %s cleared by operator.", session_id)


# ── Dev runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
