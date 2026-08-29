# Step 3 Email Contract Matrix

Date: 2026-08-29

| SDK Contract Surface | Klyrow Provider Status | Notes |
| --- | --- | --- |
| Canonical message create | Implemented | Internal service-only route maps to existing Klyrow send engine. |
| Message read-back | Implemented | Returns `messageId`, canonical status, provider reference, correlation, and metadata. |
| Message event timeline | Implemented | Maps `ProviderEvent` rows to canonical message event items. |
| Provider health | Implemented | Reports disabled while `KLYROW_SAFE_MODE=true`. |
| Reputation | Implemented | Wraps existing Klyrow reputation metrics into canonical shape. |
| Domains | Partial | Domain and DKIM selector state surfaced; SPF/DMARC/PTR/TLS/BIMI need richer DNS evidence mapping. |
| Sender identities | Existing provider APIs | Not duplicated in Step 3 canonical shim. |
| Templates | Existing provider/Mautic surface | Canonical template API remains a later implementation step. |
| Suppressions/preferences | Existing provider APIs | Canonical write surface remains a later implementation step. |
| Live provider delivery | Gated | Forced sandbox mode; no live delivery activation. |
