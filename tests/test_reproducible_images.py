from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_python_image_does_not_embed_nondeterministic_bytecode():
    for relative_path in ("apps/gateway/Dockerfile", "docker/migrate.Dockerfile"):
        dockerfile = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile
        assert "pip install --no-cache-dir --no-compile --no-deps" in dockerfile
        assert "pip check" in dockerfile


def test_python_dependency_closure_is_exactly_pinned():
    requirements = (ROOT / "apps/gateway/requirements.txt").read_text(encoding="utf-8")
    specifications = [
        line.strip()
        for line in requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert specifications
    assert all("==" in specification for specification in specifications)
    assert "pydantic-core==2.46.5" in specifications
    assert "psycopg-binary==3.2.9" in specifications


def test_web_runtime_does_not_retain_nondeterministic_package_log():
    dockerfile = (ROOT / "apps/web/Dockerfile").read_text(encoding="utf-8")
    assert "apk upgrade" not in dockerfile


def test_every_container_build_stage_pins_its_base_manifest_digest():
    for relative_path in (
        "apps/gateway/Dockerfile",
        "apps/web/Dockerfile",
        "docker/migrate.Dockerfile",
        "docker/postal-provisioner.Dockerfile",
    ):
        dockerfile = (ROOT / relative_path).read_text(encoding="utf-8")
        from_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]
        assert from_lines
        assert all("@sha256:" in line for line in from_lines)
        assert "apk upgrade" not in dockerfile


def test_postal_runtime_is_patched_from_immutable_os_and_gem_inputs():
    dockerfile = (ROOT / "docker/postal-provisioner.Dockerfile").read_text(
        encoding="utf-8"
    )
    sources = (ROOT / "docker/postal-security/debian.sources.list").read_text(
        encoding="utf-8"
    )
    gemfile = (ROOT / "docker/postal-security/Gemfile").read_text(encoding="utf-8")
    lock = (ROOT / "docker/postal-security/Gemfile.lock").read_text(encoding="utf-8")
    assert sources.count("snapshot.debian.org/") == 3
    assert sources.count("20260901T000000Z") == 3
    assert "rm -f /etc/apt/sources.list.d/*" in dockerfile
    assert "apt-get dist-upgrade -y" in dockerfile
    os_patch_layer = dockerfile.split(
        "COPY docker/postal-security/Gemfile", maxsplit=1
    )[0]
    assert "rm -f" in os_patch_layer
    assert "/var/cache/ldconfig/aux-cache" in os_patch_layer
    assert "bundle config set deployment true" in dockerfile
    assert "bundle config set without 'development test'" in dockerfile
    assert "bundle clean --force" in dockerfile
    assert "/usr/local/bundle/gems/{activestorage-7.1.6" in dockerfile
    assert "-name gem_make.out -o -name mkmf.log" in dockerfile
    assert "find /opt/postal/app/vendor/bundle -type d -exec chmod 0755" in dockerfile
    assert "rm -rf /root/.bundle/cache" in dockerfile
    assert 'gem "rails", "= 7.2.3.2"' in gemfile
    assert 'gem "jwt", "= 2.10.3"' in gemfile
    assert 'gem "puma", "= 7.2.1"' in gemfile
    assert 'gem "zlib", "= 3.2.3"' in gemfile
    assert "CHECKSUMS" in lock
    assert "rails (7.2.3.2) sha256=" in lock
    assert "zlib (3.2.3) sha256=" in lock


def test_ci_compares_two_timestamp_rewritten_oci_exports_before_publish():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)" in workflow
    assert "Verify reproducible OCI image bytes" in workflow
    assert "for copy in a b" in workflow
    assert "for image in gateway web migrate postal-provisioner" in workflow
    assert '[migrate]="docker/migrate.Dockerfile"' in workflow
    assert '[postal-provisioner]="docker/postal-provisioner.Dockerfile"' in workflow
    assert "--no-cache" in workflow
    assert "type=oci,dest=${RUNNER_TEMP}/klyrow-${image}-${copy}.tar,rewrite-timestamp=true" in workflow
    assert "cmp \\\n" in workflow
    assert workflow.count("outputs: type=registry,rewrite-timestamp=true") == 4


def test_protected_publication_covers_every_production_owned_image():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "github.ref == 'refs/heads/main'" in workflow
    assert 'test "$(git rev-parse HEAD)" = "$KLYROW_SOURCE_SHA"' in workflow
    for image in ("gateway", "web", "migrate", "postal-provisioner"):
        assert f"klyrow-{image}:${{{{ env.KLYROW_SOURCE_SHA }}}}" in workflow
        assert f"klyrow-{image}" in workflow
    assert workflow.count("actions/attest-build-provenance@977bb373ede98d70efdf65b84cb5f73e068dcc2a") == 4


def test_pull_request_images_and_evidence_bind_to_exact_head_sha():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "KLYROW_SOURCE_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in workflow
    assert workflow.count("uses: actions/checkout@") == workflow.count(
        "ref: ${{ env.KLYROW_SOURCE_SHA }}"
    )
    assert workflow.count("github.sha") == 1
    assert "${{ github.sha }}" not in workflow
    assert "klyrow-gateway:${{ env.KLYROW_SOURCE_SHA }}" in workflow
    assert "org.opencontainers.image.revision=${{ env.KLYROW_SOURCE_SHA }}" in workflow
    assert "trivy-${{ env.KLYROW_SOURCE_SHA }}" in workflow
    assert "klyrow-gateway-${{ env.KLYROW_SOURCE_SHA }}.cdx.json" in workflow


def test_all_third_party_workflow_actions_are_commit_pinned():
    workflow = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
    )
    uses = [
        line.strip().split("uses:", 1)[1].strip().split()[0]
        for line in workflow.splitlines()
        if "uses:" in line
    ]
    assert uses
    assert all(len(reference.rsplit("@", 1)[1]) == 40 for reference in uses)
