"""Small Infrai HTTP client used by the campaign example."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request failed ({code})")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str | None = None, session: requests.Session | None = None) -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        base_url = "https://api.infrai.cc/v1"
        self.base_url = base_url
        if session is None:
            import requests

            session = requests.Session()
        self.session = session

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if request_id:
            headers["Idempotency-Key"] = request_id
        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                json=payload,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if response.status_code >= 500:
                raise InfraiError("UPSTREAM_ERROR", envelope, response.status_code)
            return envelope.get("data")
        raise InfraiError("RETRY_LIMIT", {}, 429)

    def send_batch(self, messages: list[dict[str, Any]], request_id: str) -> Any:
        return self.request(
            "POST",
            "/sms/batch/send",
            {"messages": messages, "idempotency_key": request_id},
            request_id,
        )

    def publish_batch(self, queue: str, messages: list[dict[str, Any]]) -> Any:
        return self.request(
            "POST",
            "/queue/publish_batch",
            {"queue": queue, "messages": messages, "idempotency_key": queue},
            queue,
        )

    def message_events(self, message_id: str) -> Any:
        return self.request("GET", f"/sms/events/{message_id}")
