# Security design decisions

- Keep state and replay receipts transactional; reject conflicting command keys.
- Derive tenant and roles exclusively from trusted identities.
- Compare independent reviewers by subject, including when one subject holds multiple roles.
- Preserve missing evidence, stale observations and unknown permissions as distinct outcomes.
- Scope exports and retain provenance instead of asserting external truth from a digest.
- Use private local files and exclusive writes for generated material.
- Keep cloud and third-party writes outside these demos.
- Pin CI actions by commit, limit workflow permissions to contents read and avoid persisted checkout credentials.
- Hash-lock Python dependencies and lock exact Node dependencies.

A valid clinician credential must not grant every patient. Tenant, patient, purpose, requester and emergency expiration are checked on each read. Support must not retrieve clinical fields through a summary. Reviewer access does not confer treatment access. Minimize log contents and never accept real personal health data into this lab.
