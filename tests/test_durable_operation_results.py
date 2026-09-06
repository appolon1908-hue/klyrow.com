"""Synthetic result/claim invariants; PostgreSQL cases run in required CI."""
from __future__ import annotations

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.orm import sessionmaker

from apps.gateway.app.durable_keys import KEYRING_ENV, KeyringError, load_keyring, parse_keyring
from apps.gateway.app.durable_results import (
    FORMAT, canonical, integration_document, read_control_response, redact_result,
    result_matches, result_readback, seal_control_response, seal_integration_result,
)
from apps.gateway.app.main import Base, Idempotency, Tenant
from apps.gateway.app.mautic_adapter import MauticAdapterState, _claim, _failure, _success
from apps.gateway.app.operations import IntegrationOutbox, IntegrationResult, ResultIn, result as accept_result
from apps.gateway.app.production_api import _operation_json, operation_cancel, operation_reconcile


CTX = {"tenant": "tenant-a", "sub": "operator-a", "role": "MARKETING"}


def store_control(value):
    row = SimpleNamespace(tenant_id="tenant-a", key="scoped-key-a", request_hash="hash-a", resource_id="operation-a")
    row.response_json = seal_control_response(value, tenant_id=row.tenant_id, storage_key=row.key,
                                              request_hash=row.request_hash, resource_id=row.resource_id)
    return row


def test_control_response_is_encrypted_and_independent_of_browser_rotation(monkeypatch):
    row = store_control({"status": "CANCELLED", "original": "synthetic-sensitive-result"})
    assert "synthetic-sensitive-result" not in row.response_json
    monkeypatch.setenv("KLYROW_SESSION_SECRET", "a-different-session-secret" * 4)
    assert read_control_response(row)["original"] == "synthetic-sensitive-result"


@pytest.mark.parametrize("field", ["tenant_id", "key", "request_hash", "resource_id"])
def test_ciphertext_cannot_move_between_identity_bindings(field):
    row = store_control({"status": "CANCELLED"})
    setattr(row, field, "different-identity")
    with pytest.raises(HTTPException) as error:
        read_control_response(row)
    assert (error.value.status_code, error.value.detail) == (503, "durable_result_unavailable")


