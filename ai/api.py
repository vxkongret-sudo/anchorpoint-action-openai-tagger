from datetime import datetime, timedelta
from time import time

import anchorpoint as ap
import os

import requests

from common.logging import log, log_err
from common.settings import tagger_settings


def init_openai_key() -> str:
    open_api_key = tagger_settings.openai_api_key
    if not open_api_key:
        ap.UI().show_error("No API key", "Please set up an API key in the settings")
        raise ValueError("No API key set")

    return open_api_key


def init_openai_admin_key() -> str:
    openai_api_admin_key = tagger_settings.openai_api_admin_key

    return openai_api_admin_key


OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def check_usage(from_days: timedelta, to_days: timedelta = timedelta(days=0)) -> str:
    openai_api_key = init_openai_admin_key()
    if not openai_api_key:
        return "Please set up Admin API key"
    date_from = int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - from_days).timestamp())
    url = f"https://api.openai.com/v1/organization/costs?start_time={date_from}&limit=100"
    if to_days != timedelta(days=0):
        date_to = int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - to_days).timestamp())
        url += f"&end_time={date_to}"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        log(response.text)
        d = response.json()

        total = 0.0
        currency = None

        data = d["data"]
        for d in data:
            if len(d["results"]) == 0:
                continue

            for r in d["results"]:
                if "amount" in r:
                    if currency is None:
                        currency = r["amount"]["currency"]
                    total += float(r["amount"]["value"])

        if total < 0.001:
            return f"<0.001 {currency}"

        return f"{round(total, 5)} {currency}"
    except Exception as e:
        ap.UI().show_error("Error", f"Error while checking usage: {e}")
        log_err(e)
        return "-1.0"
