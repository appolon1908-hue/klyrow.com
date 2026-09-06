"""Mutation authorization must precede tenant lookup, writes, and external calls."""
import inspect

import pytest
from fastapi import HTTPException

from test_middleware_email_contract import gateway
from apps.gateway.app import messaging, production_api, provider


MUTATIONS = [
    (production_api, name) for name in ("list_create", "list_patch", "list_delete", "template_patch", "template_delete")
] + [
    (messaging, name) for name in ("domain_claim", "domain_verify", "dkim_rotate", "sender_create",
        "template_create", "template_update", "template_rollback", "template_publish",
        "campaign_create", "campaign_test", "campaign_schedule", "campaign_cancel")
] + [
    (provider, name) for name in ("domain_register", "domain_verify", "domain_dns_check",
        "domain_suspend", "dkim_verify", "sender_create", "sender_suspend",
        "smtp_credential_rotate", "smtp_credential_revoke")
]


@pytest.mark.parametrize("role", ["READ_ONLY", "ANALYST", "BILLING", "service"])
@pytest.mark.parametrize("module,name", MUTATIONS, ids=[m.__name__.split(".")[-1]+"."+n for m,n in MUTATIONS])
def test_missing_capability_is_denied_before_access(module, name, role):
    function = getattr(module, name)
    # Invalid state inputs deliberately fail if the permission check is late.
    arguments = {name: None for name, parameter in inspect.signature(function).parameters.items()
                 if parameter.default is inspect.Parameter.empty}
    arguments.update(ctx={"role": role, "permissions": ["mail.read"], "tenant": "tenant-a", "sub": "reader"}, s=None)
    with pytest.raises(HTTPException) as denied:
        function(**arguments)
    assert denied.value.status_code == 403


def test_list_http_crud_requires_explicit_grant_and_keeps_tenant_isolation(gateway):
    client, _, context = gateway
    context.update(role="service", permissions=["mail.read"])
    assert client.post("/v1/lists", json={"name": "Contacts"}).status_code == 403
    context["permissions"] = ["contact.manage"]
    created = client.post("/v1/lists", json={"name": "Contacts"})
    assert created.status_code == 201, created.text
    path = "/v1/lists/" + created.json()["id"]
    context["tenant"] = "tenant-b"
    assert client.patch(path, json={"name": "Hijacked"}).status_code == 404
    assert client.delete(path).status_code == 404
    context["tenant"] = "tenant-a"
    context["permissions"] = ["mail.read"]
    assert client.patch(path, json={"name": "Hijacked"}).status_code == 403
    assert client.delete(path).status_code == 403
    assert client.get(path).json()["name"] == "Contacts"
    context["permissions"] = ["contact.manage"]
    assert client.patch(path, json={"name": "Updated"}).status_code == 200
    assert client.delete(path).status_code == 204


@pytest.mark.parametrize("path", ["/v1/domains/claims", "/v1/internal/email/domains/register"])
def test_domain_http_creation_requires_domain_capability(gateway, path):
    client, _, context = gateway
    context.update(role="service", permissions=["mail.send"])
    assert client.post(path, json={"domain": "scope.example"}).status_code == 403
    context["permissions"] = ["domain.manage"]
    response = client.post(path, json={"domain": "scope.example"})
    assert response.status_code == 201, response.text
