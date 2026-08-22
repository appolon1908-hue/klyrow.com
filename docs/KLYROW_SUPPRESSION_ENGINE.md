# Klyrow Suppression Engine

Preflight checks tenant-recipient suppressions before queueing. Hard bounce and complaint normalization create or update suppression state idempotently. Marketing additionally requires affirmative consent from the authoritative control-plane request; absent consent fails closed.

Transactional, security, and system traffic remain separate from marketing consent, while hard-bounce and complaint safety suppression applies across streams according to provider policy.
