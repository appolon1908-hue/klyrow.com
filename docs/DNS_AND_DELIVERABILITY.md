# DNS and deliverability

Observed 2026-08-15: `klyrow.com`, `app`, `api`, `track`, and `bounce` resolve to `37.27.128.39`; HTTPS is valid for those five names. `mail.klyrow.com`, MX, SPF, and the required mail PTR are absent. An existing DMARC record is `v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:dmarc_rua@onsecureserver.net;`. Do not publish a second DMARC record—edit the existing one if policy/reporting should change. `www` is not part of the current certificate and was not confirmed in DNS.

Publish these provider-controlled records:

| Type | Name | Exact value |
|---|---|---|
| A | `mail.klyrow.com` | `37.27.128.39` |
| MX | `klyrow.com` | `10 mail.klyrow.com.` |
| MX | `bounce.klyrow.com` | `10 mail.klyrow.com.` |
| TXT | `klyrow.com` | `v=spf1 ip4:37.27.128.39 -all` |
| TXT | `postal._domainkey.klyrow.com` | the Postal public key printed below |
| PTR | `37.27.128.39` | `mail.klyrow.com` |

Postal generated this actual DKIM value (single DNS TXT value; DNS consoles may split it into quoted chunks):

```text
v=DKIM1; t=s; h=sha256; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAukHi8NGk8SaP+lS6deEZuooyTaUBUGyiIWewauEycNVYxfSURH5tNqEeLcvQNbT+bKwRqckQpsK1Tdo+0rDTavnhcpyExuazw+K0dh9wJzaxxJkrxuAGXHp4gH8mAIHaEHOWccIJcFrwDOC+2aUzLn1siqwTO/JZzFvP7NtlydSWrAkIuyL1HXSFBEnoUrnaKaV4nzigS5aZziNco24jIxXFY49SZ0mcA35aEgozcEXLniHh3agUyttXPY8O7xkdpbVT30ApNPVd4vDgKM3kEMKi+2r+Nds2ooh093g3g5QfOYc/gHaARyFc2KiSkNUq7lcudlHG8Ugfwt/1yZVQjQIDAQAB;
```

After propagation, issue a certificate containing `mail.klyrow.com`, mount it into Postal, enable SMTP TLS/STARTTLS, verify HELO and forward-confirmed reverse DNS, and only then change the SMTP bind from loopback to the intentionally selected public ports. Test SPF, DKIM, DMARC alignment, bounce MX, unsubscribe, complaint handling, and controlled seed recipients before clearing safe mode. The present PTR is `Ubuntu-jammy-latest-amd64-base.zst.` and must be changed by the hosting provider. Production deliverability is not yet claimed.
