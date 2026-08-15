# Odoo to Postal SMTP

Required architecture: Odoo on `65.109.65.169` submits to Klyrow/Postal on `37.27.128.39`; Odoo must not deliver directly to external MX hosts.

A dedicated least-privilege Postal SMTP credential must be created for Odoo and stored outside Git. It must not reuse the Mautic credential, Postal administrator credential, middleware API key, or Klyrow API key. Validate authentication with an SMTP session ending before message submission until every deliverability gate passes.

This run did not create or configure that credential because the Postal server rejected all available SSH identities. Odoo authentication and the production canary remain blocked. No external message was sent.
