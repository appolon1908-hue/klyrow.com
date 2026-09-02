from pathlib import Path

from openapi_spec_validator import validate

from apps.gateway.app.main import app


def test_required_production_routes_are_documented():
    paths = app.openapi()["paths"]
    required = {
        ("get", "/health/live"),
        ("get", "/health/ready"),
        ("get", "/v1/me/permissions"),
        ("get", "/v1/me/capabilities"),
        ("get", "/v1/me/sessions"),
        ("get", "/v1/organizations/{organization_id}"),
        ("get", "/v1/organizations/{organization_id}/members"),
        ("post", "/v1/organizations/{organization_id}/members"),
        ("patch", "/v1/organizations/{organization_id}/members/{member_id}"),
        ("get", "/v1/domains/{domain_id}"),
        ("patch", "/v1/domains/{domain_id}"),
        ("delete", "/v1/domains/{domain_id}"),
        ("get", "/v1/domains/{domain_id}/dns"),
        ("get", "/v1/domains/{domain_id}/verification"),
        ("post", "/v1/messages/{message_id}/cancel"),
        ("get", "/v1/templates/{template_id}"),
        ("patch", "/v1/templates/{template_id}"),
        ("delete", "/v1/templates/{template_id}"),
        ("get", "/v1/contacts/{contact_id}"),
        ("patch", "/v1/contacts/{contact_id}"),
        ("delete", "/v1/contacts/{contact_id}"),
        ("get", "/v1/lists"),
        ("post", "/v1/lists"),
        ("get", "/v1/lists/{list_id}"),
        ("patch", "/v1/lists/{list_id}"),
        ("delete", "/v1/lists/{list_id}"),
        ("patch", "/v1/campaigns/{campaign_id}"),
        ("post", "/v1/campaigns/{campaign_id}/schedule"),
        ("post", "/v1/campaigns/{campaign_id}/cancel"),
        ("get", "/v1/tracking/events"),
        ("get", "/v1/tracking/events/{event_id}"),
        ("get", "/v1/tracking/messages/{message_id}"),
        ("post", "/v1/suppressions"),
        ("delete", "/v1/suppressions/{suppression_id}"),
        ("get", "/v1/bounces"),
        ("get", "/v1/complaints"),
        ("get", "/v1/billing/account"),
        ("get", "/v1/billing/plans"),
        ("get", "/v1/operations"),
        ("get", "/v1/operations/{operation_id}/events"),
        ("get", "/v1/operations/{operation_id}/attempts"),
        ("post", "/v1/operations/{operation_id}/cancel"),
        ("post", "/v1/operations/{operation_id}/reconcile"),
        ("get", "/v1/providers/postal/health"),
        ("get", "/v1/providers/postal/status"),
        ("post", "/v1/integrations/mautic/commands"),
        ("get", "/v1/integrations/mautic/operations"),
        ("get", "/v1/integrations/mautic/operations/{operation_id}"),
        ("post", "/v1/integrations/mautic/operations/{operation_id}/reconcile"),
        ("get", "/v1/system/capabilities"),
        ("get", "/v1/system/readiness"),
    }
    missing = sorted(f"{method.upper()} {path}" for method, path in required if method not in paths.get(path, {}))
    assert missing == []


def test_canonical_openapi_is_structurally_valid():
    validate(app.openapi())


def test_established_canonical_aliases_remain_documented():
    paths = app.openapi()["paths"]
    for method, path in {
        ("post", "/v1/messages"),
        ("get", "/v1/messages"),
        ("get", "/v1/messages/{mid}"),
        ("get", "/v1/email/{mid}/events"),
        ("post", "/v1/auth/logout"),
        ("get", "/v1/billing/usage"),
        ("get", "/v1/billing/invoices"),
    }:
        assert method in paths[path]


def test_production_migration_is_required_by_the_model():
    migration = Path("migrations/2026090201_full_platform_api.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS contact_lists" in migration
    assert "integration_outbox_state_known" in migration
    attachments = Path("migrations/2026090202_webmail_attachments.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS webmail_attachments" in attachments
    assert "octet_length(content) = size" in attachments
    result_authority = Path("migrations/2026090203_integration_result_authority.sql").read_text()
    assert "uq_integration_result_source_key" in result_authority
    assert "UNIQUE (tenant_id, source, result_key)" in result_authority
