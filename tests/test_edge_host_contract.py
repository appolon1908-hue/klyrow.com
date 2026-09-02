from pathlib import Path


ROOT = Path(__file__).parents[1]


def _server_blocks(source: str) -> list[str]:
    blocks = []
    cursor = 0
    while True:
        start = source.find("server {", cursor)
        if start < 0:
            return blocks
        depth = 0
        for index in range(start + len("server "), len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start : index + 1])
                    cursor = index + 1
                    break
        else:
            raise AssertionError("unbalanced nginx server block")


def _https_block(source: str, hostname: str) -> str:
    matches = [block for block in _server_blocks(source) if "listen 443 ssl;" in block and f"server_name {hostname};" in block]
    assert len(matches) == 1, (hostname, len(matches))
    return matches[0]


def test_frontend_container_serves_only_the_canonical_application_host():
    source = (ROOT / "apps/web/nginx.conf").read_text(encoding="utf-8")
    assert "listen 8080 default_server;" in source
    assert "server_name app.klyrow.com;" in source
    assert "return 421;" in source
    assert 'X-Robots-Tag "noindex, nofollow"' in source
    assert "server_name app.klyrow.com api.klyrow.com" not in source
    assert "server_name track.codestra.co" not in source


def test_provider_edge_keeps_app_api_and_tracking_on_distinct_upstreams():
    source = (ROOT / "docker/proxy/klyrow.conf").read_text(encoding="utf-8")
    app = _https_block(source, "app.klyrow.com")
    api = _https_block(source, "api.klyrow.com")
    tracking = _https_block(source, "track.klyrow.com")
    bounce = _https_block(source, "bounce.klyrow.com")

    assert "proxy_pass http://klyrow_web;" in app
    assert "proxy_pass http://klyrow_gateway;" not in app
    assert "location = /mautic/api { return 404; }" in app
    assert "location ^~ /mautic/api/ { return 404; }" in app
    assert "location = /mautic/oauth { return 404; }" in app
    assert "location ^~ /mautic/oauth/ { return 404; }" in app
    assert app.index("location ^~ /mautic/api/") < app.index("location /mautic/")
    assert app.index("location ^~ /mautic/oauth/") < app.index("location /mautic/")
    assert "proxy_pass http://klyrow_gateway;" in api
    assert "proxy_pass http://klyrow_web;" not in api
    assert "location ^~ /t/" in tracking and "location / { return 404; }" in tracking
    assert "proxy_pass http://klyrow_web;" not in tracking
    assert "location / { return 404; }" in bounce
    assert "server_name track.codestra.co" not in source


def test_edge_activation_probe_covers_bff_and_wrong_host_failures():
    source = (ROOT / "scripts/verify-browser-edge").read_text(encoding="utf-8")
    for marker in ("/auth/session", "/auth/login", "track.codestra.co", "redirect_uri="):
        assert marker in source

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "scripts/verify-browser-edge" in workflow
    assert "LIVE_EMAIL_DELIVERY=false" in workflow
    assert "PRODUCTION_PROVIDER_ROUTING=false" in workflow
