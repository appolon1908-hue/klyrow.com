# Codex Task — Klyrow Website Edge Integration on Software Host

## Repository and branch

```text
Repository: appolon1908-hue/klyrow.com
Branch: ops/website-provider-host-edge
Host: 37.27.128.39 / 10.40.0.4
```

## Purpose

Prepare the existing Klyrow software Nginx edge to host the separate public website from `appolon1908-hue/klyrow-Website-` without changing the behavior of the Klyrow application, API, Postal, SMTP, Mautic, Grafana, Kyqra, tracking, bounce or internal services.

This is a cross-repository operations task. The website runtime remains owned by `klyrow-Website-`. This repository owns the existing service topology and `docker/proxy/klyrow.conf` lineage.

## Prerequisites

Do not implement the final edge split until these website items are reviewed:

- the exact website Docker runtime;
- `ops/provider-host-nginx-edge`;
- the exact website release candidate or approved staging candidate;
- confirmed free loopback website port;
- complete rollback evidence.

Read the provider-host deployment documents in the website repository.

## Current configuration audit

Inventory the live and repository configuration before editing:

- current `docker/proxy/klyrow.conf` behavior;
- active Nginx config/import path;
- current Certbot certificate names and covered hostnames;
- current upstreams for apex, `www`, `app`, `api`, `track`, `bounce`, `/mautic/`, `/ops/` and provider callbacks;
- all listeners and their owners;
- existing protected-service health.

Do not assume repository main exactly matches the live host. Record drift and stop if it cannot be reconciled safely.

## Required end state

```text
klyrow.com
www.klyrow.com       -> public website loopback upstream

app.klyrow.com       -> existing Klyrow application upstream
api.klyrow.com       -> existing Klyrow API upstream
track.klyrow.com     -> preserve current behavior
bounce.klyrow.com    -> preserve current behavior
```

Existing Mautic, Grafana, Postal, webhook and administrative routes must remain scoped to the correct host. Do not expose administrative routes on the public marketing apex.

## Required implementation

- split the combined host configuration into clear host-specific server blocks or reviewed includes;
- preserve all current non-website upstreams and policies;
- add an apex website upstream variable/configuration using loopback port 18110 only after free-port verification;
- add `www` permanent redirect to apex;
- preserve Certbot-managed certificate handling;
- preserve/accommodate ACME challenge handling;
- add request IDs, bounded timeouts, body limits, hashed-asset caching and privacy-safe logs for the website block;
- add config assembly/validation tests;
- add host-routing regression tests;
- add backup, install, reload and rollback runbook/scripts without executing production activation from this branch;
- document exact integration with the website repository release SHA and image digest.

## Protected behavior tests

Prove before and after candidate config validation:

- app/API health and version unchanged;
- Postal web/workers/SMTP health unchanged;
- tracking and bounce behavior unchanged;
- Mautic and Grafana routes unchanged;
- Kyqra listener/health unchanged;
- no private/internal listener becomes public;
- certificate coverage remains valid;
- no unrelated Nginx host changes.

## Safety

- no Caddy installation;
- no public production activation from this branch;
- no direct live config edit without reviewed source;
- no full Nginx/provider-stack restart;
- no port takeover;
- no private-key or secret commit;
- no Postal/Odoo/n8n/Keycloak/database mutation;
- no live email, SMS or billing change.

## Evidence

Report exact repository/live config comparison, candidate diff, Nginx validation, host-routing tests, protected-service tests, rollback rehearsal, blockers and the exact website release artifact this edge config expects.