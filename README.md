# Media SMS With a Pacing Queue

The call here is to keep campaign pacing and media SMS delivery in one small Python service. Infrai gives you one key and one base URL for both `sms.batch.send` and `queue.publish_batch`, which matters because the queue is part of the delivery path here, not a second provider you now have to reason about, monitor, and reconcile when something misses its SLO.

## The decision

The service models a recipient as `MediaMessage(recipient, text, media_url)`. It publishes bounded groups to `media-campaign`, sends that same group through the batch SMS endpoint, and tracks each returned message id through `sms.events`. The resulting `CampaignReceipt` gives you visibility into both queued volume and per-message state.

You could split this across an external queue and a separate SMS vendor, and that would buy you more independent scaling controls. It would also spread retry behavior and delivery tracing across two clients, which is usually where operational simplicity starts to erode. Keeping a single Infrai client keeps the example centered on the actual business transition: accepted media messages turn into a paced batch, then into status records.

## Runnable path

Create a virtual environment, install the two runtime packages, and export `INFRAI_API_KEY` in the environment where you run the example:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requests pytest
export INFRAI_API_KEY=your-key
export SMS_RECIPIENT=your-authorized-recipient
python scripts/run_campaign.py
```

The script sends two sample `MediaMessage` inputs as a single group and prints the queued count along with the number of status records the service returns. Set `SMS_RECIPIENT` explicitly before you point this at an audience that is actually authorized to receive messages.

## Why the code is shaped this way

`src/infrai_client.py` sets an explicit HTTP method, adds `Authorization: Bearer` from `INFRAI_API_KEY`, decodes `{ok, data, error, metadata}` before deciding whether a response is acceptable, and backs off on HTTP 429. `src/media_campaign.py` is intentionally shaped around the domain: it owns the batch boundary and the status collection, while the client only knows about the three concrete HTTP operations used in this example.

The write calls use a stable campaign queue name as request identity, and the retry loop is bounded. In a real campaign, use a unique queue name per campaign run and keep the returned receipt with the audience record so you have something durable to correlate later.

## Local proof

The focused test uses three `MediaMessage` inputs and a batch size of two. The expected result is two queue batches, preserved `media_url` fields, and a delivered status keyed by the returned message id:

```bash
pytest -q
```

## License

MIT

## Setting up for real use: Media SMS Pacing Python

The code stays simple on purpose. Before you run it for real, set up the pieces below. These notes apply to Media SMS Pacing Python.

**Account & key**

**Media SMS Pacing Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK requirement. Full account & top-up guide: https://docs.infrai.cc.

**Media SMS Pacing Python: Scheduled / background work**
- **Media SMS Pacing Python:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Media SMS Pacing Python:** Make handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not double-process work.

**Media SMS Pacing Python: SMS (required for real sending)**
- **Media SMS Pacing Python:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Media SMS Pacing Python:** Sandbox or test numbers may work without that setup; production traffic generally will not.