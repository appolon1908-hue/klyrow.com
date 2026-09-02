# Server 37 current mail-domain evidence — 2026-09-02

Scope: read-only verification of the 14 enabled inbound/outbound domains in the
live Postal database on Server 37. The database query selected only domain
name, public DKIM selector, status fields, and check timestamp. It did not read
verification tokens or DKIM private-key columns. No SMTP authentication or mail
submission was attempted.

Postal refreshed its own DNS cache between `2026-09-02T17:15:50Z` and
`2026-09-02T17:15:54Z`. Every row reported verified ownership and
SPF/DKIM/MX/return-path status `OK`. Independent queries made afterward agreed
through one authoritative nameserver, Cloudflare `1.1.1.1`, and Google
`8.8.8.8` for MX and the active public DKIM record. The SPF, return-path, single
DMARC, and tracking checks below use Cloudflare; DKIM hashes bind the normalized
public TXT response without copying key material into this evidence.

| Domain | MX 3-way | SPF | DKIM 3-way | Return path | DMARC exactly 1 | Tracking | DKIM public-record SHA-256 |
|---|---|---|---|---|---|---|---|
| `beyvra.com` | PASS | PASS | PASS | PASS | PASS | PASS | `669255324878dc7a11a608e064fb9e573ea4083eef23990f482e4d4d9ddd45f1` |
| `breero.com` | PASS | PASS | PASS | PASS | PASS | PASS | `e5765da7a1378a8effa102bda586868fe209b54409b472c43c840084febd2dfe` |
| `breero.shop` | PASS | PASS | PASS | PASS | PASS | PASS | `d44e8b650db401edd7de4f2b1bc61f24e92aabece2ca8e39a0984892d15d9462` |
| `codestra.agency` | PASS | PASS | PASS | PASS | PASS | PASS | `d2ad854f5b80b9b92467c5f5636d1b5e118031f088a75a46a36f989d7174a318` |
| `codestra.cloud` | PASS | PASS | PASS | PASS | PASS | PASS | `d232253586efe26797a0b8549dda962a8eabf077d3c8e0b76d0e4bce551f1259` |
| `codestra.co` | PASS | PASS | PASS | PASS | PASS | PASS | `43dd8484a546903f2c6b40643d9d40f14aa37578fc1a7552ebbbf02a56624aac` |
| `codestra.digital` | PASS | PASS | PASS | PASS | PASS | PASS | `604b731ef73a93312b4b23517809aee9bff49497e7a528db2cace7b5c158a422` |
| `codestra.media` | PASS | PASS | PASS | PASS | PASS | PASS | `7c56636adf796dae758bd08048802bddbe58eb717a92b9cf46c308b2f0516341` |
| `klyrow.com` | PASS | PASS | PASS | PASS | PASS | PASS | `455c2352a8b1bbb1ce92c5927d30b20f56dd6cdf8e020bbdd6b89bba5b63d890` |
| `kyqra.com` | PASS | PASS | PASS | PASS | PASS | PASS | `daf5ca88f4a8c293c9ee47aa88f1b616b6444c243dd233e07ce61fb9b2e1a58a` |
| `moneybee.loan` | PASS | PASS | PASS | PASS | PASS | PASS | `34624deb3086341eade85f1f0eb20b7d59c5e9abaf7cbb7f831ccfd794cee6a2` |
| `moneybeeloan.com` | PASS | PASS | PASS | PASS | PASS | PASS | `97ade73efe95149b97b03810525c7984fb7d584cc15665e87aebdd34f65c5b81` |
| `nativoenglish.com` | PASS | PASS | PASS | PASS | PASS | PASS | `31c00ac4087dc0d607d32c7b2b640335593a5c6f5d48b1a29df58f96424825fa` |
| `telnexa.co` | PASS | PASS | PASS | PASS | PASS | PASS | `ec0bc8b3d1fbb03fabeec352115b9de7cb9af9c011ff474922e88f93373b3ce6` |

Shared SMTP identity read-back:

- `mail.klyrow.com A 37.27.128.39`: PASS
- `37.27.128.39 PTR mail.klyrow.com`: PASS
- SMTP port 25 STARTTLS handshake: PASS
- certificate name `mail.klyrow.com`: PASS
- certificate-chain verification: PASS
- negotiated protocol/cipher: TLS 1.3 / `TLS_AES_256_GCM_SHA384`

This is current public-DNS and transport evidence, not permission to send.
`docs/SECURITY_SMTP_ACTIVATION.md` records a prior DKIM exposure concern. The
active-selector rotation history must be reconciled and any still-exposed key
rotated through the approved DNS procedure before `DOMAIN_POLICY=PASS` or live
mail certification. General external delivery remains disabled in the release
candidate.

`EMAIL_SENT_UNINTENTIONALLY=0`

`SSH_CHANGED=NO`
