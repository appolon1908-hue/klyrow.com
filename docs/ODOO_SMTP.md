# Odoo to Postal SMTP

Required architecture: Odoo on `65.109.65.169` submits to Klyrow/Postal on `37.27.128.39`; Odoo must not deliver directly to external MX hosts.

A dedicated least-privilege Postal SMTP credential must be created for Odoo and stored outside Git. It must not reuse the Mautic credential, Postal administrator credential, middleware API key, or Klyrow API key. Validate authentication with an SMTP session ending before message submission until every deliverability gate passes.

No Odoo service or SMTP configuration is present on the Klyrow host. Access to the documented Odoo host and its credential store was not available during this run, so Odoo authentication remains blocked and no credential was created or exposed. The production canary also remains blocked. No external message was sent.
