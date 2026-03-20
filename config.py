"""Central configuration — all secrets come from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value


OPENAI_API_KEY: str = _require("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_OPERATOR_CHAT_ID: str = _require("TELEGRAM_OPERATOR_CHAT_ID")
TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "@HopperBot")

# GPT model
GPT_MODEL: str = "gpt-4o"

# Maximum conversation turns kept in memory per session
MAX_HISTORY_TURNS: int = 40
