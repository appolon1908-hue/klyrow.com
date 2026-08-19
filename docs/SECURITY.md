# Security

Secrets are generated into ignored `.env`/`secrets`, never images or Git. Passwords use Argon2; API keys are hashed; webhook signatures use HMAC-SHA256 and constant-time comparison with replay persistence. Public APIs require authentication, RBAC and tenant filters. Databases, RabbitMQ, Mautic and Grafana are not directly public. Containers use least privilege where upstream images permit it.

Rotate API, webhook, database, Postal, session and Grafana secrets independently. Back up before rotation. Protect the host Nginx and SSH configuration, allow SSH from trusted networks, and firewall SMTP/web ports narrowly. Review dependencies and pinned images routinely. Report vulnerabilities privately to the repository owner; do not include production secrets or customer data.

TOTP secrets stay server-side and recovery codes only as hashes. Sessions are revocable. Marketing requires recorded consent and current preference; suppressions override every stream. Personalization escapes values and rejects scripts, event handlers, embedded active content and JavaScript URLs. Two independent environment controls prevent one configuration mistake from enabling delivery.
