# Odoo to Postal SMTP

Odoo on `65.109.65.169` must submit through Klyrow Postal. It must not deliver
directly to external MX hosts.

Configure the Odoo outgoing mail server with these exact non-secret values:

| Setting | Value |
|---|---|
| Description/service identifier | `odoo-production` |
| SMTP host | `mail.klyrow.com` |
| SMTP port | `25` |
| Connection security | `STARTTLS` |
| SMTP username | `klyrow/klyrow-production` |
| Authentication | Required |

The dedicated password is stored outside Git at
`/etc/klyrow/odoo-postal.env` on the Klyrow host. The file and its parent
directory are root-only (`0600` and `0700`). Transfer the password to the Odoo
operator through the approved secret channel and store it in Odoo's protected
credential store; never paste it into tickets, logs, shell history, or Git.

The credential is a Postal SMTP credential named `odoo-production` and is
cryptographically distinct from the Mautic credential. Authorized envelope and
header sender domains are limited to Postal-verified Klyrow domains, currently
`klyrow.com` and its subdomains. Do not authorize arbitrary customer or external
domains without completing Postal ownership verification and sender-policy
approval.

Host-local readiness is complete, but no Odoo authentication attempt or message
submission was made from `65.109.65.169`. The Odoo operator may validate login
and issue `NOOP`, ending the session before `MAIL FROM`/`DATA`. No external
canary may be sent until an explicitly approved recipient is supplied.

## Non-logging credential handoff

The approved `klyrow-deploy` identity may export only this credential through
the fixed helper:

```bash
sudo -n /usr/local/sbin/export-odoo-postal-credential
```

The root-owned helper accepts no arguments, reads only
`/etc/klyrow/odoo-postal.env`, requires a root-owned regular file with exact mode
`0600`, rejects missing, duplicate, or unrelated keys, and emits exactly the
five documented SMTP variables. `klyrow-deploy` cannot traverse `/etc/klyrow`
or run arbitrary sudo commands.

From the middleware/Odoo host, connect with the existing alias and pipe stdout
directly into the approved root-owned Odoo secret/configuration importer. Do not
capture it in command substitution, terminal output, shell tracing, logs, or an
unrestricted temporary file:

```bash
ssh -o BatchMode=yes klyrow-server \
  'sudo -n /usr/local/sbin/export-odoo-postal-credential' \
  | <approved-root-owned-odoo-secret-importer>
```

The exact Odoo importer/destination is intentionally not invented here. This
application server cannot authenticate to `65.109.65.169`, so remote import,
Odoo-origin STARTTLS authentication, and sender-policy verification remain an
Odoo-operator action. The verification session must contain only connect,
STARTTLS, AUTH, NOOP, and QUIT.

For the next separately authorized canary, Odoo must preserve the Klyrow
correlation ID in Postal's message tag (`X-Postal-Tag`) so native status webhook
payloads carry it without raw-header lookup. The first canary used
`X-Correlation-ID`; its historical failure reconciliation therefore supplied
that retained value explicitly. This does not authorize another message.