def test_rotation_reads_previous_key_and_unknown_key_does_not_fall_back(isolated_durable_result_keyring):
    path = isolated_durable_result_keyring
    old = store_control({"status": "CANCELLED"})
    keys = json.loads(path.read_text())
    previous_id = keys["active_key_id"]
    keys["keys"]["next"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
    keys["active_key_id"] = "next"
    path.write_text(json.dumps(keys))
    assert read_control_response(old) == {"status": "CANCELLED"}
    current = store_control({"status": "QUEUED"})
    assert json.loads(current.response_json)["kid"] == "next"
    del keys["keys"][previous_id]
    path.write_text(json.dumps(keys))
    with pytest.raises(HTTPException):
        read_control_response(old)
    assert read_control_response(current)["status"] == "QUEUED"


@pytest.mark.parametrize("damage", ["ciphertext", "nonce", "kid", "format"])
def test_damaged_envelope_never_becomes_a_new_request(damage):
    row = store_control({"status": "CANCELLED"})
    value = json.loads(row.response_json)
    value[damage] = "not-valid"
    row.response_json = json.dumps(value)
    with pytest.raises(HTTPException):
        read_control_response(row)


def test_missing_key_has_no_session_key_or_plaintext_fallback(monkeypatch):
    monkeypatch.delenv(KEYRING_ENV)
    with pytest.raises(HTTPException):
        store_control({"status": "CANCELLED"})


@pytest.mark.parametrize("kind", ["symlink", "directory", "writable", "oversized", "relative"])
def test_invalid_key_files_fail_closed(tmp_path, kind):
    path = tmp_path / "bad"
    if kind == "symlink":
        path.symlink_to(tmp_path / "missing")
    elif kind == "directory":
        path.mkdir()
    else:
        path.write_text("x" * (9000 if kind == "oversized" else 1))
        path.chmod(0o666 if kind == "writable" else 0o600)
    with pytest.raises(KeyringError):
        load_keyring("relative.json" if kind == "relative" else path)


def test_duplicate_key_identifiers_fail_closed():
    with pytest.raises(KeyringError):
        parse_keyring(b'{"schema_version":1,"active_key_id":"a","keys":{"a":"x","a":"y"}}')


def test_legacy_compatibility_is_read_only_and_can_be_disabled(monkeypatch):
    row = SimpleNamespace(tenant_id="a", key="b", request_hash="c", resource_id="d", response_json='{"ok":true}')
    assert read_control_response(row) == {"ok": True}
    monkeypatch.setenv("KLYROW_DURABLE_RESULT_LEGACY_READ_ENABLED", "false")
    with pytest.raises(HTTPException):
        read_control_response(row)


def result_row(payload=None, **changes):
    attrs = dict(id="result-a", tenant_id="tenant-a", outbox_id="operation-a", source="MAUTIC",
                 result_key="mautic:operation-a", created_at=datetime.now(timezone.utc))
    attrs.update(changes)
    row = IntegrationResult(**attrs)
    row.payload_json = seal_integration_result(payload or {"contacts": {"total": 1}}, tenant_id=row.tenant_id,
                                              outbox_id=row.outbox_id, source=row.source, result_key=row.result_key)
    return row


def test_nested_provider_secrets_are_redacted_and_storage_is_encrypted():
    original = {"contacts": {"total": 1}, "nested": [{"access_token": "token-value", "email": "private@example.test"}],
                "private-key": "key-value", "reset_url": "https://example.test/secret"}
    row = result_row(original)
    assert all(secret not in row.payload_json for secret in ("token-value", "private@example.test", "key-value"))
    payload, metadata = result_readback(row)
    assert metadata["availability"] == "AVAILABLE"
    assert payload["contacts"]["total"] == 1
    assert payload["nested"][0] == {"access_token": "[REDACTED]", "email": "[REDACTED]"}
    assert result_matches(row, original)
    assert not result_matches(row, {**original, "private-key": "changed"})


@pytest.mark.parametrize("kind", ["absent", "corrupt", "expired", "invalid-retention"])
def test_missing_or_unusable_result_has_explicit_status(monkeypatch, kind):
    row = result_row()
    if kind == "absent": row = None
    if kind == "corrupt": row.payload_json = "not-json"
    if kind == "expired": row.created_at -= timedelta(days=31)
    if kind == "invalid-retention": monkeypatch.setenv("KLYROW_RESULT_RETENTION_SECONDS", "-1")
    payload, metadata = result_readback(row)
    assert payload == {}
    assert metadata["availability"] == {"absent": "UNAVAILABLE", "corrupt": "INVALID", "expired": "EXPIRED", "invalid-retention": "INVALID"}[kind]


def test_oversized_and_deep_results_are_rejected():
    with pytest.raises(ValueError): canonical({"value": "x" * 65536})
    value = {}
    for _ in range(15): value = {"nested": value}
    with pytest.raises(ValueError): redact_result(value)


@pytest.fixture
def operation_db():
    url = os.getenv("KLYROW_CONTRACT_POSTGRES_URL")
    admin = None
    if url:
        schema = "durable_" + uuid.uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection: connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as session:
        session.add(Tenant(id="tenant-a", name="Synthetic", quota=100))
        session.commit()
    try: yield sessions
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection: connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def operation(state="PROCESSING", attempts=1, **changes):
    attrs = dict(id="operation-a", tenant_id="tenant-a", target="MAUTIC", event_type="campaign.publish.v1",
                 aggregate_id="campaign-a", payload_json='{"envelope":{"correlation_id":"original-correlation"}}',
                 idempotency_key="storage-digest-not-correlation", state=state, attempts=attempts,
                 lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=1))
    attrs.update(changes)
    return IntegrationOutbox(**attrs)


