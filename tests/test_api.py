import asyncio,base64,hashlib,hmac,json,os,subprocess,sys,time,uuid
from pathlib import Path
from unittest.mock import AsyncMock,patch
import pytest
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
SERVICE_TOKEN_FILE="/tmp/klyrow-beyvra-test-token"
Path(SERVICE_TOKEN_FILE).write_text("bounded-beyvra-test-token",encoding="utf-8")
os.environ.update(KLYROW_DATABASE_URL="sqlite:///./test.db",KLYROW_SESSION_SECRET="test-session-secret-at-least-32-bytes",KLYROW_WEBHOOK_SECRET="hook-secret",KLYROW_SAFE_MODE="true",KLYROW_ADMIN_EMAIL="admin@example.com",KLYROW_ADMIN_PASSWORD="correct-horse-battery-staple",BEYVRA_EMAIL_SERVICE_TOKEN_FILE=SERVICE_TOKEN_FILE,BEYVRA_EMAIL_TENANT_ID="a",KLYROW_AUTH_RATE_PER_MINUTE="1000")
from fastapi.testclient import TestClient
from sqlalchemy import select
from apps.gateway.app.main import AllowedSender,Audit,Base,DB,Domain,Event,Message,Suppression,Tenant,User,app,engine,ph

def setup_module():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with DB() as s:
        for n in ("a","b"):
            t=Tenant(id=n,name=n,quota=10); s.add(t); s.add(User(id=n,tenant_id=n,email=f"{n}@example.com",password_hash=ph.hash("long-enough-password"),role="tenant_admin")); s.add(Domain(id=n,tenant_id=n,domain=f"{n}.example.com",token=n,verified=True));s.add(AllowedSender(id=n,tenant_id=n,address=f"sender@{n}.example.com",role="support"))
        s.commit()
client=TestClient(app)
def login(n): return client.post("/v1/auth/login",json={"email":f"{n}@example.com","password":"long-enough-password"}).json()["access_token"]
def hdr(n): return {"Authorization":"Bearer "+login(n)}
def test_unauthorized(): assert client.get("/v1/domains").status_code==401
def test_logout_revokes_active_session():
    access=login("a");h={"Authorization":"Bearer "+access}
    assert client.get("/v1/me",headers=h).status_code==200
    assert client.post("/v1/auth/logout",headers=h).status_code==204
    assert client.get("/v1/me",headers=h).status_code==401
def test_tenant_isolation():
    assert [d["domain"] for d in client.get("/v1/domains",headers=hdr("a")).json()]==["a.example.com"]
def test_api_key_revoke():
    h=hdr("a"); made=client.post("/v1/api-keys",headers=h,json={"name":"ci"}).json(); kh={"Authorization":"Bearer "+made["key"]}; assert client.get("/v1/domains",headers=kh).status_code==200; assert client.delete("/v1/api-keys/"+made["id"],headers=h).status_code==204; assert client.get("/v1/domains",headers=kh).status_code==401
def test_logout_revokes_active_session():
    token=login("a");headers={"Authorization":"Bearer "+token};assert client.post("/v1/auth/logout",headers=headers).status_code==204;assert client.get("/v1/me",headers=headers).status_code==401
def test_safe_send_and_suppression():
    h={**hdr("a"),"Idempotency-Key":"send-1"}; x={"to":"ok@example.net","sender":"sender@a.example.com","subject":"test","html":"<p>test</p>"}; r=client.post("/v1/messages",headers=h,json=x); assert r.status_code==202 and r.json()["safe_mode"]; assert client.post("/v1/messages",headers=h,json=x).json()["id"]==r.json()["id"]
    with DB() as s:s.add(Suppression(id="s",tenant_id="a",email="blocked@example.net",reason="hard_bounce"));s.commit()
    x["to"]="blocked@example.net"; assert client.post("/v1/email/send",headers={**hdr("a"),"Idempotency-Key":"send-2"},json=x).status_code==422
