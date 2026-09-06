# K0 mail remediation disposition

This is a source audit for issue #49, compared on September 6, 2026 against
protected main `12c8becec4e30c497be123844f92cb070d4cc7af`. The historical
aggregate is `59e58d39f0a67c39219c76579d94e6e00766e736` (31 files). Its ten
claims come from that commit's `docs/MAIL_REMEDIATION_1_10.md` and were checked
against current modules and test coverage. This is not runtime certification.

| Historical gap | Current source and disposition |
|---|---|
| 1. Inbound/shared inbox activation | `webmail.py`, `webmail_models.py`, and `provider_reconciliation_fixes.py` preserve tenant-owned inbound storage and replay. `test_webmail_inbound_ownership.py` covers route ownership, attachments, and reader restrictions. The historical 16-address manifest and aggregate activation/readiness endpoints remain absent. |
| 2. Middleware outage returns 503 | `main.postal_hook` persists a retry record but still returns 503 after Middleware failure. The legacy 202-after-persistence behavior remains a focused follow-up; acceptance must also prove atomic replay/outbox persistence and interrupted-write recovery. |
| 3. Machine credentials and transport selection | `main.auth` validates resolver/JWT authority; #92 adds exact mutation capability resolution. `postal_provisioning.py` and `tenant_postal_delivery.py` use tenant/domain credentials and reject an unprovisioned tenant's global-key fallback (`test_postal_tenant_provisioning.py`). This does not establish support for the aggregate's raw scoped-key/service-secret login or its domain-selected transport registry. Those require canonical identity/transport reconciliation. |
| 4. Structured versus SECURITY MIME payloads | Structured core messages use `tenant_postal_delivery.attributed_postal_payload`; SECURITY MIME remains encrypted, purpose-specific, and scrubbed by `security_smtp_worker.py`. `test_browser_email_postal_e2e.py` and SECURITY worker tests cover these separate paths. The old mixed-purpose worker must not replace them; general `ProviderMessage` live-adapter parity remains to be proved. |
| 5. PTR evidence | The current deliverability route used only the final IPv4 octet and accepted hostname substrings. The accompanying focused patch fixes both defects. External DNS and the complete launch gate still require independent evidence. |
| 6. Campaign activation | Current campaign canary controls remain authoritative. #90 explicitly rejects unsupported future scheduling. Historical phrase-attested activation endpoints are absent and must not be used to bypass current capability, canary, or delivery controls. |
| 7. Tracking and placement | Current lifecycle analytics exist in `saas.py`; `docs/MAIL_DNS.md` assigns tracking to the gateway. Historical Gmail seed OAuth/placement modules and endpoints are absent. Their tenant consent, secret authority, callback safety, and placement evidence remain separate work. |
| 8. Corporate role addresses | The historical versioned role manifest, provisioning tool, and status matrix are absent. Existing inbound route models do not prove staffed destination authority. Governed provisioning and destination verification remain open. |
| 9. Agent mailbox readiness | `agent_mailboxes.py` and `webmail.py` retain identity, mapping, route, and sender boundaries, with `test_agent_mailboxes.py` and webmail ownership coverage. The historical aggregate readiness report is absent; actual external adapter attestations are still required. |
| 10. Source/deployment drift | Current digest-bound Compose, source/configuration checks, previous-release rollback evidence, schema dependency, and protected image workflows supersede the aggregate's commit-tag-only launchers. See `scripts/verify-release-authority`, `scripts/verify-release-authority.py`, and `test_production_readiness.py`. Do not restore the old whole-file deployment/Compose versions. |

The historical direct `/v1/webhooks/postal-inbound` route is also not an
automatic port: `docs/SERVER_37_KLYROW_SOURCE_REMEDIATION.md` explicitly records
why a direct inbound route was rejected. Preserve the current authenticated
inbound results, tenant attribution, quarantine, and attachment replay checks.

## PTR regression and validation

For `mail.example.com -> 192.0.2.45`, the route now queries
`45.2.0.192.in-addr.arpa`. It requires an exact case-insensitive PTR hostname
match, allowing the DNS terminal dot. Prefix/suffix lookalikes do not qualify.
Missing forward addresses, empty answers, NXDOMAIN, and resolver timeouts keep
PTR false. Tenant ownership is checked before DNS and the result is persisted
under that tenant. TLS and the other readiness conditions remain required.

The new HTTP regression module reproduced three failures on the protected
baseline (one incorrect reverse query and two false-positive hostnames).
After the patch, all 12 PTR cases plus the eight existing SaaS tests passed.
The tests use synthetic DNS responses and do not modify DNS or send email.

This inventory does not close #49: the open rows above and the other four
historical tips still need complete acceptance evidence. The two billing
regressions previously found during K0 reconciliation are merged through #93.
