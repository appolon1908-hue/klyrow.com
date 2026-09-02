from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_secret_scan_policy_allows_only_exact_non_secret_values():
    policy = (ROOT / ".gitleaks.toml").read_text(encoding="utf-8")

    assert "paths =" not in policy
    assert "commits =" not in policy
    assert "[extend]" in policy
    assert "useDefault = true" in policy
    assert "[allowlist]" in policy
    assert "[[allowlists]]" not in policy
    assert "invite_capability_0123456789abcdef" in policy
    assert "1198C0117593497A5EC5C199286AF1F9897469DC" in policy
    assert "C28D937575603EB4ABB725861C0779DC5C0A9DE4" in policy
    assert "AFD8691FDAEDF03BDF6E460563F15A9B715376CA" in policy