def test_unapproved_local_part_is_denied():
    x={"to":"ok@example.net","sender":"admin@a.example.com","subject":"test","html":"<p>test</p>"}
    assert client.post("/v1/email/send",headers={**hdr("a"),"Idempotency-Key":"unapproved-local"},json=x).status_code==403

def test_idempotency_key_is_tenant_scoped_and_changed_payload_conflicts():
    payload_a={"to":"a@example.net","sender":"sender@a.example.com","subject":"same","html":"<p>a</p>"}
    payload_b={"to":"b@example.net","sender":"sender@b.example.com","subject":"same","html":"<p>b</p>"}
    assert client.post("/v1/email/send",headers={**hdr("a"),"Idempotency-Key":"shared-key"},json=payload_a).status_code==202
    assert client.post("/v1/email/send",headers={**hdr("b"),"Idempotency-Key":"shared-key"},json=payload_b).status_code==202
    changed={**payload_a,"subject":"changed"};r=client.post("/v1/email/send",headers={**hdr("a"),"Idempotency-Key":"shared-key"},json=changed)
    assert r.status_code==409 and r.json()["detail"]=="idempotency_key_payload_mismatch"

def test_idempotency_key_is_tenant_scoped():
    body={"to":"same@example.net","subject":"same","html":"<p>same</p>"}
    for tenant in ("a","b"):
        payload={**body,"sender":f"sender@{tenant}.example.com"}
        assert client.post("/v1/email/send",headers={**hdr(tenant),"Idempotency-Key":"tenant-scope-key"},json=payload).status_code==202

def test_production_startup_fails_without_session_secret():
    env={**os.environ,"KLYROW_ENV":"production"};env.pop("KLYROW_SESSION_SECRET",None);env.pop("KLYROW_SESSION_SECRET_FILE",None)
    result=subprocess.run([sys.executable,"-c","import apps.gateway.app.main"],env=env,capture_output=True,text=True)
    assert result.returncode!=0 and "production requires KLYROW_SESSION_SECRET_FILE" in result.stderr

def test_webhook_ssrf_targets_are_rejected():
    assert client.post("/v1/webhooks",headers=hdr("a"),json={"url":"https://127.0.0.1/hook"}).status_code==422

def test_beyvra_service_scope_sender_policy_and_idempotency():
    base={"Authorization":"Bearer bounded-beyvra-test-token","X-Service-Identity":"codestra-server-a:beyvra-email-production","X-Service-Scopes":"email.send email.status","Idempotency-Key":"beyvra-1"}
    payload={"to":"synthetic@example.net","sender":"support@beyvra.com","subject":"Synthetic","html":"<p>Synthetic</p>","text":"Synthetic","stream":"transactional"}
    assert client.post("/v1/internal/email/beyvra/send",headers={**base,"X-Service-Scopes":"email.status"},json=payload).status_code==403
    assert client.post("/v1/internal/email/beyvra/send",headers={**base,"Idempotency-Key":"beyvra-spoof"},json={**payload,"sender":"spoof@beyvra.com"}).status_code==403
    with DB() as s:s.add(Domain(id="beyvra-domain",tenant_id="a",domain="beyvra.com",token="fixture",verified=True));s.add(AllowedSender(id="beyvra-support",tenant_id="a",address="support@beyvra.com",role="support"));s.commit()
    with patch("apps.gateway.app.main.emit_middleware",new=AsyncMock(return_value=True)):
        first=client.post("/v1/internal/email/beyvra/send",headers=base,json=payload);second=client.post("/v1/internal/email/beyvra/send",headers=base,json=payload)
    assert first.status_code==202 and first.json()["provider_message_id"]==second.json()["provider_message_id"]