@pytest.mark.parametrize("state,attempt,expected", [("CANCELLED",1,1),("PROCESSING",2,1),("DEAD_LETTER",1,1)])
def test_stale_completion_retains_state_and_records_only_one_observation(operation_db, state, attempt, expected):
    with operation_db() as session:
        item = operation(state, attempt)
        session.add(item); session.commit()
        assert _success(session, item.id, {"ok":True}, expected_attempt=expected) is False
        assert _success(session, item.id, {"ok":True}, expected_attempt=expected) is False
        session.refresh(item)
        assert (item.state, item.attempts) == (state, attempt)
        assert session.scalar(select(func.count()).select_from(IntegrationResult)) == 1
        assert session.scalar(select(IntegrationResult.source)) == "MAUTIC_LATE"


def test_stale_failure_cannot_modify_new_claim_or_circuit(operation_db):
    with operation_db() as session:
        item = operation(attempts=2)
        session.add(item); session.commit()
        assert _failure(session,item.id,"old error",retryable=True,expected_attempt=1) is False
        assert item.state == "PROCESSING" and item.attempts == 2
        assert session.get(MauticAdapterState,"primary") is None


def test_valid_claim_completes_once_with_private_result(operation_db):
    with operation_db() as session:
        item = operation()
        session.add(item); session.commit()
        assert _success(session,item.id,{"count":1,"api_key":"private"},expected_attempt=1) is True
        assert _success(session,item.id,{"count":1},expected_attempt=1) is False
        assert item.state == "COMPLETED"
        result = session.scalar(select(IntegrationResult))
        assert integration_document(result)[0] == {"count":1,"api_key":"[REDACTED]"}
        assert session.scalar(select(func.count()).select_from(IntegrationResult)) == 1


