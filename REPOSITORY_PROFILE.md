# Repository Profile — `klyrow.com`

## Identity

- **Repository:** `appolon1908-hue/klyrow.com`
- **Category:** Communications runtime — email
- **Visibility:** `public`
- **Default branch:** `main`
- **Authority:** Primary Klyrow email/SaaS backend and Postal/Mautic runtime authority
- **Status:** Production-oriented tenant-isolated email platform with safe mode and independent production gates.

## Purpose

Provides authenticated email submission, sender-domain onboarding, templates, campaigns, consent/preferences, suppressions, deliverability, journeys, analytics, delivery events, billing foundations, portals, metrics, backups, and operator controls around Postal and Mautic.

## Owns

- Postal/Mautic submission and provider message state
- Domain, sender, SPF/DKIM/DMARC, bounce, complaint, suppression, and reputation evidence
- Email tenant/application state, signed events, safe-mode runtime, backup, and restore

## Does not own

- Public Klyrow marketing website
- Cross-system authorization or privileged application writes
- Alternate direct Postal/Mautic access for browsers or products

## Key integrations

- Middleware as the only privileged command boundary
- `SDK-repository` Communications API contracts
- Kong/Keycloak and Caddy
- Postal, Mautic, SMTP, DNS/PTR, and signed provider callbacks

## Current priorities

1. Complete Communications API v1 email mapping and duplicate-safe reconciliation
2. Prove domain verification, sender eligibility, deliverability, consent, and suppression flows
3. Preserve uncertain outcomes as reconciliation work instead of resending blindly
4. Certify safe mode, abuse handling, backup/restore, immutable releases, and production gates

## Governance and safety

- Target promotion model: `feature/docs/fix/security/upgrade -> development -> test -> staging -> production -> main`.
- Use pull requests and exact-head/merge-result validation; merging source never authorizes deployment.
- Never commit Postal/Mautic credentials, SMTP secrets, API tokens, customer message content, or private keys.
- Production images and releases must be immutable; mutable `latest` tags are not release authority.
- `KLYROW_SAFE_MODE` and the independent production gate remain fail-closed until launch approval.
- This document does not send email, change DNS/PTR, or activate production.

## Account-wide catalog

See `appolon1908-hue/documentaions/REPOSITORY_CATALOG.md`.