def test_contacts_campaigns_and_isolation():
    a,b=hdr("a"),hdr("b"); assert client.post("/v1/contacts",headers=a,json={"email":"one@example.net","name":"One"}).status_code==200; assert len(client.get("/v1/contacts",headers=a).json())==1; assert client.get("/v1/contacts",headers=b).json()==[]
    c=client.post("/v1/campaigns",headers={**a,"Idempotency-Key":"campaign-1"},json={"name":"Mock campaign","subject":"Test"}); assert c.status_code==201; cid=c.json()["id"]; assert client.get("/v1/campaigns/"+cid,headers=b).status_code==404
def test_webhook_signature_and_replay():
    body=json.dumps({"event":"email.delivered","message_id":"m","tenant_id":"a"},separators=(",",":")); ts=str(int(time.time())); eid=str(uuid.uuid4()); sig=hmac.new(b"hook-secret",f"{ts}.{eid}.{body}".encode(),hashlib.sha256).hexdigest(); h={"X-Klyrow-Timestamp":ts,"X-Klyrow-Event-Id":eid,"X-Klyrow-Signature":sig,"Content-Type":"application/json"}
    with patch("apps.gateway.app.main.emit_middleware",new=AsyncMock(return_value=True)):
        assert client.post("/v1/webhooks/postal",headers=h,content=body).status_code==202; replay=client.post("/v1/webhooks/postal",headers=h,content=body); assert replay.status_code==202 and replay.json()["duplicate"] is True
    h["X-Klyrow-Signature"]="bad"; assert client.post("/v1/webhooks/postal",headers=h,content=body).status_code==401

def test_webhook_status_suppression_audit_and_duplicate():
    with DB() as s:
        s.add(Message(id="event-message",tenant_id="a",recipient="bounce@example.net",sender="sender@a.example.com",subject="synthetic",status="accepted_test"));s.commit()
    body=json.dumps({"event":"email.bounced","message_id":"event-message","correlation_id":"event-message","tenant_id":"a","recipient":"bounce@example.net","status":"HardBounce"},separators=(",",":"));ts=str(int(time.time()));eid=str(uuid.uuid4());sig=hmac.new(b"hook-secret",f"{ts}.{eid}.{body}".encode(),hashlib.sha256).hexdigest();h={"X-Klyrow-Timestamp":ts,"X-Klyrow-Event-Id":eid,"X-Klyrow-Signature":sig,"Content-Type":"application/json"}
    with patch("apps.gateway.app.main.emit_middleware",new=AsyncMock(return_value=True)):
        first=client.post("/v1/webhooks/postal",headers=h,content=body);duplicate=client.post("/v1/webhooks/postal",headers=h,content=body)
    assert first.status_code==202 and duplicate.json()["duplicate"] is True
    with DB() as s:
        assert s.get(Message,"event-message").status=="hard_bounce"
        assert len(list(s.scalars(select(Suppression).where(Suppression.tenant_id=="a",Suppression.email=="bounce@example.net"))))==1
        assert s.get(Event,eid) is not None
        assert s.scalar(select(Audit).where(Audit.action=="email.status.hard_bounce")) is not None

def test_postal_native_signature_normalization_and_idempotency(tmp_path):
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048); public=tmp_path/"postal-public.pem"; public.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)); os.environ.update(KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY=str(public),KLYROW_POSTAL_TENANT_ID="a")
    payload={"event":"MessageDeliveryFailed","timestamp":time.time(),"uuid":str(uuid.uuid4()),"payload":{"message":{"id":1,"message_id":"provider-message","tag":"correlation-1","from":"sender@a.example.com","to":"person@example.net"},"status":"HardFail"}}
    body=json.dumps(payload,separators=(",",":")).encode(); sig=base64.b64encode(private.sign(body,padding.PKCS1v15(),hashes.SHA256())).decode(); headers={"X-Postal-Signature-256":sig,"Content-Type":"application/json"}
    with patch("apps.gateway.app.main.emit_middleware",new=AsyncMock(return_value=True)) as emit:
        first=client.post("/v1/webhooks/postal-native",headers=headers,content=body); duplicate=client.post("/v1/webhooks/postal-native",headers=headers,content=body)
    assert first.status_code==202 and duplicate.status_code==202 and duplicate.json()["duplicate"] is True
    sent=emit.await_args.args; assert sent[0]=="klyrow.email.bounced" and sent[1]["correlation_id"]=="correlation-1"
    assert client.post("/v1/webhooks/postal-native",headers={"X-Postal-Signature-256":"bad"},content=body).status_code==401


