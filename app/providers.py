"""Minimal Gemini and LINE HTTP clients with non-sensitive error reporting."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class ProviderError(Exception):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            raw = response.read()
    except HTTPError as exc:
        # Never include provider response bodies, URLs, or headers in exceptions/logs.
        raise ProviderError(f"http_{exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("network_error") from None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProviderError("invalid_json") from None
    if not isinstance(data, dict):
        raise ProviderError("invalid_response")
    return data


def _generate_reply(text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    if not api_key:
        raise ProviderError("gemini_not_configured")

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "你是一位友善、自然、簡潔的聊天朋友。請用使用者本則訊息所用的語言回答。"
                        "每次請把這則訊息當成第一次互動，不要假設或提及任何先前對話。"
                    )
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {"maxOutputTokens": 256, "temperature": 0.7},
    }
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='')}:generateContent"
    )
    data = _post_json(endpoint, {"x-goog-api-key": api_key}, payload)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        answer = "".join(part["text"] for part in parts if isinstance(part.get("text"), str)).strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        raise ProviderError("empty_model_reply") from None
    if not answer:
        raise ProviderError("empty_model_reply")
    return answer[:4800]


def reply_to_line(text: str, reply_token: str) -> None:
    access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not access_token:
        raise ProviderError("line_not_configured")
    answer = _generate_reply(text)
    _post_json(
        "https://api.line.me/v2/bot/message/reply",
        {"Authorization": f"Bearer {access_token}"},
        {"replyToken": reply_token, "messages": [{"type": "text", "text": answer}]},
    )
