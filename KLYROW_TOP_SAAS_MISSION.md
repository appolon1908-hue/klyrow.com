# Klyrow Top SaaS Expansion Mission

You have full autonomy to evolve the existing Klyrow production email platform into a top-tier multi-tenant SaaS product while preserving the current safe-mode protections, Mautic → Postal architecture, middleware integration, tenant isolation, and production safety controls.

## Current baseline

Klyrow already has a production branch with Dockerized Mautic, Postal, gateway, portal, RBAC, tenant isolation, API keys, suppressions, quotas, signed webhooks, monitoring, backups, and safe-mode delivery controls.

Do not replace working components without a clear migration reason. Extend the current platform.

Production delivery must remain gated until DNS, PTR/rDNS, TLS, middleware connectivity, and owner-approved external sending tests pass.

## Goal

Make Klyrow competitive with leading modern email/marketing SaaS platforms by combining:

- high-quality email delivery infrastructure
- real-time customer data and segmentation
- powerful automation journeys
- excellent deliverability operations
- strong developer APIs
- polished client/admin experience
- advanced analytics and experimentation
- AI-assisted workflows
- strict compliance, consent, and tenant isolation
- horizontal scalability and operational resilience

## 1. Unified customer data and event platform

Build a first-class customer profile/event layer owned by Klyrow.

Support:
- profiles with multiple identifiers
- email, phone, external CRM ID, customer ID
- custom attributes
- custom events
- event properties
- page/app/activity events where explicitly integrated
- profile merge rules
- identity resolution
- profile timelines
- event ingestion API
- batch import
- CSV import/export
- middleware/Odoo synchronization
- data retention policies
- consent and preference fields

Create versioned APIs for:
- profile create/update
- event ingestion
- bulk import
- profile lookup
- event lookup

Do not write directly to Odoo PostgreSQL.

## 2. Real-time segmentation engine

Build dynamic segments that recalculate from customer attributes and behavior.

Support:
- AND/OR nested rules
- profile attributes
- event occurrence
- event count
- event properties
- date/time windows
- engagement conditions
- campaign activity
- opens/clicks/bounces/unsubscribes
- geographic fields
- CRM/Odoo fields delivered through middleware
- manual segments
- exclusion segments
- suppression-aware segments

Add segment preview, estimated audience size, sample profiles, usage references, and audit history.

Segments must update safely without leaking data across tenants.

## 3. Visual journey and automation builder

Build a polished drag-and-drop journey builder on top of Klyrow/Mautic capabilities.

Support nodes for:
- trigger
- segment entry
- API/event trigger
- wait/delay
- wait-until
- email send
- conditional split
- percentage split
- A/B branch
- goal/conversion
- update profile
- webhook/API call
- internal middleware event
- add/remove segment
- unsubscribe/suppress
- stop/exit

Support journey versioning, draft/publish, rollback, pause, resume, per-profile journey history, and troubleshooting views.

Allow conversion goals and exit criteria.

## 4. Campaign, template, and content studio

Build a modern email content experience.

Include:
- drag-and-drop email builder
- responsive templates
- HTML editor
- plain-text preview
- reusable blocks
- saved brand styles
- variables/personalization
- conditional content blocks
- dynamic sections
- image/media library
- test-send workflow
- inbox preview hooks where available
- mobile/desktop preview
- template version history
- clone/template library

Enforce safe HTML sanitization and tenant isolation.

## 5. Experimentation and optimization

Add structured experimentation.

Support:
- subject-line A/B tests
- sender-name tests
- content tests
- CTA tests
- send-time tests
- percentage splits
- holdout/control groups
- automatic winner selection
- configurable success metric
- statistical confidence reporting

Store experiment definitions and results with auditability.

## 6. Advanced analytics and attribution

Build a serious analytics layer.

Dashboard metrics should include:
- accepted
- queued
- sent
- delivered
- bounced
- deferred
- complaints
- unsubscribes
- opens
- unique opens
- clicks
- unique clicks
- click-through rate
- delivery rate
- bounce rate
- complaint rate
- unsubscribe rate
- campaign conversion rate
- automation conversion rate
- tenant usage
- domain usage
- message volume over time

Add:
- campaign comparisons
- segment performance
- journey performance
- cohort analysis where practical
- engagement trends
- top links
- geo/device summaries where lawfully collected
- conversion events from middleware/Odoo
- revenue attribution fields if the customer supplies revenue events

Do not invent revenue data.

## 7. Deliverability command center

Build a dedicated deliverability dashboard and operational controls.

