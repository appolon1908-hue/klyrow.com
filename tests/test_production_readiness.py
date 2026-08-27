from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_runtime_secret_bootstrap_never_prints_credentials():
    script = (ROOT / "scripts/generate-env").read_text()
    assert '[[ "$EUID" -eq 0 ]]' in script
    assert "KLYROW_RUNTIME_SECRET_DIR:-/etc/klyrow/secrets" in script
    assert 'install -o root -g root -m 0600' in script
    assert "KLYROW_SESSION_SECRET_FILE=$runtime_secret_dir/session-secret" in script
    assert "KLYROW_POSTAL_API_KEY_FILE=$runtime_secret_dir/postal-api-key" in script
    assert "KLYROW_METRICS_TOKEN_FILE=$runtime_secret_dir/metrics-token" in script
    assert "Initial admin password:" not in script
    assert "chown root:root .env" in script


def test_schema_migration_is_a_required_gateway_dependency():
    compose = (ROOT / "docker-compose.yml").read_text()
    runner = (ROOT / "scripts/migrate").read_text()
    assert "gateway-migrate: {condition: service_completed_successfully}" in compose
    assert "2026082701_mail_operations_remediation.sql" in compose
    assert "docker/migrate.Dockerfile" in compose
    assert "pg_advisory_xact_lock" in runner
    assert "applied migration checksum mismatch" in runner
    canary = (ROOT / "migrations/2026082202_production_canary_claim_ledger.sql").read_text()
    assert "ALTER COLUMN updated_at SET DEFAULT now()" in canary
    assert "claimed_deliveries, updated_at" in canary
    legacy = (ROOT / "migrations/0000_legacy_schema_compat.sql").read_text()
    assert "RENAME COLUMN domain_id TO domain_claim_id" in legacy
    assert "RENAME COLUMN secret_hash TO verifier_hash" in legacy


def test_mail_worker_has_the_canonical_mtls_event_delivery_contract():
    compose = (ROOT / "docker-compose.yml").read_text()
    worker = compose.split("  worker:", 1)[1].split("  scheduler:", 1)[0]
    assert "KLYROW_EMAIL_EVENT_URL: https://middleware-email-events.internal.codestra.agency:18080/internal/provider-events/klyrow" in worker
    assert "KLYROW_SERVER_A_CA_FILE: /run/codestra-mtls/server-a/root-ca.crt" in worker
    assert "KLYROW_SERVER_A_CLIENT_CERT_FILE: /run/codestra-mtls/server-a/client-fullchain.crt" in worker
    assert "KLYROW_SERVER_A_CLIENT_KEY_FILE: /run/codestra-mtls/server-a/client.key" in worker
    assert "/etc/codestra/mtls/server-a-event-client:/run/codestra-mtls/server-a:ro" in worker


def test_upgrade_migrates_legacy_environment_secrets_before_compose():
    update = (ROOT / "scripts/update").read_text()
    deploy = (ROOT / "scripts/deploy").read_text()
    migration = (ROOT / "scripts/migrate-runtime-secrets").read_text()
    assert "scripts/migrate-runtime-secrets" in update
    assert "scripts/migrate-runtime-secrets" in deploy
    assert 'os.geteuid() != 0' in migration
    assert 'os.chmod(target, 0o600)' in migration
    assert 'removed = set(specs)' in migration


def test_outbox_recovers_abandoned_sending_leases():
    source = (ROOT / "apps/gateway/app/main.py").read_text()
    assert 'EmailOutbox.state=="sending"' in source
    assert "EmailOutbox.updated_at<stale" in source
    assert 'postal_headers(transport,"klyrow:"+snapshot[1])' in source


def test_outbox_retries_back_off_and_terminal_failure_updates_message():
    source = (ROOT / "apps/gateway/app/main.py").read_text()
    migration = (ROOT / "migrations/2026082201_email_outbox_and_tenant_idempotency.sql").read_text()
    assert "EmailOutbox.next_attempt_at<=current" in source
    assert "failed=item.attempts>=5" in source
    assert "if first_attempt:" in source
    assert "min(300,2**max(item.attempts,1))" in source
    assert 'message.status="failed"' in source
    assert 'kind="klyrow.email.failed"' in source
    assert "next_attempt_at timestamptz" in migration


def test_single_domain_canary_is_durable_and_fail_closed():
    source = (ROOT / "apps/gateway/app/main.py").read_text()
    migration = (ROOT / "migrations/2026082201_email_outbox_and_tenant_idempotency.sql").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "canary_configuration_valid()" in source
    assert 'KLYROW_CANARY_ALLOWED_CAMPAIGN' in source
    assert 'with_for_update()' in source
    assert 'production_canary_limit_reached' in source
    assert 'bulk_delivery_disabled_during_canary' in source
    assert 'campaign_delivery_disabled_during_canary' in source
    assert 'production_canary_gate' in migration
    assert 'canary_payload_allowed(payload)' in source
    assert 'payload.get("campaign_id")==allowed_campaign' in source
    assert '"campaign_id":x.campaign_id' in source
    assert 'item.state="quarantined"' in source
    assert 'gate.claimed_deliveries+=1' in source
    assert 'claimed_deliveries integer NOT NULL DEFAULT 0' in migration
    assert 'invalid_outbox_payload' in source
    assert 'normalized_recipients' in source
    assert 'except (TypeError,ValueError):maximum=-1' in source
    assert "KLYROW_CANARY_MAX_DELIVERIES" in compose
    assert 'KLYROW_BULK_DELIVERY_ENABLED: "false"' in compose


def test_resolver_requires_write_permission_for_mutating_routes():
    source = (ROOT / "apps/gateway/app/main.py").read_text()
    assert 'request.method not in {"GET","HEAD","OPTIONS"}' in source
    assert 'permission="klyrow.webhook" if "webhook" in request.url.path else "klyrow.send"' in source


def test_health_counts_outbox_and_reflects_durable_canary_capacity():
    source = (ROOT / "apps/gateway/app/main.py").read_text()
    assert "select(func.count()).select_from(EmailOutbox)" in source
    assert "gate.reserved_deliveries<maximum" in source
    assert "production_gate_open(s)" in source


def test_prometheus_uses_the_private_metrics_credential():
    compose = (ROOT / "docker-compose.yml").read_text()
    prometheus = (ROOT / "config/prometheus.yml").read_text()
    assert "secrets: [klyrow_metrics_token]" in compose
    assert "credentials_file: /run/secrets/klyrow_metrics_token" in prometheus
    alerts=(ROOT/"config/alerts.yml").read_text()
    for name in ("KlyrowEmailQueueStalled","KlyrowN8nDeliveryStalled","KlyrowOdooDeliveryStalled","KlyrowCustomerWebhookFailures","KlyrowHighBounceRate","KlyrowHighComplaintRate","KlyrowDomainDnsInvalid","KlyrowBillingReconciliationFailure","KlyrowHostCpuPressure","KlyrowHostMemoryPressure"):
        assert "alert: "+name in alerts


def test_container_scan_fails_only_for_configured_high_and_critical_findings():
    workflow=(ROOT/".github/workflows/ci.yml").read_text()
    assert "severity: CRITICAL,HIGH" in workflow
    assert "limit-severities-for-sarif: true" in workflow
    assert 'exit-code: "1"' in workflow
