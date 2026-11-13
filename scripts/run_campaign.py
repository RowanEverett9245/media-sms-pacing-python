import os

from src.media_campaign import MediaMessage, send_campaign


def main() -> None:
    recipient = os.environ["SMS_RECIPIENT"]
    audience = [
        MediaMessage(recipient, "Your morning briefing", "https://example.com/briefing.jpg"),
        MediaMessage(recipient, "Your morning briefing", "https://example.com/briefing.jpg"),
    ]
    receipt = send_campaign(audience, batch_size=2)
    print(f"queued={receipt.queued} status_count={len(receipt.statuses)}")


if __name__ == "__main__":
    main()