Track per tenant/domain/IP where available:
- SPF status
- DKIM status
- DMARC status
- PTR/rDNS status
- TLS status
- bounce rate
- complaint rate
- block/defer rate
- delivery latency
- suppression growth
- queue depth
- domain verification state
- sending volume trends

Add alerts for:
- DNS verification failure
- certificate expiry
- abnormal bounce spike
- complaint spike
- deferral spike
- queue backlog
- domain suspension

Implement compliant sending-ramp guidance for newly verified senders, based on explicit opt-in traffic and conservative volume controls. Do not implement spam-evasion or provider-bypass features.

## 8. Consent, preference, and compliance center

Make compliance a core product feature.

Support:
- consent source
- consent timestamp
- consent version
- double opt-in workflow where configured
- subscription categories/topics
- global unsubscribe
- list/topic unsubscribe
- suppression reasons
- complaint suppression
- hard-bounce suppression
- preference center
- export/delete request workflow
- consent audit history
- tenant-configurable retention rules

Implement enforcement at send time so suppressed/unsubscribed recipients cannot be sent marketing email accidentally.

## 9. Developer platform

Make Klyrow excellent for developers.

Provide:
- versioned REST API
- OpenAPI spec
- API explorer
- API-key scopes
- rate limits
- idempotency keys
- request IDs
- SDK generation targets for JavaScript/TypeScript, Python, PHP, and curl examples
- webhook signing
- webhook replay protection
- webhook delivery logs
- manual webhook resend
- sandbox/test mode
- test API keys
- mock/simulated delivery events

Do not expose raw Postal or Mautic admin APIs as the public product surface.

## 10. Integrations marketplace foundation

Create a connector framework so future integrations can be added without changing core architecture.

Prioritize:
- Odoo through existing middleware
- n8n through existing middleware
- Google OAuth/Gmail/Workspace authorized workflows
- generic webhook connector
- CSV import/export
- REST source/destination connector

Prepare extension points for future CRM/ecommerce integrations.

Do not use Gmail as the bulk delivery engine.

## 11. AI-assisted capabilities

Add optional AI-assisted features behind clear controls.

Implement interfaces for:
- subject-line suggestions
- email draft generation
- tone/length rewrite
- campaign summary
- segment creation from natural-language rules
- journey draft generation
- send-time recommendation using tenant engagement history
- anomaly explanations for bounce/delivery changes

AI must not autonomously send campaigns without explicit user confirmation.

Do not send private tenant content to an external AI service unless the tenant/admin has configured and approved that provider.

Provide provider abstraction so AI can be disabled or swapped.

## 12. Enterprise SaaS controls

Add production SaaS account management.

Support:
- organizations/tenants
- multiple users per tenant
- invitations
- roles
- platform_admin
- tenant_admin
- marketer/operator
- developer
- analyst/read_only
- support role with controlled impersonation/audit if implemented
- MFA/TOTP
- session management
- session revocation
- audit logs
- API-key lifecycle
- domain ownership verification
- account suspension
- quota controls

Prepare SSO/SAML/OIDC extension points for enterprise customers.

## 13. Billing and plan engine

Build a provider-agnostic SaaS billing foundation.

Support:
- plans
- monthly message allowance
- contact/profile allowance
- API limits
- user-seat limits
- overage rules
- trial state
- active/past-due/suspended states
- usage ledger
- invoice metadata
- manual credits/adjustments
- audit history

Do not hard-code one payment provider into the data model.

Do not bill users during development tests.

## 14. Marketing vs transactional separation

Create distinct policy and operational paths for:
- marketing email
- transactional email

Support separate:
- API credentials/scopes
- sending streams
- quotas
- suppression behavior where legally appropriate
- analytics
- templates
- sender domains
- delivery policies

Transactional traffic must not silently bypass mandatory legal/abuse protections.

## 15. Reliability, scaling, and high availability

Design Klyrow so the current server is node 1, not the permanent limit.

Prepare architecture for:
- multiple gateway/API nodes
- multiple workers
- queue scaling
- database backup/replica strategy
- Postal worker scaling
- Mautic worker scaling
- load balancer/reverse proxy scaling
- stateless sessions where practical
- centralized persistence
- graceful deployment/rollback
- rolling updates
- maintenance mode
- health/readiness checks

Add resource limits and autoscaling guidance.

## 16. Observability and SRE controls

Expand Prometheus/Grafana or equivalent.

