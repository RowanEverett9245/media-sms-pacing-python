from src.media_campaign import MediaMessage, send_campaign


class FakeClient:
    def __init__(self):
        self.published = []
        self.sent = []

    def publish_batch(self, queue, messages):
        self.published.append((queue, messages))

    def send_batch(self, messages, request_id):
        self.sent.append((messages, request_id))
        return {"message_ids": [f"m{len(self.sent)}"]}

    def message_events(self, message_id):
        return {"message_id": message_id, "status": "delivered"}


def test_campaign_keeps_media_and_splits_the_pacing_queue():
    client = FakeClient()
    messages = [MediaMessage(f"+1555{i:07d}", "hello", "https://example.com/a.jpg") for i in range(3)]

    receipt = send_campaign(messages, batch_size=2, queue="briefings", client=client)

    assert receipt.queued == 3
    assert [len(batch[1]) for batch in client.published] == [2, 1]
    assert client.published[0][0] == "briefings"
    assert client.sent[0][0][0]["media_url"].endswith("a.jpg")
    assert receipt.statuses["m1"]["status"] == "delivered"
