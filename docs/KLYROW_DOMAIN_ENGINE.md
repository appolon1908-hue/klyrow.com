# Klyrow Domain Engine

Lifecycle states are `PENDING`, `DNS_REQUIRED`, `VERIFYING`, `VERIFIED`, `SENDING_ENABLED`, `SUSPENDED`, and `REMOVED`. A domain is globally unique across tenants and begins with an ownership challenge.

Execution checks exactly one SPF record containing the configured platform authorization, exact active DKIM, exactly one DMARC record, return-path, tracking hostname, and Klyrow MX when inbound is enabled. Missing external DNS results in `DNS_REQUIRED`; it never fabricates verification or blocks internal software certification.