Add dashboards and alert-ready metrics for:
- API latency/error rate
- webhook failures
- SMTP queue health
- Postal workers
- Mautic jobs
- campaign scheduler
- database health
- Redis/RabbitMQ health
- CPU/RAM/disk
- TLS expiry
- DNS verification state
- tenant volume spikes
- deliverability anomalies

Create structured logs, correlation IDs, audit logs, and runbooks.

## 17. Client onboarding wizard

Build a guided onboarding flow:

1. create organization
2. invite team
3. choose use case
4. add sending domain
5. show exact DNS records
6. verify SPF/DKIM/DMARC
7. show PTR dependency where relevant
8. create first API key or campaign
9. import contacts with consent confirmation
10. send test message
11. configure webhook
12. launch checklist

Do not allow production bulk sending until required verification and compliance gates pass.

## 18. Admin operations center

Expand the platform admin interface with:
- tenant health
- sending domains
- volume
- queue state
- deliverability risk
- bounce/complaint thresholds
- abuse flags
- account suspension
- API-key revocation
- audit history
- webhook failures
- TLS/DNS state
- system resource health
- background job health
- Postal/Mautic service health

Include safe support tooling without exposing tenant secrets.

## 19. Cross-channel future readiness

Do not merge Telnexa into Klyrow, but prepare a clean event/API contract so a future unified customer journey can coordinate email and SMS through middleware.

Possible future flow:
Klyrow journey event → middleware → Telnexa SMS

Keep products separately deployable and separately permissioned.

## 20. Security hardening

Maintain and extend:
- HTTPS everywhere public
- free trusted ACME/Let's Encrypt certificates with automatic renewal
- certificate expiry monitoring
- SMTP TLS
- secure cookies
- HSTS where appropriate
- CSP
- CSRF controls
- password hashing
- MFA
- rate limiting
- SSRF prevention
- parameterized database access
- XSS protection
- webhook allow/deny controls
- secret rotation
- no secrets in Git
- dependency scanning
- Docker network isolation
- non-public Redis/database/RabbitMQ

Do not weaken security to make tests pass.

## Required test expansion

Add automated tests for:
- dynamic segmentation
- journey execution
- journey pause/resume
- conversion goals
- tenant isolation
- content personalization
- unsubscribe enforcement
- preference-center changes
- experiment assignment
- experiment winner calculation
- API idempotency
- webhook replay rejection
- rate limits
- domain verification
- deliverability alerts
- admin suspension
- MFA if implemented
- audit logs
- billing usage ledger
- marketing/transactional separation
- safe-mode production gate
- horizontal worker restart/recovery

## Deployment rules

Continue on branch:
`agent/production-email-platform`

Keep the current PR updated rather than creating an unrelated implementation branch unless technically necessary.

Commit logically grouped changes and push regularly.

Update documentation and DEPLOYMENT_REPORT.md with implemented, tested, blocked, and future items.

Do not merge the PR until critical tests pass.

Do not enable unrestricted production sending until:
- required DNS is published
- PTR/rDNS is correct
- trusted TLS is active
- middleware connectivity is restored
- controlled external test delivery is explicitly authorized
- suppression/consent enforcement is verified

## Priority order

Implement in this order:

### P0 — launch-critical SaaS quality
- onboarding wizard
- dynamic segmentation
- journey builder core
- deliverability command center
- preference/consent center
- analytics dashboard
- API/webhook developer experience
- MFA/audit hardening
- launch gates and DNS/TLS/PTR verification

### P1 — competitive differentiation
- advanced experimentation
- AI-assisted drafting/segmentation/journey creation
- advanced attribution/cohorts
- integrations framework
- billing/plan engine
- expanded admin operations center

### P2 — enterprise/scale
- SSO/OIDC/SAML extension points
- high-availability architecture
- multi-node worker scaling
- advanced support tooling
- cross-channel middleware contract with Telnexa

## Definition of done

This mission is complete when:
- P0 features are implemented and tested
- existing Mautic → Postal flow still passes
- tenant isolation still passes
- consent/suppression enforcement passes
- dynamic segments work
- journey automation works
- analytics populate from real internal events
- deliverability dashboard reflects actual system/DNS state
- onboarding wizard works
- API/webhook docs are complete
- security tests pass
- no production secrets are committed
- all safe-mode launch gates remain enforced until external requirements are complete
- DEPLOYMENT_REPORT.md clearly distinguishes implemented, tested, blocked, and P1/P2 backlog

Proceed autonomously through implementation, Docker deployment, migrations, testing, documentation, commits, and PR updates. Fix routine failures yourself. Stop only for missing external credentials, provider-level DNS/PTR changes, or destructive actions affecting unrelated production data.