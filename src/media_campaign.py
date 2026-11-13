from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class MediaMessage:
    recipient: str
    text: str
    media_url: str

    def api_payload(self) -> dict[str, str]:
        return {"to": self.recipient, "body": self.text, "media_url": self.media_url}


@dataclass(frozen=True)
class CampaignReceipt:
    queued: int
    sent: Any
    statuses: dict[str, Any]


def send_campaign(
    messages: list[MediaMessage],
    batch_size: int = 50,
    queue: str = "media-campaign",
    client: InfraiClient | None = None,
) -> CampaignReceipt:
    """Queue work in bounded groups, send each group, then collect message events."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    api = client or InfraiClient()
    groups = [messages[i : i + batch_size] for i in range(0, len(messages), batch_size)]
    queued = sum(len(group) for group in groups)
    for group in groups:
        api.publish_batch(queue, [{"payload": item.api_payload()} for item in group])
    sent: list[Any] = []
    statuses: dict[str, Any] = {}
    for group in groups:
        result = api.send_batch([item.api_payload() for item in group], request_id=queue)
        sent.append(result)
        if isinstance(result, dict):
            for message_id in result.get("message_ids", []):
                statuses[message_id] = api.message_events(message_id)
    return CampaignReceipt(queued=queued, sent=sent, statuses=statuses)