def test_postal_outage_retries_without_loss_or_second_canary_claim(tmp_path,monkeypatch):
    from apps.gateway.app import main as gateway
    from datetime import datetime,timezone,timedelta
    key_file=tmp_path/"postal-key";key_file.write_text("synthetic-key")
    monkeypatch.setattr(gateway,"SAFE_MODE",False)
    monkeypatch.setenv("KLYROW_POSTAL_API_KEY_FILE",str(key_file))
    monkeypatch.setenv("KLYROW_POSTAL_API_URL","https://postal.invalid")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_DOMAIN","a.example.com")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_SENDER","sender@a.example.com")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_RECIPIENT","sink@example.net")
    monkeypatch.setenv("KLYROW_CANARY_ALLOWED_CAMPAIGN","COD-WEB-OUT")
    monkeypatch.setenv("KLYROW_CANARY_MAX_DELIVERIES","1")
    payload={"to":["sink@example.net"],"from":"sender@a.example.com","subject":"outage",
        "plain_body":"fixture","campaign_id":"COD-WEB-OUT"}
    with DB() as s:
        s.merge(gateway.ProductionCanaryGate(gate_key=gateway.canary_gate_key(),reserved_deliveries=1,claimed_deliveries=0))
        s.add(Message(id="postal-outage-message",tenant_id="a",recipient="sink@example.net",
            sender="sender@a.example.com",subject="outage",status="queued"))
        s.add(gateway.EmailOutbox(id="postal-outage-outbox",tenant_id="a",message_id="postal-outage-message",
            payload=json.dumps(payload),state="pending",attempts=0))
        s.commit()
    class FailedClient:
        async def __aenter__(self):return self
        async def __aexit__(self,*_):return False
        async def post(self,*_,**__):raise RuntimeError("synthetic_provider_unavailable")
    with patch.object(gateway.asyncio,"sleep",new=AsyncMock(side_effect=[None,asyncio.CancelledError()])), \
         patch.object(gateway.httpx,"AsyncClient",return_value=FailedClient()):
        with pytest.raises(asyncio.CancelledError):asyncio.run(gateway.email_outbox_loop())
    with DB() as s:
        item=s.get(gateway.EmailOutbox,"postal-outage-outbox");gate=s.get(gateway.ProductionCanaryGate,gateway.canary_gate_key())
        assert item.state=="retry" and item.attempts==1 and s.get(Message,"postal-outage-message").status=="queued"
        assert gate.claimed_deliveries==1
        item.next_attempt_at=datetime.now(timezone.utc)-timedelta(seconds=1);s.commit()
    response=type("Response",(),{"raise_for_status":lambda self:None,
        "json":lambda self:{"data":{"message_id":"synthetic-provider-id"}}})()
    class RecoveredClient(FailedClient):
        async def post(self,*_,**__):return response
    with patch.object(gateway.asyncio,"sleep",new=AsyncMock(side_effect=[None,asyncio.CancelledError()])), \
         patch.object(gateway.httpx,"AsyncClient",return_value=RecoveredClient()):
        with pytest.raises(asyncio.CancelledError):asyncio.run(gateway.email_outbox_loop())
    with DB() as s:
        item=s.get(gateway.EmailOutbox,"postal-outage-outbox");gate=s.get(gateway.ProductionCanaryGate,gateway.canary_gate_key())
        assert item.state=="delivered" and item.provider_message_id=="synthetic-provider-id" and item.attempts==2
        assert s.get(Message,"postal-outage-message").status=="accepted" and gate.claimed_deliveries==1
