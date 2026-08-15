import hashlib,hmac,json,os,time,uuid
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
