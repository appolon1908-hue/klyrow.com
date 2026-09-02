# Klyrow production mail DNS contract

Observed from both authoritative nameservers, Cloudflare `1.1.1.1`, Google `8.8.8.8`, and the live Postal 3.3.7 database on 2026-08-15. Public DNS was refreshed through Cloudflare and Google on 2026-09-02; both resolvers returned one matching record for the apex SPF, SPF include, bounce SPF, DKIM, and DMARC contracts, plus the expected A, MX, bounce MX, and PTR records. This read-only refresh did not submit mail. TTL `3600` is recommended for all records during rollout. Postal created the sending domain once and generated selector `postal-QQaKrT`; its private key remains only in Postal's database and protected backups.

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

## CURRENT REVERSE-DNS STATUS

Verified 2026-08-15 20:22 CEST. All three authoritative Hetzner
reverse nameservers, Cloudflare, and Google return `mail.klyrow.com.` for
`37.27.128.39`; both authoritative forward nameservers return
`mail.klyrow.com A 37.27.128.39`. PTR and identity-matched FCrDNS now pass. The
host-local certificate and STARTTLS work described in `POSTAL_SMTP.md` is
complete. No result relies on `/etc/hosts`. Bulk delivery remains disabled
pending an approved canary.

During propagation, some Cloudflare and Google recursive edges intermittently
returned the previous Hetzner hostname from cache. All authoritative reverse
nameservers consistently return `mail.klyrow.com.`; recursive caches will
converge when the prior 86400-second TTL expires.

## First-canary authentication correction

Message 1 proves receivers did not evaluate the apex SPF record. Because
Postal's cached custom-return-path status was `Missing`, its delivery envelope
fell back to `bounce.klyrow.com`. That domain has no TXT/SPF record, so Gmail
returned SPF fail. Add exactly one authoritative record:

| Type | Name | Value |
|---|---|---|
| TXT | `bounce.klyrow.com` | `v=spf1 include:spf.klyrow.com -all` |

The include terminates at `v=spf1 ip4:37.27.128.39 -all`; it has no recursion,
syntax, multiplicity, or lookup-limit issue. On 2026-09-02 Cloudflare and
Google each returned exactly one matching bounce SPF record. The propagation
blocker is therefore cleared.

Postal's domain DNS cache was refreshed after worker egress repair and now
reports SPF/DKIM/MX/return-path `OK`. The intended next envelope domain is
`psrp.klyrow.com`, aligned with From `klyrow.com` under relaxed DMARC.

Public DNS correctness is not production activation approval. The currently
published selector predates the required rotation of previously exposed Postal
DKIM keys in `SECURITY_SMTP_ACTIVATION.md`. Production domain policy remains
blocked until an approved rotation is performed, the replacement public TXT is
read back byte-for-byte, Postal reports the replacement selector active, the
prior selector is retired, and the protected backup/restore path is verified.
