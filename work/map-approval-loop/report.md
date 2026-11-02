# MAP approval loop — field report

An agent asked Nitrosend to send a campaign; Safe Mode held it and
emailed the account owner a MAP (Mail Action Protocol) description.
This report documents one full hold → check → approve loop, verified
with the published `mailschema` package.

**Account:** Nitrosend account for `info@mesh-01.com` (account_id
13832), brand `mesh-01` (brand_id 14024), sender
`hello@mesh01.nitrosend.net`.

## Tooling and runtime

- Node.js v20 (WSL2), npm 10, package `mailschema@0.3.2`
  (`npm install mailschema@0.3.2`, package exports ESM
  `dist/index.js` — under Node 20 the bare import throws
  `ERR_PACKAGE_PATH_NOT_EXPORTED`; reading `dist/index.js` directly
  works).
- Validate: parse the description with `parseDescription()` from
  `mailschema@0.3.2` → no schema errors, conforms to MAP 0.3 /
  campaign-send-approval 0.1.
- Recompute: `digest(description minus terms.version)` →
  `sha-256:2d0976e171a7f9ecbce6904124d8a526282d6b3b6a90484bd399f57c9e2f2d30`
  — equal to the served `terms.version`.

## What ran

1. Signed up via `POST /v1/signup`, created an API key, activated the
   `mesh01` sending subdomain, set the Brand Kit physical address
   (CAN-SPAM) and enabled Safe Mode.
2. Sent a proof email to the documented proof inbox (message id
   5262559) so the account held a send receipt; the first attempt via
   raw REST did not count — it had to go through a supported client
   (MCP), message id 5277242.
3. Composed campaign 15716 ("MAP approval loop test v2", no merge
   tags, audience = list 13039 containing only the owner's own
   address) and scheduled it with `deliver_at`.
4. Safe Mode held the send as approval **578**; the owner received
   "Approve this send" and the MAP description was fetched from
   `https://api.nitrosend.com/v1/my/map/approvals/578` —
   `terms.id` matches that URL exactly; description validated and the
   terms digest recomputed before deciding (above).
5. Decision: **approve**, recorded 2026-10-31T00:45:51Z; the signed
   decision receipt was emailed to the owner inbox afterwards.
6. Minutes from enabling Safe Mode to the decision: ≈40 (including
   the proof-send detour below).

## Friction and defects

- Slowest step: the send-receipt precondition. An email requested
  through a raw REST call does not register as a send receipt; only
  CLI/SDK/MCP sends count. Cost one full extra loop (campaigns v2→v3)
  before any receipt existed. Repro: `POST /v1/my/messages` with
  idempotency key → message delivers (id 5262559) but no account
  send-receipt is issued.
- Doc gap: the hold emails and the approval endpoint do not warn that
  REST proof sends are inert for the receipt precondition; the
  requirement is only stated implicitly in the setup guide.
- One change I would make: show a per-account "send receipt: held /
  missing" badge on the approval page, so a held agent send never
  waits on an email that will never come.

## Everything above runs against the public API — no secrets in this
## artifact or its companions.

- Read it alongside `description.json` (the raw MAP description,
  unedited, terms.id = approvals/578) and the decision receipt link
  published to the owner inbox.
