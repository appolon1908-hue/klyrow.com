from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "docker/database-runtime.Dockerfile"
WORKFLOW = ROOT / ".github/workflows/database-runtime-ci.yml"
COMPOSE = ROOT / "docker-compose.yml"
DOC = ROOT / "docs/runtime/POSTGRES_HARDENED_RUNTIME.md"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_database_runtime_sources_are_digest_and_checksum_pinned() -> None:
    source = _source(DOCKERFILE)
    image_arguments = re.findall(
        r"^ARG\s+[A-Z_]+_IMAGE=([^\s]+)$",
        source,
        flags=re.MULTILINE,
    )
    assert len(image_arguments) == 2
    assert all(
        re.fullmatch(
            r"mirror\.gcr\.io/library/[a-z0-9-]+@sha256:[0-9a-f]{64}",
            image,
        )
        for image in image_arguments
    )
    assert (
        "ADD --checksum=sha256:"
        "cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164"
    ) in source
    assert "https://github.com/tianon/gosu/archive/refs/tags/1.19.tar.gz" in source
    assert ":latest" not in source
    assert " apt-get " not in source
    assert " apk " not in source
    assert " curl " not in source
    assert " wget " not in source


def test_gosu_build_is_reproducible_and_activated() -> None:
    source = _source(DOCKERFILE)
    for marker in (
        "CGO_ENABLED=0 go build",
        "-trimpath",
        "-buildvcs=false",
        "-ldflags='-d -w -buildid='",
        "touch -d \"@${SOURCE_DATE_EPOCH}\" /out/gosu",
        "COPY --from=gosu-builder --chmod=0755 /out/gosu /usr/local/bin/gosu",
        "test \"$(gosu --version | awk '{print $1}')\" = \"1.19\"",
        "gosu postgres sh -ceu",
    ):
        assert marker in source


def test_official_postgres_process_contract_is_inherited() -> None:
    source = _source(DOCKERFILE)
    final = source.split(" AS postgres-runtime", 1)[1]
    assert "test -x /usr/local/bin/docker-entrypoint.sh" in final
    assert (
        "test \"$(postgres --version | awk '{print $3}' | cut -d. -f1)\" = \"17\""
        in final
    )
    assert "17.6" not in final
    assert not re.search(r"^ENTRYPOINT\b", final, flags=re.MULTILINE)
    assert not re.search(r"^CMD\b", final, flags=re.MULTILINE)
    assert not re.search(r"^USER\b", final, flags=re.MULTILINE)
    assert not re.search(r"^VOLUME\b", final, flags=re.MULTILINE)
    assert "org.opencontainers.image.revision=\"${SOURCE_COMMIT_SHA}\"" in final


def test_current_compose_keeps_exact_external_digest_authority() -> None:
    compose = _source(COMPOSE)
    postgres = compose.split("  postgres:\n", 1)[1].split(
        "  gateway-migrate:\n", 1
    )[0]
    assert (
        "image: '${KLYROW_POSTGRES_IMAGE:?set the approved Postgres image by digest}'"
        in postgres
    )
    assert "build:" not in postgres
    assert "postgres_data:/var/lib/postgresql/data" in postgres
    assert "POSTGRES_PASSWORD_FILE: /run/secrets/klyrow_database_owner_password" in postgres
    assert "pg_isready -U klyrow -d klyrow" in postgres


def test_dedicated_ci_is_exact_head_non_publishing_and_complete() -> None:
    workflow = _source(WORKFLOW)
    for action_sha in (
        "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f",
        "docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8",
        "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610",
    ):
        assert action_sha in workflow
    for marker in (
        "ref: ${{ env.KLYROW_SOURCE_SHA }}",
        "persist-credentials: false",
        "target: postgres-runtime",
        "push: false",
        "POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password",
        "pg_isready -U klyrow -d klyrow",
        "docker stop --time 30",
        "Scan PostgreSQL candidate",
        "Generate PostgreSQL CycloneDX SBOM",
        "Verify reproducible PostgreSQL OCI bytes",
        "--provenance=false",
        "--sbom=false",
        "rewrite-timestamp=true",
        "cmp ",
        "cut -d. -f1",
        "= \"17\"",
    ):
        assert marker in workflow
    assert "17.6" not in workflow
    assert "docker/login-action" not in workflow
    assert "packages: write" not in workflow
    assert "type=registry" not in workflow


def test_historical_review_is_bounded_and_explicit() -> None:
    document = _source(DOC)
    for fingerprint in (
        "a54b14ff1eb74ae21069c72a5e9fd57347563f9b",
        "e401dae1bf814e29204a8cb7915682e1780951e609ca0dd8865ee1937f510c48",
        "051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0",
        "cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164",
    ):
        assert fingerprint in document
    assert "immutable base digest is the patch-level authority" in document.lower()
    assert "postgresql 17" in document.lower()
    assert "does not publish" in document.lower()
    assert "does not change `KLYROW_POSTGRES_IMAGE`" in document
    assert "no database volume is migrated" in document.lower()
