# Email event worker rollback

The pre-change snapshot is stored under the root-only
`/root/klyrow-backups/email-reseller-20260816T074929Z` directory.

1. Keep `KLYROW_SAFE_MODE=true` and
   `KLYROW_PRODUCTION_GATE_APPROVED=false`.
2. Restore only `apps/gateway/app/main.py` and, if required, the matching
   Compose file from the snapshot. Do not restore database contents unless a
   separately approved data rollback is required.
3. Validate with `python3 -m py_compile`, `docker compose config --quiet`, the
   focused gateway tests, and `git diff --check`.
4. Rebuild and recreate only `gateway` with `--no-deps`.
5. Require private health on `10.40.0.4:18000`, Postal management on loopback,
   both delivery gates disabled, and zero new Postal messages.

The PostgreSQL snapshot is included for disaster recovery. Normal code
rollback must preserve provider events, suppression rows, audit records, and
the retry/DLQ history created after deployment.
