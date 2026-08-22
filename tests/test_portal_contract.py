from pathlib import Path

from fastapi.testclient import TestClient

from apps.gateway.app.main import app


ROOT=Path(__file__).parents[1]
client=TestClient(app)


def test_canonical_message_route_is_in_openapi():
    schema=client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/v1/messages"]
    assert "/v1/email/send" not in schema["paths"]


def test_portal_uses_canonical_route_and_send_gate_contract():
    script=(ROOT/"apps/gateway/app/portal.js").read_text()
    assert 'api("/v1/messages"' in script
    assert "g.sending_enabled" in script
    assert 'aria-current' in script


def test_portal_has_keyboard_and_live_region_foundations():
    page=(ROOT/"apps/gateway/app/portal.html").read_text()
    assert page.count("<body>")==1 and page.count("</body>")==1
    assert 'href="#main-content"' in page
    assert 'id="main-content" tabindex="-1"' in page
    assert page.count('aria-live="assertive"')>=2
    assert 'aria-current="page"' in page
    assert '@media(max-width:820px)' in page