def test_expired_claim_cannot_complete(operation_db):
    with operation_db() as session:
        item=operation(lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
        session.add(item); session.commit()
        assert _success(session,item.id,{"ok":True},expected_attempt=1) is False
        assert item.state == "PROCESSING"


def test_cancelled_operation_replays_after_browser_key_rotation(operation_db, monkeypatch):
    with operation_db() as session:
        item=operation("PENDING",0)
        session.add(item); session.commit()
        first=operation_cancel(item.id,CTX,session,"cancel-key-a")
        monkeypatch.setenv("KLYROW_SESSION_SECRET","different-browser-secret" * 2)
        assert operation_cancel(item.id,CTX,session,"cancel-key-a") == first
        assert first["status"] == "CANCELLED"
        assert '"format"' in session.scalar(select(Idempotency.response_json))


def test_ambiguous_dead_letter_cannot_be_blindly_requeued(operation_db):
    with operation_db() as session:
        item=operation("DEAD_LETTER",1,last_error="mautic_transport_ambiguous")
        session.add(item);session.commit()
        with pytest.raises(HTTPException) as error: operation_reconcile(item.id,CTX,session,"reconcile-key-a")
        assert error.value.detail == "operation_requires_provider_readback"
        assert item.state == "DEAD_LETTER"


def test_integration_result_is_encrypted_and_changed_replay_conflicts(operation_db):
    with operation_db() as session:
        item=operation("PENDING",0,target="N8N")
        session.add(item);session.commit()
        request=ResultIn(outbox_id=item.id,source="N8N",result_key="result-key-1",payload={"ok":True,"token":"secret-a"})
        first=accept_result(request,CTX,session)
        assert accept_result(request,CTX,session) == {"id":first["id"],"duplicate":True}
        with pytest.raises(HTTPException) as error:
            accept_result(request.model_copy(update={"payload":{"ok":True,"token":"secret-b"}}),CTX,session)
        assert error.value.status_code == 409
        assert "secret-a" not in session.scalar(select(IntegrationResult.payload_json))


@pytest.mark.skipif(not os.getenv("KLYROW_CONTRACT_POSTGRES_URL"), reason="Required CI supplies disposable PostgreSQL")
def test_locked_cancel_and_claim_have_one_winner(operation_db):
    from concurrent.futures import ThreadPoolExecutor
    with operation_db() as initial:
        initial.add(operation("PENDING",0));initial.commit()
    with operation_db() as cancellation:
        item=cancellation.scalar(select(IntegrationOutbox).where(IntegrationOutbox.id=="operation-a").with_for_update())
        def competing_claim():
            with operation_db() as worker: return _claim(worker)
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(competing_claim).result(timeout=10) is None
        assert operation_cancel(item.id,CTX,cancellation,"concurrent-cancel-key")["status"] == "CANCELLED"
    with operation_db() as verify:
        assert _claim(verify) is None
        assert verify.get(IntegrationOutbox,"operation-a").state == "CANCELLED"


def test_late_completion_blocks_reclaim_and_reports_reconciliation(operation_db):
    with operation_db() as session:
        item = operation("RETRY", 1, next_attempt_at=datetime.now(timezone.utc)-timedelta(seconds=1))
        session.add(item); session.commit()
        assert _success(session, item.id, {"ok": True}, expected_attempt=1) is False
        assert _claim(session) is None
        view = _operation_json(item, session)
        assert view["reconciliation_required"] and not view["retryability"]
        assert item.state == "RETRY"


def test_duplicate_envelope_fields_fail_closed():
    row = store_control({"ok": True})
    row.response_json = row.response_json[:-1] + ',"format":"klyrow-durable-result.v1"}'
    with pytest.raises(HTTPException): read_control_response(row)


def test_maximum_accepted_payload_has_room_for_authenticated_metadata():
    value = {"value": "x" * (65536-len(canonical({"value": ""})))}
    assert len(canonical(value)) == 65536
    assert result_matches(result_row(value), value)


def test_tenant_bounded_rewrap_is_dry_run_idempotent_and_preserves_hash(operation_db, isolated_durable_result_keyring):
    from apps.gateway.app.durable_maintenance import rewrap_batch
    key_id = load_keyring().active_key_id
    original = {"ok": True, "token": "must-still-affect-replay-hash"}
    with operation_db() as session:
        session.add(operation("COMPLETED"))
        row = result_row(original)
        row.payload_json = json.dumps(original)
        session.add(row)
        session.add(IntegrationResult(id="result-b", tenant_id="tenant-b", outbox_id="other",
            source="MAUTIC", result_key="other-key", payload_json='{"private":"other-tenant"}'))
        session.commit()
        report = rewrap_batch(session, table="integration", tenant_id="tenant-a", expected_key_id=key_id)
        assert report["eligible"] == 1 and report["updated"] == 0
        assert row.payload_json == json.dumps(original)
        report = rewrap_batch(session, table="integration", tenant_id="tenant-a", expected_key_id=key_id, apply=True)
        session.commit()
        assert report["updated"] == 1 and result_matches(row, original)
        assert session.get(IntegrationResult, "result-b").payload_json == '{"private":"other-tenant"}'
        assert rewrap_batch(session, table="integration", tenant_id="tenant-a", expected_key_id=key_id, apply=True)["updated"] == 0
        keys = json.loads(isolated_durable_result_keyring.read_text())
        keys["keys"]["rotated"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
        keys["active_key_id"] = "rotated"
        isolated_durable_result_keyring.write_text(json.dumps(keys))
        assert rewrap_batch(session, table="integration", tenant_id="tenant-a", expected_key_id="rotated", apply=True)["updated"] == 1
        session.commit()
        del keys["keys"][key_id]
        isolated_durable_result_keyring.write_text(json.dumps(keys))
        assert result_matches(row, original)
        assert not result_matches(row, {**original, "token":"changed"})


def test_rewrap_corrupt_batch_changes_no_row(operation_db):
    from apps.gateway.app.durable_maintenance import rewrap_batch
    with operation_db() as session:
        session.add_all([
            Idempotency(id="a", tenant_id="tenant-a", key="a", request_hash="a", resource_id="a", response_json='{"ok":true}'),
            Idempotency(id="b", tenant_id="tenant-a", key="b", request_hash="b", resource_id="b", response_json='broken'),
        ])
        session.commit()
        with pytest.raises(HTTPException):
            rewrap_batch(session, table="control", tenant_id="tenant-a", expected_key_id=load_keyring().active_key_id, apply=True)
        session.rollback()
        assert session.get(Idempotency, "a").response_json == '{"ok":true}'
