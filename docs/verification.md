# Verification and evidence

The local CLI scenario invokes the same domain service as the API. Expected denials are asserted, not substituted with canned responses. Public sample output is captured by executing it against the committed synthetic inputs. Python tests include authorization, schema boundaries, tenant separation, independent subjects, idempotency conflicts, concurrent replay and audit tampering. Domain-specific cases exercise evidence fidelity, stale decisions and expiry. Browser tests use the actual HTTP server without mocked responses and check the narrow mobile layout. The screenshot is captured from that run.

Python coverage includes the entire `app` package, statements and branches, with an 80% minimum gate. CLI startup and optional native collectors remain in the denominator. Node coverage measures the imported TypeScript scenario contract and reference resolver only. It does not measure the browser application or Python service. Browser and Docker results are separate checks, not added to either coverage percentage.

The restricted Docker smoke check verifies a non-root UID, HTTP response and content security policy under a read-only root with dropped capabilities. A separate container command runs the complete CLI demonstration with external networking disabled. Dependencies require network during setup/build. Hosted CI uses SHA-pinned actions, contents-read permission and disabled checkout credential persistence. Python lockfiles contain hashes and Node versions are locked. Runtime dependency advisory checks are performed separately for both languages.

`docs/local-verification.json` records measured local results. `docs/hosted-verification.json`, after publication, identifies the exact hosted commit and Verify run. Green CI applies to that revision only and is not a guarantee of external account permissions, production scalability or absence of all vulnerabilities.

[Hosted Verify run 41370911097](https://github.com/jayekwere/careboundary/actions/runs/41370911097) passed at `60f57568ea837a424f39dd8f6a6b7af0e8539235`. Exact jobs, steps and artifact digests are recorded in [the hosted receipt](hosted-verification.json).

Public CI artifacts use an explicit file allowlist and reject private-key markers. Browser state stays outside that public evidence set.

[Hosted Verify run 41371621704](https://github.com/jayekwere/careboundary/actions/runs/41371621704) passed at `60986bccb1365d33e63ec3e006698e631567c3a0`. Exact jobs, steps and artifact digests are recorded in [the hosted receipt](hosted-verification.json).

A dedicated negative test rejects integer and string aliases for the literal synthetic marker. This check is necessary because the underlying validation library accepts integer `1` for a boolean literal unless a pre-validator rejects it. The Actions badge identifies validation of the current revision; the JSON receipt remains an immutable historical verification point.
