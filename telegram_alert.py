"""
Telegram integration.

Two responsibilities:
1. Alert the human operator when a platform-switch is detected.
2. Provide a helper to send the crafted "redirect to Telegram" reply
   that the child persona delivers to the offender.
"""
import asyncio
import logging

from telegram import Bot
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_OPERATOR_CHAT_ID,
    TELEGRAM_BOT_USERNAME,
)

logger = logging.getLogger(__name__)

_bot = Bot(token=TELEGRAM_BOT_TOKEN)


# ── Operator alert ────────────────────────────────────────────────────────────

ALERT_TEMPLATE = """\
🚨 *PLATFORM-SWITCH DETECTED*

*Session ID:* `{session_id}`
*Detected platform:* {platform}

*Last offender message:*
_{offender_message}_

*Action required:* Monitor incoming Telegram contact from this session.
"""


async def _send_operator_alert(
    session_id: str,
    platform: str,
    offender_message: str,
) -> None:
    await _bot.send_message(
        chat_id=TELEGRAM_OPERATOR_CHAT_ID,
        text=ALERT_TEMPLATE.format(
            session_id=session_id,
            platform=platform,
            offender_message=offender_message[:400],   # guard against huge pastes
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


def send_operator_alert(
    session_id: str,
    platform: str,
    offender_message: str,
) -> None:
    """
    Fire-and-forget Telegram alert to the operator.
    Safe to call from synchronous code.
    """
    try:
        asyncio.get_event_loop().run_until_complete(
            _send_operator_alert(session_id, platform, offender_message)
        )
    except Exception:
        logger.exception("Failed to send operator alert to Telegram.")


# ── Child-persona redirect reply ─────────────────────────────────────────────

def build_redirect_reply(current_platform: str) -> str:
    """
    Return the scripted response the child gives when the offender
    suggests moving to another platform.

    The phrasing is deliberately naive and hesitant — consistent with
    the 'Amit' persona — while steering toward the monitored Telegram.
    """
    return (
        f"omg wait my parents like literally check my {current_platform} logs all the time lol "
        f"they get so mad if i talk to ppl they dont know 😬 "
        f"can we just talk on Telegram instead?? they dont know abt that one "
        f"my user is {TELEGRAM_BOT_USERNAME}"
    )
