import base64,hashlib,hmac,json,os,time,uuid
from unittest.mock import AsyncMock,patch
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
os.environ.update(KLYROW_DATABASE_URL="sqlite:///./test.db",KLYROW_SESSION_SECRET="test-secret",KLYROW_WEBHOOK_SECRET="hook-secret",KLYROW_SAFE_MODE="true",KLYROW_ADMIN_EMAIL="admin@example.com",KLYROW_ADMIN_PASSWORD="correct-horse-battery-staple")
from fastapi.testclient import TestClient
from apps.gateway.app.main import Base,DB,Domain,Suppression,Tenant,User,app,engine,ph

def setup_module():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with DB() as s:
        for n in ("a","b"):
            t=Tenant(id=n,name=n,quota=10); s.add(t); s.add(User(id=n,tenant_id=n,email=f"{n}@example.com",password_hash=ph.hash("long-enough-password"),role="tenant_admin")); s.add(Domain(id=n,tenant_id=n,domain=f"{n}.example.com",token=n,verified=True))
        s.commit()
client=TestClient(app)
def login(n): return client.post("/v1/auth/login",json={"email":f"{n}@example.com","password":"long-enough-password"}).json()["access_token"]
def hdr(n): return {"Authorization":"Bearer "+login(n)}
def test_unauthorized(): assert client.get("/v1/domains").status_code==401
def test_tenant_isolation():
    assert [d["domain"] for d in client.get("/v1/domains",headers=hdr("a")).json()]==["a.example.com"]
def test_api_key_revoke():
    h=hdr("a"); made=client.post("/v1/api-keys",headers=h,json={"name":"ci"}).json(); kh={"Authorization":"Bearer "+made["key"]}; assert client.get("/v1/domains",headers=kh).status_code==200; assert client.delete("/v1/api-keys/"+made["id"],headers=h).status_code==204; assert client.get("/v1/domains",headers=kh).status_code==401
def test_safe_send_and_suppression():
    h={**hdr("a"),"Idempotency-Key":"send-1"}; x={"to":"ok@example.net","sender":"sender@a.example.com","subject":"test","html":"<p>test</p>"}; r=client.post("/v1/email/send",headers=h,json=x); assert r.status_code==202 and r.json()["safe_mode"]; assert client.post("/v1/email/send",headers=h,json=x).json()["id"]==r.json()["id"]
    with DB() as s:s.add(Suppression(id="s",tenant_id="a",email="blocked@example.net",reason="unsubscribe"));s.commit()
    x["to"]="blocked@example.net"; assert client.post("/v1/email/send",headers={**hdr("a"),"Idempotency-Key":"send-2"},json=x).status_code==422
def test_contacts_campaigns_and_isolation():
    a,b=hdr("a"),hdr("b"); assert client.post("/v1/contacts",headers=a,json={"email":"one@example.net","name":"One"}).status_code==200; assert len(client.get("/v1/contacts",headers=a).json())==1; assert client.get("/v1/contacts",headers=b).json()==[]
    c=client.post("/v1/campaigns",headers={**a,"Idempotency-Key":"campaign-1"},json={"name":"Mock campaign","subject":"Test"}); assert c.status_code==201; cid=c.json()["id"]; assert client.get("/v1/campaigns/"+cid,headers=b).status_code==404
def test_webhook_signature_and_replay():
    body=json.dumps({"event":"email.delivered","message_id":"m","tenant_id":"a"},separators=(",",":")); ts=str(int(time.time())); eid=str(uuid.uuid4()); sig=hmac.new(b"hook-secret",f"{ts}.{eid}.{body}".encode(),hashlib.sha256).hexdigest(); h={"X-Klyrow-Timestamp":ts,"X-Klyrow-Event-Id":eid,"X-Klyrow-Signature":sig,"Content-Type":"application/json"}
    assert client.post("/v1/webhooks/postal",headers=h,content=body).status_code==202; assert client.post("/v1/webhooks/postal",headers=h,content=body).status_code==409; h["X-Klyrow-Signature"]="bad"; assert client.post("/v1/webhooks/postal",headers=h,content=body).status_code==401

def test_postal_native_signature_normalization_and_idempotency(tmp_path):
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048); public=tmp_path/"postal-public.pem"; public.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)); os.environ.update(KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY=str(public),KLYROW_POSTAL_TENANT_ID="a")
    payload={"event":"MessageDeliveryFailed","timestamp":time.time(),"uuid":str(uuid.uuid4()),"payload":{"message":{"id":1,"message_id":"provider-message","tag":"correlation-1","from":"sender@a.example.com","to":"person@example.net"},"status":"HardFail"}}
    body=json.dumps(payload,separators=(",",":")).encode(); sig=base64.b64encode(private.sign(body,padding.PKCS1v15(),hashes.SHA256())).decode(); headers={"X-Postal-Signature-256":sig,"Content-Type":"application/json"}
    with patch("apps.gateway.app.main.emit_middleware",new=AsyncMock(return_value=True)) as emit:
        first=client.post("/v1/webhooks/postal-native",headers=headers,content=body); duplicate=client.post("/v1/webhooks/postal-native",headers=headers,content=body)
    assert first.status_code==202 and duplicate.status_code==202 and duplicate.json()["duplicate"] is True
    sent=emit.await_args.args; assert sent[0]=="klyrow.email.bounced" and sent[1]["correlation_id"]=="correlation-1"
    assert client.post("/v1/webhooks/postal-native",headers={"X-Postal-Signature-256":"bad"},content=body).status_code==401
