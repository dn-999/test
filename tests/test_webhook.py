from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from app import main, providers


def make_request(body: bytes, signature: str) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/webhook",
        "raw_path": b"/webhook",
        "query_string": b"",
        "headers": [(b"x-line-signature", signature.encode("ascii"))],
        "server": ("testserver", 80),
        "client": ("testclient", 1234),
        "root_path": "",
    }
    return Request(scope, receive)


def sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


class WebhookTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_text_is_acked_and_queued_but_sticker_is_ignored(self) -> None:
        secret = "local-test-channel-secret"
        text_event = {
            "type": "message",
            "webhookEventId": "test-text-1",
            "replyToken": "test-reply-token",
            "message": {"type": "text", "text": "hello"},
        }
        sticker_event = {
            "type": "message",
            "webhookEventId": "test-sticker-1",
            "replyToken": "unused-reply-token",
            "message": {"type": "sticker", "stickerId": "1"},
        }
        body = json.dumps({"events": [text_event, sticker_event]}).encode()
        background = BackgroundTasks()

        with patch.dict(os.environ, {"LINE_CHANNEL_SECRET": secret}), patch.object(
            main, "_claim_event", return_value=True
        ), patch.object(main, "_process_text_event"):
            response = await main.webhook(make_request(body, sign(body, secret)), background)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(background.tasks), 1)
        self.assertEqual(background.tasks[0].args[0], text_event)

    async def test_invalid_signature_is_rejected_without_queuing(self) -> None:
        body = b'{"events":[]}'
        background = BackgroundTasks()
        with patch.dict(os.environ, {"LINE_CHANNEL_SECRET": "local-test-channel-secret"}):
            with self.assertRaises(HTTPException) as raised:
                await main.webhook(make_request(body, "invalid"), background)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(len(background.tasks), 0)

    async def test_repeated_event_id_is_not_queued_twice(self) -> None:
        secret = "local-test-channel-secret"
        event = {
            "type": "message",
            "webhookEventId": "duplicate-test-id",
            "replyToken": "test-reply-token",
            "message": {"type": "text", "text": "hello"},
        }
        body = json.dumps({"events": [event]}).encode()
        background = BackgroundTasks()
        with patch.dict(os.environ, {"LINE_CHANNEL_SECRET": secret}), patch.object(
            main, "_claim_event", return_value=False
        ):
            response = await main.webhook(make_request(body, sign(body, secret)), background)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(background.tasks), 0)


class GeminiTests(unittest.TestCase):
    def test_request_contains_only_current_message(self) -> None:
        api_result = {"candidates": [{"content": {"parts": [{"text": "reply"}]}}]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-local-test-key"}), patch.object(
            providers, "_post_json", return_value=api_result
        ) as post_json:
            result = providers._generate_reply("只測試此則訊息")
        self.assertEqual(result, "reply")
        request_payload = post_json.call_args.args[2]
        self.assertEqual(
            request_payload["contents"],
            [{"role": "user", "parts": [{"text": "只測試此則訊息"}]}],
        )


if __name__ == "__main__":
    unittest.main()
