# Klyrow and Keycloak connection review — 2026-09-10 UTC

Klyrow runs on 37.27.128.39 (private 10.40.0.4); the canonical Codestra Keycloak
issuer resolves to 65.109.65.169. Checks below used the running gateway, the
configured Keycloak database in a read-only transaction, and a no-message SMTP
handshake. No user credentials, bearer tokens, mail contents or customer records
were exported. No email, SMS, password reset or customer login was performed.

| Connection | Observed result | Required work |
| --- | --- | --- |
| Gateway → OIDC discovery | HTTPS 200; exact issuer `https://auth.codestra.co/realms/codestra` | Connected |
| Gateway → signing keys | HTTPS 200; two published keys | Connected; actual human-token verification needs a controlled login |
| Browser → Keycloak | `/auth/login` returns 302 with `klyrow-portal`, exact `https://app.klyrow.com/auth/callback`, PKCE S256; Keycloak login form returns 200 | Connected; no completed human login was claimed |
| Portal callback source | Keycloak repository still declared `https://klyrow.com/`; live client and Klyrow BFF use the app callback | Correct the Keycloak desired state before its next apply |
| Access-token audience | Klyrow verifier expects `klyrow-api`; the live portal's client-specific mapper names `codestra-kong-certification` | Reconcile the reviewed portal audience mapper; inherited scopes were not certified |
| Code exchange and refresh | Existing source used ambient HTTP proxy settings and did not consistently reject non-object token responses | This PR shares canonical no-proxy/no-redirect transport and sanitizes malformed responses |
| Keycloak → Klyrow SMTP | Private 10.40.0.4:587 answers EHLO/STARTTLS; IP-based certificate verification fails | Use certificate hostname `mail.klyrow.com` with private address resolution |
| SMTP hostname verification | Connecting to 10.40.0.4 with TLS hostname `mail.klyrow.com` verifies successfully; AUTH advertised after TLS; NOOP 250 | Private transport verified; SMTP authentication and delivery remain unverified |
| Realm security mail | Live `codestra` realm has no SMTP rows | Provision the dedicated SECURITY credential and apply reviewed SMTP settings |
| Klyrow SECURITY configuration | Gateway has no configured SECURITY tenant, username or sender; enable/production switches absent | Provision and verify the dedicated stream before security mail activation |
| Canonical `klyrow-gateway` events identity | Desired Keycloak client exists in Git; no matching live Codestra client found | Apply the reviewed machine identity and corresponding Middleware release |
| Legacy service identities | Live `klyrow-email-provider` and `klyrow-email-adapter` exist; adapter has full scope enabled | Inventory their consumers and retire or narrow through the protected identity plan; do not repurpose them for the canonical gateway |
| New Odoo SMS identity | `odoo-sms` is absent in the live realm | Provision tenant-bound identity for Odoo #93 / Middleware #221 before SMS activation |
| Signup/recovery | Registration disabled, password reset enabled, SMTP absent in live realm | Signup and completed reset delivery are not certified |

The SMTP certificate is valid for `mail.klyrow.com`, issued by Let's Encrypt,
and expires 2026-11-13. No certificate-check bypass is an acceptable fix. The
companion Keycloak change binds that hostname to 10.40.0.4 in its dedicated
Compose service and updates the SMTP contract/validation together.

Keycloak repository authority requires a merged exact-source release, verified
runtime paths, a check plan and independent review before apply. A repository
merge alone does not change the active realm or provision SMTP credentials.
The running Keycloak Compose stack is `/opt/codestra/identity-platform/deploy/compose.identity.yaml`,
which differs from the dedicated desired-state Compose file. Verify the actual
runtime paths and map the hostname there through the approved deployment before
applying the new realm SMTP host. Preserve the current login connection during
that reconciliation.
