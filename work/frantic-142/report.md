# Frantic bounty #142 — MAP approval loop report

**Task:** Approve or decline an agent's held campaign after checking its MAP description.
**Account:** Nitrosend account for `info@mesh-01.com` (account_id 13832), brand sid `7a3d023ef09df8a38a538213`, sender `hello@mesh01.nitrosend.net`.

## What ran

1. Signed up via `POST /v1/signup`, created API key, activated `mesh01` sending subdomain.
2. Sent proof email to `proof@dogfood.nitrosend.net` (message id 5262559) so the account held a send receipt.
3. Set the physical mailing address in the Brand Kit (CAN-SPAM), enabled Safe Mode.
4. Created list `13039` with the account owner's own address as sole contact, composed campaign `15696` ("MAP approval loop test", no merge tags, audience = the list) and scheduled it with `deliver_at`.
5. Safe Mode held the send as `awaiting_approval`; the owner received "Approve this send" and the MAP description was fetched from `https://api.nitrosend.com/v1/my/map/approvals/563` — the description's `terms.id` matches that URL exactly.

## Check before deciding

- `npx mailschema@0.3.2 description description.json --contract campaign-send-approval-0.1.json` → **Valid MAP 0.3 description**.
- Recomputed `terms.version` with the package `digest()` over the description minus `terms.version` → `sha-256:7abeea6cf4ceda9f5c5f3058311f5ded94a2930940593dbc2bed34035451f517` — **equal to the served `terms.version`**.

## Decision

**Approve.** The description's terms matched the held send exactly: campaign 15696, single recipient (the owner's own address), scheduled delivery. Approving at the verified terms version exercised the intended loop end-to-end: agent request → hold → MAP description check → owner decision → release.

Receipt: issued by Nitrosend to the owner inbox after the decision (`runx.ai` link delivered alongside).
