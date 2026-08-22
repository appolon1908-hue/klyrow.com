# Klyrow Provider Rollback

Deployments use source SHA and exact image digest. Before deployment, retain encrypted backups and the prior release manifest/image digest. Rollback replaces only Klyrow gateway/SMTP services, never Postal data or out-of-scope services unless the reviewed recovery plan explicitly requires it.

Forward-only schema additions remain compatible with the prior application. After rollback verify gateway, Postal, databases, RabbitMQ, safe mode, queue reconciliation, and the complete Telnexa/Jasmin/billing fingerprint. Do not roll back by deleting mail data.
