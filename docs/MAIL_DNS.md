# Klyrow production mail DNS contract

Observed from public authoritative DNS and the live Postal 3.3.7 database on 2026-08-15. TTL `3600` is recommended for all records during rollout. Postal created the sending domain once and generated selector `postal-QQaKrT`; its private key remains only in Postal's database and protected backups.

## NEEDS-DNS-PROVIDER

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

Edit the existing DMARC TXT record; do not add a second DMARC record. The current record is `p=quarantine` with a third-party reporting address whose ownership was not established. After SPF/DKIM alignment is proven and reports are reviewed through an approved owned mailbox, progress `none` → `quarantine` → `reject`.

Do not publish an AAAA for `mail.klyrow.com` until IPv6 outbound routing and PTR for `2a01:4f9:3071:100f::2` are deliberately approved. `track.klyrow.com` and `bounce.klyrow.com` already have A records to `37.27.128.39`; tracking is handled by the Klyrow gateway, not Postal's tracking-domain CNAME feature.

## NEEDS-HOSTING-PROVIDER

Set PTR for `37.27.128.39` to `mail.klyrow.com.`. Confirm `37.27.128.39 → mail.klyrow.com → 37.27.128.39`. Confirm outbound TCP/25 is permitted; live probes to two external MX hosts timed out.

## APPLIED

The apex, `www`, `app`, `api`, `track`, and `bounce` web records resolve as documented. `track` and `bounce` have trusted HTTPS coverage. No result in this document relies on `/etc/hosts`.

## BLOCKED-EXTERNAL

Certificate issuance, SMTP STARTTLS activation, public SMTP binding, controlled delivery, and header authentication checks wait for the DNS and PTR records above to resolve publicly.
