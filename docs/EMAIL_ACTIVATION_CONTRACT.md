# General-email activation and runtime reconciliation

The gateway, mail worker, SMTP relay, Postal web, Postal worker, and Postal SMTP
must declare one complete general-email profile. A healthy process or a single
`LIVE_EMAIL_DELIVERY=true` flag does not establish end-to-end delivery.

| Control | Disabled profile | Live-eligible profile |
| --- | --- | --- |
| `KLYROW_SAFE_MODE` | `true` | `false` |
| `KLYROW_PRODUCTION_GATE_APPROVED` | `false` | `true` |
| `LIVE_EMAIL_DELIVERY` | `false` | `true` |
| `EXTERNAL_EMAIL_DELIVERY` | `false` | `true` |
| `PRODUCTION_PROVIDER_ROUTING` | `false` | `true` |

`delivery_safety.py` enforces all five controls for general gateway/worker email.
Missing values, malformed values, or any closed gate keep that path in safe mode.
Only the literal strings `true` and `false`, ignoring case and surrounding
whitespace, are accepted. Existing tenant, sender, suppression, canary, campaign,
and reconciliation controls continue to apply after these process gates open.

SECURITY SMTP is a separate credential- and recipient-scoped path controlled by
`smtp_policy.py`. General-email activation neither grants SECURITY SMTP authority
nor enables live non-SECURITY SMTP, which remains sandbox-only. SMS, PSTN,
marketing, and bulk controls are outside this overlay.

## Readback API

`GET /v1/admin/delivery/activation` uses the existing bearer authentication and
requires `platform_admin`. It returns the normalized five controls, missing or
invalid control names, blocking controls, `safe_mode`, and `live_delivery_enabled`.
It provides no activation mutation and does not read Docker or secret files.

The same `email_activation` object is included in gateway `/health`,
`/v1/health`, `/capabilities`, and the private worker health response. Its scope is
`process_general_email`; it explicitly reports stack consistency and end-to-end
delivery as `unverified`. `live_eligible` describes environment configuration,
not recipient delivery, a consumed canary allowance, or a provider acknowledgment.

## Deployment and runtime validation

The base Compose file remains disabled. `compose.email-activation.yaml` is an
explicit release overlay that applies the same five values to all six components.
Use it only as part of the approved, checksum-bound complete release composition.
Include it after the other overlays and use the exact same composition for config
validation, release-authority verification, and deployment. Standard launchers
keep their disabled composition; this change does not silently activate it.

`scripts/verify-release-authority` now validates the rendered configuration before
the pre-pull and post-pull authority checks can succeed. Therefore `start`, `deploy`,
and `update` all reject missing components, missing/invalid controls, partial
profiles, and gateway/worker/Postal mismatches before starting containers.

For an already selected Compose command, pipe the full rendered JSON directly to
the validator without saving or printing secret-bearing configuration:

```bash
set -o pipefail
"${COMPOSE[@]}" config --format json | python3 scripts/verify-email-activation
```

Read back the six exact deployed container identities using the inspect mode:

```bash
set -o pipefail
docker inspect klyrow-gateway-1 klyrow-worker-1 klyrow-smtp-relay-1 \
  klyrow-postal-web-1 klyrow-postal-worker-1 klyrow-postal-smtp-1 \
  | python3 scripts/verify-email-activation --source inspect
```

The output contains only normalized control booleans and fixed diagnostic names;
credentials, arbitrary environment values, and health logs are not echoed.
Exit code `0` means the configuration agrees, `1` means it is blocked, and `2`
means the input is invalid. Inspect mode additionally requires running containers
and rejects duplicate identities. Stop on any failure; never replay queued mail
or rewrite retry/dead-letter states to make a check pass.

## Postal enforcement and completion evidence

Native Postal does not acquire a Klyrow kill switch merely because Compose
declares an environment flag. Review the exact Postal image and any mounted
entrypoint that consumes it. Both validator modes report `postal_enforcement`
and `end_to_end_delivery` as `unverified`; configuration parity alone cannot
promote either field to verified.

Completion requires the approved immutable images and config checksum, runtime
readback from every component, reviewed Postal enforcement, and an authorized
bounded message to a controlled recipient. Reconcile its immutable message ID
with Postal acceptance and the signed delivery callback/recipient evidence.
SMTP acceptance alone is not delivery. Preserve unknown outcomes for reconciliation
and retain the reviewed rollback manifest and backup evidence.

## Observed server discrepancy, September 9, 2026

On `37.27.128.39`, the gateway, worker, and SMTP relay declared the live-eligible
profile. Postal web/worker/SMTP declared only `LIVE_EMAIL_DELIVERY=false` from the
five controls; the other four were unset. All three Postal services used a
host-mounted `live-gate` entrypoint. Reading that protected script was denied to
the SentinelX account, so its enforcement behavior remains unknown.

The running gateway revision was `da9d85891a4e313748e309aed86662d6c03d26bb`.
This source change does not update that image, alter delivery settings, or send
mail. A runtime rollout still requires the existing protected release authority.
