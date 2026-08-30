import ast
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "apps" / "gateway" / "app"
SMTP_MANIFEST = ROOT / "codestra" / "integration" / "klyrow-smtp.integration.v1.json"
METRICS_CONTRACT = ROOT / "monitoring" / "klyrow-smtp-metrics-contract.v1.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def python_trees():
    for path in sorted(APP_ROOT.rglob("*.py")):
        yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def literal_strings(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.add(child.value)
    return values


def static_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_string(node.left)
        right = static_string(node.right)
        if left is not None and right is not None:
            return left + right
        if left is not None:
            return left + "<dynamic>"
        if right is not None:
            return "<dynamic>" + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("<dynamic>")
        return "".join(parts)
    return None


def discover_emit_middleware_events() -> set[str]:
    events: set[str] = set()
    for _path, tree in python_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or call_name(node.func) != "emit_middleware":
                continue
            if not node.args:
                events.add("<missing-event-argument>")
                continue
            events.add(static_string(node.args[0]) or "<dynamic-event>")
    return events


def discover_route_paths() -> set[str]:
    routes: set[str] = set()
    for _path, tree in python_trees():
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                route = decorator.args[0] if decorator.args else None
                if route is not None:
                    value = static_string(route)
                    if value and value.startswith("/"):
                        routes.add(value)
    return routes


def discover_status_values() -> set[str]:
    statuses: set[str] = set()
    for _path, tree in python_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = {getattr(target, "id", None) for target in node.targets}
                if "TERMINAL_MESSAGE_STATUSES" in targets or "MESSAGE_STATES" in targets:
                    statuses.update(value.lower() for value in literal_strings(node.value))
            if isinstance(node, ast.keyword) and node.arg == "status":
                statuses.update(value.lower() for value in literal_strings(node.value))
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "status":
                        statuses.update(value.lower() for value in literal_strings(node.value))
    return statuses


def discover_emit_middleware_headers() -> set[str]:
    for _path, tree in python_trees():
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function.name != "emit_middleware":
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.Assign):
                    continue
                if not any(isinstance(target, ast.Name) and target.id == "headers" for target in node.targets):
                    continue
                if isinstance(node.value, ast.Dict):
                    return {
                        key.value
                        for key in node.value.keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    }
    return set()


def discover_prometheus_collectors() -> dict[str, set[str]]:
    collectors: dict[str, set[str]] = {}
    collector_types = {"Counter", "Gauge", "Histogram", "Summary", "Info"}
    for _path, tree in python_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or call_name(node.func) not in collector_types:
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            name = node.args[0].value
            if not isinstance(name, str):
                continue
            labels: set[str] = set()
            if len(node.args) >= 3:
                labels.update(literal_strings(node.args[2]))
            for keyword in node.keywords:
                if keyword.arg in {"labelnames", "labels"}:
                    labels.update(literal_strings(keyword.value))
            collectors[name] = labels
    return collectors


@pytest.mark.xfail(strict=True, reason="C1: declared SMTP events do not match events emitted by the app yet")
def test_smtp_published_events_match_emitters():
    manifest = load_json(SMTP_MANIFEST)

    declared = set(manifest["events"]["publishedEvents"])
    emitted = discover_emit_middleware_events()

    assert emitted == declared


@pytest.mark.xfail(strict=True, reason="C2: Klyrow has not implemented the inbound Middleware command API yet")
def test_middleware_command_contract_has_runtime_routes_and_handlers():
    manifest = load_json(SMTP_MANIFEST)
    source_literals = set()
    for _path, tree in python_trees():
        source_literals.update(literal_strings(tree))

    routes = discover_route_paths()
    assert "/v1/commands" in routes
    assert "/v1/operations/{command_id}" in routes
    assert set(manifest["middleware"]["allowedCommands"]) <= source_literals


@pytest.mark.xfail(strict=True, reason="C3: runtime status values still differ from the canonical SMTP status model")
def test_runtime_message_statuses_match_smtp_status_model():
    manifest = load_json(SMTP_MANIFEST)

    declared = set(manifest["events"]["statusModel"])
    runtime = discover_status_values()

    assert runtime == declared


@pytest.mark.xfail(strict=True, reason="C4: outbound Middleware calls do not send all required command headers yet")
def test_emit_middleware_sends_required_headers():
    manifest = load_json(SMTP_MANIFEST)

    required = set(manifest["middleware"]["requiredHeaders"])
    emitted = discover_emit_middleware_headers()

    assert required <= emitted


def test_prometheus_collectors_do_not_use_forbidden_labels():
    metrics = load_json(METRICS_CONTRACT)
    forbidden = set(metrics["forbiddenLabels"])

    collectors = discover_prometheus_collectors()
    violations = {
        metric: sorted(labels & forbidden)
        for metric, labels in collectors.items()
        if labels & forbidden
    }

    assert violations == {}


@pytest.mark.xfail(strict=True, reason="C5: SMTP collectors have not been normalized onto required platform labels yet")
def test_prometheus_collectors_include_required_platform_labels():
    metrics = load_json(METRICS_CONTRACT)
    required = set(metrics["requiredLabels"])

    collectors = discover_prometheus_collectors()
    missing = {
        metric: sorted(required - labels)
        for metric, labels in collectors.items()
        if required - labels
    }

    assert missing == {}
