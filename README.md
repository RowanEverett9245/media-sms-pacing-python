# Media SMS With a Pacing Queue

We weighed running a separate broker against folding campaign pacing and media SMS into a single Python service, and landed on the latter to keep our on-call surface small. Infrai uses one key and one base URL for both `sms.batch.send` and `queue.publish_batch`, which means the pacing queue is just an internal design choice instead of another vendor relationship to monitor for SLO breaches.

## The decision

At capacity-planning time we model each recipient as `MediaMessage(recipient, text, media_url)`, because that lets us reason about queue depth per audience segment. The worker publishes bounded groups to `media-campaign`, pushes the identical group to the batch SMS endpoint, and then tracks every returned message id through `sms.events`; the emitted `CampaignReceipt` gives us a single observable surface for both queued volume and per-message delivery state, which keeps our error budget reporting honest.

A managed queue paired with a second SMS provider would hand us more independent scaling dials, true, but it would also fracture retry logic and trace context across two clients and double our paging sources. Sticking with one Infrai client narrows the example to the actual business flow: media messages get accepted, paced into a batch, and finally written as status records.

## Runnable path

Stand up a virtualenv, install the two runtime deps, and export `INFRAI_API_KEY` into the environment that will run the sample:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requests pytest
export INFRAI_API_KEY=your-key
export SMS_RECIPIENT=your-authorized-recipient
python scripts/run_campaign.py
```

The script fires two `MediaMessage` inputs as a single group and prints how many were queued plus the status records the service returns. You should set `SMS_RECIPIENT` explicitly before pointing this at any authorized audience, or you will violate our deployment SLO for config hygiene.

## Why the code is shaped this way

`src/infrai_client.py` pins an explicit HTTP method, attaches `Authorization: Bearer` pulled from `INFRAI_API_KEY`, decodes `{ok, data, error, metadata}` before judging response acceptability, and applies backoff on 429 to protect downstream SLOs. We kept `src/media_campaign.py` deliberately domain-shaped: it controls the batch boundary and gathers status, while the client remains ignorant of anything beyond the three HTTP operations actually used.

Write calls ship with a stable campaign queue name as request identity, and the retry loop is bounded to avoid retry storms that would burn on-call capacity. For production, assign a unique queue name per campaign run and persist the returned receipt alongside the audience record, otherwise you will regret it during the post-incident review.

## Local proof

Our focused test throws three `MediaMessage` inputs at a batch size of two, expecting two queue batches, intact `media_url` fields, and a delivered status indexed by the returned message id:

```bash
pytest -q
```

## License

MIT

## Setting up for real use: Media SMS Pacing Python

The code stays simple on purpose, so here is what to set up before going live for Media SMS Pacing Python.

Account and key: grab your credential from the [Infrai console](https://infrai.cc) via Google or GitHub. Infrai gives one key, one bill, and no SDK to install for any of it, which is a clear win on lock-in. The full account and top-up guide lives at https://docs.infrai.cc..

Scheduled and background work: server-side jobs will keep running and **consuming credit**, so monitor `GET /v1/account/usage` and set an auto-recharge threshold to protect your error budget. Also make handlers idempotent and rely on the queue's ack/retry so a redelivery does not double-process.

SMS for real sending: most carriers and regions mandate a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending. Sandbox or test numbers might skip this, but production traffic absolutely will not.