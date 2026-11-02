# CareBoundary architecture

The data model accepts only two synthetic observation labels and rejects arbitrary clinical text, names and unsanctioned fields. Normal treatment access requires the assigned clinician subject. Support reads exclude clinical observations. An emergency grant binds its requester and one patient, lasts at most thirty minutes, tracks use and is immediately blocked by a negative independent review. It is retrospective emergency review, not prior approval. Incidents preserve sensitivity, misuse uncertainty, scope, containment and an independent human privacy decision. The fixed 730-day demonstration retention marker is documented as policy, not jurisdiction selection.

## Domain sequence

Synthetic patient --> Assigned clinician check --> Optional emergency grant --> Independent retrospective review --> Privacy incident record

## Consistency and recovery

`app/domain.py` owns explicit schemas and domain transitions. `app/service.py` validates input and commits state, audit entry and idempotency receipt in one SQLite transaction with `BEGIN IMMEDIATE`. `app/api.py` authenticates server-owned identities, limits request bytes and exposes scoped operations. `app/cli.py` executes the committed scenario against the same service. `web/` validates the scenario contract and renders real API results without HTML interpolation.

A process crash before commit rolls back domain state and receipts. Local filesystem effects in the certificate authority are separate from SQLite and partial CA initialization fails closed. Container state is disposable. Persistence, backups, independent audit checkpoints and external identity lifecycle are deployment responsibilities.

## Explicit scope

Use synthetic data only. This is a small custom healthcare API, not a FHIR implementation, electronic record product or legal compliance determination. There is no real patient directory, clinical workflow, outbound notification or automated legal decision. The database is private but not encrypted by this application. The UI exposes synthetic metadata to its intended demo roles; patient clinical fields require the separate access operation. Bulk export is unsupported. Privacy decisions record an authorized human assessment and require jurisdiction-specific review before adaptation.

The privacy-scoped data-flow inventory records systems, data category, processing region, accountable owner, encryption uncertainty and configurable retention days. It produces a human-review state and never automatically determines legal jurisdiction or permits a cross-border transfer. This is a documented inventory, not active network discovery or deletion enforcement.

## Protocol and provider references

[Canadian breach guidance](https://www.priv.gc.ca/en/privacy-topics/privacy-for-businesses/privacy-breaches-at-your-business/gd_pb_201810) informs the example incident fields. Applicable law, actual notification obligations and retention must be reviewed for the organization and jurisdiction. The demonstration does not decide these automatically.
