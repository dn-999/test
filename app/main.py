"""Stateless LINE text webhook for Render and local Docker Compose."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.providers import ProviderError, reply_to_line

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("line_chatbot")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
_seen_events: OrderedDict[str, float] = OrderedDict()
_seen_lock = threading.Lock()
_EVENT_TTL_SECONDS = 20 * 60
_EVENT_CACHE_LIMIT = 1000


def valid_line_signature(body: bytes, signature: str | None, channel_secret: str) -> bool:
    if not signature:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


def _claim_event(event_id: str | None) -> bool:
    """Claim an event ID for short-lived duplicate suppression; stores no message data."""
    if not event_id:
        return True
    now = time.monotonic()
    with _seen_lock:
        expired = [key for key, added in _seen_events.items() if now - added > _EVENT_TTL_SECONDS]
        for key in expired:
            _seen_events.pop(key, None)
        if event_id in _seen_events:
            return False
        _seen_events[event_id] = now
        while len(_seen_events) > _EVENT_CACHE_LIMIT:
            _seen_events.popitem(last=False)
    return True


def _process_text_event(event: dict[str, Any]) -> None:
    try:
        text = event["message"]["text"]
        reply_token = event["replyToken"]
        reply_to_line(text, reply_token)
    except ProviderError as exc:
        logger.warning("event_processing_failed category=%s", exc.category)
    except Exception as exc:  # Keep user data and provider details out of logs.
        logger.warning("event_processing_failed category=%s", type(exc).__name__)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    body = await request.body()
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    signature = request.headers.get("x-line-signature")
    if not channel_secret or not valid_line_signature(body, signature, channel_secret):
        raise HTTPException(status_code=400, detail="invalid signature")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="invalid JSON") from None
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="invalid events")

    for event in events:
        if not isinstance(event, dict):
            continue
        message = event.get("message")
        if event.get("type") != "message" or not isinstance(message, dict) or message.get("type") != "text":
            continue
        if not isinstance(message.get("text"), str) or not isinstance(event.get("replyToken"), str):
            continue
        if not _claim_event(event.get("webhookEventId")):
            continue
        background_tasks.add_task(_process_text_event, event)

    # ACK before any cloud-model or LINE Reply API calls. LINE's webhook sender
    # expects a 2xx quickly; background work still depends on the process staying up.
    return JSONResponse(status_code=200, content={"status": "accepted"})
