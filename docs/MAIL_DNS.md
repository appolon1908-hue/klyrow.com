# Klyrow production mail DNS contract

Observed from both authoritative nameservers, Cloudflare `1.1.1.1`, Google `8.8.8.8`, and the live Postal 3.3.7 database on 2026-08-15. TTL `3600` is recommended for all records during rollout. Postal created the sending domain once and generated selector `postal-QQaKrT`; its private key remains only in Postal's database and protected backups.

## APPLIED

Every record in the table below is publicly present and consistent. Postal independently reports ownership verified and SPF, DKIM, MX, and return-path status `OK`. `_dmarc.klyrow.com` returns exactly one TXT record.

| Type | Host/name | Exact value | TTL | Purpose |
|---|---|---|---:|---|
| A | `mail.klyrow.com` | `37.27.128.39` | `3600` | SMTP hostname and HELO forward resolution |
| MX | `klyrow.com` | `10 mail.klyrow.com.` | `3600` | Postal inbound routing and domain validation |
| MX | `bounce.klyrow.com` | `10 mail.klyrow.com.` | `3600` | Postal route/bounce ingress |
| TXT | `klyrow.com` | `v=spf1 include:spf.klyrow.com ~all` | `3600` | Authorize the deployed Postal SPF include; staged soft-fail |
| TXT | `spf.klyrow.com` | `v=spf1 ip4:37.27.128.39 -all` | `3600` | Authorize only the verified IPv4 outbound host |
| TXT | `postal-QQaKrT._domainkey.klyrow.com` | `v=DKIM1; t=s; h=sha256; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC4KQys+axMbGLcElf0WvbIi9z/jySwuRQ1hLUqTaKakWXBI4fqEj5kH8OOam4AQo6/6W68C6QtZM39a1bJF/lkfzG7brjuLOBBIWyUXNgS/UJIrJHu2+6IvqCPyaX/cLrwhgYVTU7gjtYEdG3/QNeJRGQkGqf7jTi8Gnz3JqKk+QIDAQAB;` | `3600` | Live Postal DKIM public key |
| TXT | `klyrow.com` | `postal-verification rjXOtdO7qcqtmMocTcnpMv0xiczgwY1w` | `3600` | Live Postal domain ownership verification |
| CNAME | `psrp.klyrow.com` | `bounce.klyrow.com.` | `3600` | Postal custom return-path alignment |
| TXT | `_dmarc.klyrow.com` | `v=DMARC1; p=none; adkim=r; aspf=r` | `3600` | Staged monitoring policy without an invented reporting mailbox |

The prior DMARC TXT record was replaced rather than duplicated. After SPF/DKIM alignment is proven and reports are reviewed through an approved owned mailbox, progress `none` → `quarantine` → `reject`.

Do not publish an AAAA for `mail.klyrow.com` until IPv6 outbound routing and PTR for `2a01:4f9:3071:100f::2` are deliberately approved. `track.klyrow.com` and `bounce.klyrow.com` already have A records to `37.27.128.39`; tracking is handled by the Klyrow gateway, not Postal's tracking-domain CNAME feature.

## NEEDS-HOSTING-PROVIDER

Set PTR for `37.27.128.39` to `mail.klyrow.com.`. Confirm `37.27.128.39 → mail.klyrow.com → 37.27.128.39`.

Public resolvers currently return `static.39.128.27.37.clients.your-server.de.`. Although that hostname resolves forward to `37.27.128.39`, it does not match Postal's `mail.klyrow.com` HELO identity. Forced-IPv4 outbound TCP/25 probes to external Google MX hosts pass. No SMTP message transaction occurred.

## BLOCKED-EXTERNAL

Per the deployment gate, mail certificate issuance and SMTP STARTTLS activation wait for PTR to become `mail.klyrow.com.` and forward-confirm correctly. Controlled delivery also waits for an explicitly approved recipient. No result in this document relies on `/etc/hosts`.
