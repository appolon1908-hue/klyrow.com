# Klyrow Provider Operations

Restricted operations expose health, bounded sandbox processing, message retry, event retry, and reconciliation. They require an authenticated platform-admin service identity and remain tenant-scoped. There is no generic root execution endpoint.

Reconciliation detects delivered messages missing capture, delivery event, or usage, plus stuck queue states. Operators investigate before retrying; idempotency and unique usage constraints prevent duplicate delivery records and double billing.
