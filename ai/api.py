import re

import anchorpoint as ap

from common.logging import log, log_err
from common.settings import tagger_settings


def init_anthropic_key() -> str:
    api_key = tagger_settings.anthropic_api_key
    if not api_key:
        ap.UI().show_error("No API key", "Please set up an Anthropic API key in the settings")
        raise ValueError("No API key set")

    return api_key


def extract_json(text: str) -> str:
    """Strip markdown code blocks if Claude wraps JSON in them."""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
