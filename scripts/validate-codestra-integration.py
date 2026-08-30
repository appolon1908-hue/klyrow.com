from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str) -> dict:
    path = ROOT / relative
    if not path.exists():
        raise AssertionError(f"missing required file: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        raise AssertionError(f"missing required file: {relative}")
    return path.read_text(encoding="utf-8")


def validate() -> None:
    manifest = read_json("codestra/integration/klyrow.integration.v1.json")
    middleware = read_json("codestra/integration/middleware-command-contract.v1.json")
    n8n = read_json("codestra/integration/n8n-orchestration.v1.json")
    aliases = read_json("codestra/integration/openbao-secret-aliases.v1.json")
    metrics = read_json("monitoring/klyrow-metrics-contract.v1.json")
    env = read_text("codestra/integration/runtime.env.example")
    target = read_text("monitoring/prometheus-target.disabled.yml")
    rules = read_text("monitoring/klyrow-recording-rules.yml")
    docs = read_text("docs/CODESTRA-INTEGRATION-FILES.md")

    assert manifest["schemaVersion"] == "1.0"
    assert manifest["application"] == "klyrow.com"
    assert manifest["status"] == "INTEGRATION_FILES_PREPARED_NOT_DEPLOYED"
    assert manifest["identity"]["browserSecretsAllowed"] is False
    assert manifest["gateway"]["directN8nAccessAllowed"] is False
    assert manifest["gateway"]["directOdooAccessAllowed"] is False
    assert manifest["gateway"]["directSmtpProviderAccessFromN8nAllowed"] is False
    assert manifest["smtp"]["directSmtpFromN8nAllowed"] is False
    assert manifest["smtp"]["directSmtpFromBrowserAllowed"] is False
    assert manifest["smtp"]["publicLiveDeliveryEnabledByDefault"] is False
    assert manifest["smtp"]["securitySmtpLiveEnabledByDefault"] is False
    assert manifest["productionGates"]["liveEmailDeliveryEnabled"] is False
    assert manifest["productionGates"]["n8nWorkflowsImported"] is False
    assert manifest["productionGates"]["n8nWorkflowsActive"] is False
    assert manifest["middleware"]["automationApi"]["commands"] == "POST /v2/automation/commands"

    for command in [
        "email.message.send.v1",
        "email.message.status.read.v1",
        "email.smtp.credential.create.v1",
        "email.smtp.credential.rotate.v1",
        "email.smtp.credential.revoke.v1",
        "email.delivery.replay.v1",
    ]:
        assert command in manifest["middleware"]["allowedCommands"]
        assert any(entry["type"] == command for entry in middleware["commands"])

    assert middleware["status"] == "PREPARED_NOT_DEPLOYED"
    assert middleware["invariants"]["n8nIsWriteAuthority"] is False
    assert middleware["invariants"]["smtpBypassesMiddlewareForAutomation"] is False
    assert "raw-smtp" in middleware["transport"]["forbiddenDirectTargets"]
    assert "postal-admin-api" in middleware["transport"]["forbiddenDirectTargets"]

    assert n8n["lane"] == "CP-KLYROW"
    assert n8n["n8n"]["role"] == "orchestrator"
    assert n8n["n8n"]["writeAuthority"] is False
    assert n8n["n8n"]["inactiveByDefault"] is True
    assert n8n["runtimeGate"]["productionTrafficAllowed"] is False
    assert any(entry["name"] == "CP-KLYROW-COMMON-ERROR" for entry in n8n["workflowGroups"])
    for http_target in n8n["n8n"]["allowedHttpTargets"]:
        assert http_target.startswith("https://api.codestra.co/v2/automation/")

    assert aliases["authority"] == "Codestra-OpenBao"
    assert aliases["gitMayContainSecretValues"] is False
    assert all(alias["name"].startswith("klyrow/") for alias in aliases["aliases"])

    assert metrics["status"] == "CONTRACT_PREPARED_NOT_SCRAPED"
    assert metrics["metricsEnabledByDefault"] is False
    for label in manifest["observability"]["requiredLabels"]:
        assert label in metrics["requiredLabels"]
        assert label in target
    for label in manifest["observability"]["forbiddenLabels"]:
        assert label in metrics["forbiddenLabels"]
        assert label in target

    for family in [
        "klyrow_http_requests_total",
        "klyrow_http_request_duration_seconds",
        "klyrow_mail_total",
        "klyrow_provider_queue_messages",
        "klyrow_integration_outbox_items",
    ]:
        assert any(entry["name"] == family for entry in metrics["metricFamilies"])

    for flag in [
        "KLYROW_SAFE_MODE=true",
        "KLYROW_N8N_ORCHESTRATION_ENABLED=false",
        "KLYROW_MIDDLEWARE_CANARY_ENABLED=false",
        "KLYROW_PROVIDER_LIVE_DELIVERY_ENABLED=false",
        "KLYROW_SECURITY_SMTP_ENABLED=false",
        "KLYROW_SECURITY_SMTP_LIVE_ENABLED=false",
        "LIVE_EMAIL_DELIVERY=false",
        "EXTERNAL_EMAIL_DELIVERY=false",
        "MARKETING_DELIVERY=false",
        "PRODUCTION_PROVIDER_ROUTING=false",
        "METRICS_ENABLED=false",
    ]:
        assert flag in env

    for forbidden in ["CLIENT_SECRET=", "ACCESS_TOKEN=", "REFRESH_TOKEN=", "SMTP_PASSWORD=", "API_KEY="]:
        assert forbidden not in env

    for fragment in [
        "klyrow:http_requests:rate5m",
        "klyrow:http_errors:ratio5m",
        "klyrow:integration_outbox:sum",
    ]:
        assert fragment in rules

    for fragment in [
        "Caddy",
        "Kong",
        "Middleware",
        "CP-KLYROW-COMMON-ERROR",
        "SMTP credentials are tenant scoped",
        "Activation Gates",
    ]:
        assert fragment in docs


if __name__ == "__main__":
    validate()
    print("Klyrow Codestra integration files validation PASS")
