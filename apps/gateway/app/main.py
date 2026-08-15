import hashlib, hmac, json, os, secrets, time, uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx, jwt
from argon2 import PasswordHasher
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL=os.getenv("KLYROW_DATABASE_URL", "sqlite:///./klyrow.db")
SECRET=os.getenv("KLYROW_SESSION_SECRET", "dev-only-change-me")
SAFE_MODE=os.getenv("KLYROW_SAFE_MODE", "true").lower()=="true" or os.getenv("KLYROW_PRODUCTION_GATE_APPROVED","false").lower()!="true"
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
DB=sessionmaker(engine, expire_on_commit=False)
ph=PasswordHasher()
app=FastAPI(title="Klyrow API", version="1.0.0", docs_url=None if os.getenv("KLYROW_ENV")=="production" else "/docs")
REQUESTS=Counter("klyrow_http_requests_total","Requests",["path","status"])
MAIL=Counter("klyrow_mail_total","Mail lifecycle",["event"])
LATENCY=Histogram("klyrow_http_request_duration_seconds","Request latency",["path"])
rate_buckets=defaultdict(deque)

class Base(DeclarativeBase): pass
class Tenant(Base):
    __tablename__="tenants"; id:Mapped[str]=mapped_column(String,primary_key=True); name:Mapped[str]=mapped_column(String); enabled:Mapped[bool]=mapped_column(Boolean,default=True); quota:Mapped[int]=mapped_column(Integer,default=10000)
class User(Base):
    __tablename__="users"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id")); email:Mapped[str]=mapped_column(String,unique=True,index=True); password_hash:Mapped[str]=mapped_column(String); role:Mapped[str]=mapped_column(String,default="tenant_user"); enabled:Mapped[bool]=mapped_column(Boolean,default=True); reset_hash:Mapped[Optional[str]]=mapped_column(String,nullable=True); reset_expires:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)
class ApiKey(Base):
    __tablename__="api_keys"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); name:Mapped[str]=mapped_column(String); key_hash:Mapped[str]=mapped_column(String,unique=True); revoked:Mapped[bool]=mapped_column(Boolean,default=False)
class Domain(Base):
    __tablename__="domains"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); domain:Mapped[str]=mapped_column(String); token:Mapped[str]=mapped_column(String); verified:Mapped[bool]=mapped_column(Boolean,default=False)
class Message(Base):
    __tablename__="messages"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); recipient:Mapped[str]=mapped_column(String); sender:Mapped[str]=mapped_column(String); subject:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Event(Base):
    __tablename__="events"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); message_id:Mapped[str]=mapped_column(String,index=True); kind:Mapped[str]=mapped_column(String); payload:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Suppression(Base):
    __tablename__="suppressions"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); email:Mapped[str]=mapped_column(String,index=True); reason:Mapped[str]=mapped_column(String)
class Replay(Base):
    __tablename__="webhook_replays"; id:Mapped[str]=mapped_column(String,primary_key=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Audit(Base):
    __tablename__="audit_log"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); actor:Mapped[str]=mapped_column(String); action:Mapped[str]=mapped_column(String); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Contact(Base):
    __tablename__="contacts"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); email:Mapped[str]=mapped_column(String,index=True); name:Mapped[Optional[str]]=mapped_column(String,nullable=True); subscribed:Mapped[bool]=mapped_column(Boolean,default=True); metadata_json:Mapped[str]=mapped_column(Text,default="{}")
    __table_args__=(UniqueConstraint("tenant_id","email",name="uq_contact_tenant_email"),)
class Campaign(Base):
    __tablename__="campaigns"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); name:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String,default="draft"); subject:Mapped[Optional[str]]=mapped_column(String,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Idempotency(Base):
    __tablename__="idempotency_keys"; key:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); request_hash:Mapped[str]=mapped_column(String); resource_id:Mapped[str]=mapped_column(String); response_json:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class WebhookEndpoint(Base):
    __tablename__="webhook_endpoints"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); url:Mapped[str]=mapped_column(String); enabled:Mapped[bool]=mapped_column(Boolean,default=True); secret_hash:Mapped[str]=mapped_column(String)

def db():
    with DB() as s: yield s
def sha(v): return hashlib.sha256(v.encode()).hexdigest()
def token(user,s):
    from .saas import SessionRecord
    sid=str(uuid.uuid4());s.add(SessionRecord(id=sid,user_id=user.id,tenant_id=user.tenant_id));s.commit();return jwt.encode({"sub":user.id,"tenant":user.tenant_id,"role":user.role,"sid":sid,"exp":datetime.now(timezone.utc)+timedelta(hours=8)},SECRET,algorithm="HS256")
def audit(s, ctx, action): s.add(Audit(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],actor=ctx["sub"],action=action))
def auth(authorization:str=Header(default=""), x_klyrow_tenant_id:Optional[str]=Header(default=None), s:Session=Depends(db)):
    if not authorization.startswith("Bearer "): raise HTTPException(401,"authentication_required")
    raw=authorization[7:]
    try:
        middleware_key=os.getenv("KLYROW_MIDDLEWARE_API_KEY","")
        if middleware_key and hmac.compare_digest(raw.encode(),middleware_key.encode()):
            tenant=s.get(Tenant,x_klyrow_tenant_id) if x_klyrow_tenant_id else None
            if not tenant or not tenant.enabled:raise HTTPException(403,"valid_tenant_required")
            ctx={"sub":"middleware-service","tenant":tenant.id,"role":"tenant_admin","service":True}
        elif raw.startswith("kly_"):
            key=s.scalar(select(ApiKey).where(ApiKey.key_hash==sha(raw),ApiKey.revoked==False))
            if not key: raise ValueError()
            tenant=s.get(Tenant,key.tenant_id)
            if not tenant or not tenant.enabled: raise HTTPException(403,"account_suspended")
            ctx={"sub":key.id,"tenant":key.tenant_id,"role":"tenant_admin","api_key":True}
        else:
            ctx=jwt.decode(raw,SECRET,algorithms=["HS256"])
            from .saas import SessionRecord
            session=s.get(SessionRecord,ctx.get("sid")) if ctx.get("sid") else None
            if ctx.get("sid") and (not session or session.revoked):raise HTTPException(401,"session_revoked")
            tenant=s.get(Tenant,ctx["tenant"])
            if not tenant or not tenant.enabled:raise HTTPException(403,"account_suspended")
    except HTTPException: raise
    except Exception: raise HTTPException(401,"invalid_credentials")
    now=time.time(); q=rate_buckets[ctx["tenant"]]
    while q and q[0]<now-60:q.popleft()
    if len(q)>=int(os.getenv("KLYROW_RATE_PER_MINUTE","60")): raise HTTPException(429,"rate_limit_exceeded")
    q.append(now); return ctx
def require(*roles):
    def inner(ctx=Depends(auth)):
        if ctx["role"] not in roles: raise HTTPException(403,"insufficient_role")
        return ctx
    return inner

class Login(BaseModel): email:EmailStr; password:str; otp:Optional[str]=None
class ResetRequest(BaseModel): email:EmailStr
class Reset(BaseModel): token:str; password:str=Field(min_length=14)
class KeyIn(BaseModel): name:str=Field(min_length=1,max_length=80)
class DomainIn(BaseModel): domain:str=Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")
class MailIn(BaseModel):
    customer_id:Optional[str]=None; to:EmailStr; sender:EmailStr; reply_to:Optional[EmailStr]=None; subject:str=Field(max_length=998); html:str=Field(max_length=100000); text:Optional[str]=None; template_id:Optional[str]=None; campaign_id:Optional[str]=None; tags:list[str]=Field(default_factory=list,max_length=50); tracking:dict=Field(default_factory=dict); callback_metadata:dict=Field(default_factory=dict); stream:str=Field(default="transactional",pattern="^(marketing|transactional)$"); topic:str="marketing"
    @model_validator(mode="before")
    @classmethod
    def accept_from_alias(cls,data):
        if isinstance(data,dict) and "sender" not in data and "from" in data:data={**data,"sender":data["from"]}
        return data
class BulkMailIn(BaseModel): messages:list[MailIn]=Field(min_length=1,max_length=100)
class ContactIn(BaseModel): email:EmailStr; name:Optional[str]=Field(default=None,max_length=200); subscribed:bool=True; metadata:dict={}
class CampaignIn(BaseModel): name:str=Field(min_length=1,max_length=200); subject:Optional[str]=Field(default=None,max_length=998)
class TenantIn(BaseModel): name:str=Field(min_length=1,max_length=200); quota:int=Field(default=10000,ge=0,le=10000000)
class QuotaIn(BaseModel): quota:int=Field(ge=0,le=10000000)
class WebhookIn(BaseModel): url:str=Field(pattern=r"^https://")

async def emit_middleware(event_type:str,payload:dict):
    base=os.getenv("KLYROW_MIDDLEWARE_URL","").rstrip("/"); key=os.getenv("KLYROW_MIDDLEWARE_API_KEY",""); secret=os.getenv("KLYROW_WEBHOOK_SECRET","")
    if not base or not key or not secret:return
    event_id=payload.get("event_id") or str(uuid.uuid4()); payload={"event_id":event_id,"source_system":"klyrow","event_type":event_type,"timestamp":datetime.now(timezone.utc).isoformat(),**payload}
    body=json.dumps(payload,separators=(",",":"),sort_keys=True).encode(); ts=str(int(time.time())); canonical=ts.encode()+b"\n"+event_id.encode()+b"\nklyrow\n"+body
    signature=hmac.new(secret.encode(),canonical,hashlib.sha256).hexdigest(); headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","X-Source-System":"klyrow","X-Klyrow-Timestamp":ts,"X-Klyrow-Event-Id":event_id,"X-Klyrow-Signature":"sha256="+signature}
    path={"klyrow.email.bounced":"bounces","klyrow.email.complained":"complaints","klyrow.email.unsubscribed":"unsubscribes"}.get(event_type,"events")
    try:
        async with httpx.AsyncClient(timeout=1,trust_env=False) as client: response=await client.post(f"{base}/api/v1/klyrow/{path}",headers=headers,content=body); response.raise_for_status()
    except Exception as exc: print(json.dumps({"level":"warning","system":"klyrow","event_id":event_id,"message_id":payload.get("message_id"),"event":"middleware_delivery_failed","error":type(exc).__name__}))

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with DB() as s:
        if not s.scalar(select(User).limit(1)):
            email=os.getenv("KLYROW_ADMIN_EMAIL"); password=os.getenv("KLYROW_ADMIN_PASSWORD")
            if email and password and len(password)>=14:
                t=Tenant(id=str(uuid.uuid4()),name="Klyrow",quota=int(os.getenv("KLYROW_DAILY_QUOTA","10000"))); s.add(t); s.add(User(id=str(uuid.uuid4()),tenant_id=t.id,email=email.lower(),password_hash=ph.hash(password),role="platform_admin")); s.commit()

@app.middleware("http")
async def headers(request, call_next):
    started=time.monotonic();request_id=request.headers.get("X-Request-Id") or str(uuid.uuid4())
    try: response=await call_next(request)
    except Exception: REQUESTS.labels(request.url.path,"500").inc(); raise
    response.headers.update({"X-Request-Id":request_id,"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Permissions-Policy":"camera=(), microphone=(), geolocation=()","Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"})
    REQUESTS.labels(request.url.path,str(response.status_code)).inc();LATENCY.labels(request.url.path).observe(time.monotonic()-started); return response

@app.get("/v1/health")
def health(s:Session=Depends(db)): s.execute(select(1)); return {"status":"ok","safe_mode":SAFE_MODE,"production_gate_approved":os.getenv("KLYROW_PRODUCTION_GATE_APPROVED","false").lower()=="true"}
@app.get("/metrics")
def metrics(): from fastapi.responses import Response; return Response(generate_latest(),media_type="text/plain")
@app.post("/v1/auth/login")
def login(x:Login,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.email==x.email.lower()))
    try: valid=u and u.enabled and ph.verify(u.password_hash,x.password)
    except Exception: valid=False
    if not valid: raise HTTPException(401,"invalid_credentials")
    from .saas import MfaConfig,verify_totp
    m=s.get(MfaConfig,u.id)
    if m and m.enabled and (not x.otp or not verify_totp(m.secret,x.otp)):raise HTTPException(401,"mfa_required")
    return {"access_token":token(u,s),"token_type":"bearer","role":u.role,"tenant_id":u.tenant_id}
@app.post("/v1/auth/logout",status_code=204)
def logout(ctx=Depends(auth)): return None
@app.post("/v1/auth/forgot-password",status_code=202)
def forgot(x:ResetRequest,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.email==x.email.lower()))
    if u: raw=secrets.token_urlsafe(32); u.reset_hash=sha(raw); u.reset_expires=datetime.now(timezone.utc)+timedelta(minutes=30); s.commit()
    return {"detail":"If the account exists, reset instructions will be delivered."}
@app.post("/v1/auth/reset-password")
def reset(x:Reset,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.reset_hash==sha(x.token)))
    if not u or not u.reset_expires or u.reset_expires.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise HTTPException(400,"invalid_or_expired_token")
    u.password_hash=ph.hash(x.password); u.reset_hash=None; u.reset_expires=None; s.commit(); return {"status":"reset"}
@app.get("/v1/me")
def me(ctx=Depends(auth)): return ctx
@app.post("/v1/api-keys")
def create_key(x:KeyIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    raw="kly_"+secrets.token_urlsafe(32); k=ApiKey(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],name=x.name,key_hash=sha(raw)); s.add(k); audit(s,ctx,"api_key.created"); s.commit(); return {"id":k.id,"key":raw,"name":k.name}
@app.delete("/v1/api-keys/{kid}",status_code=204)
def revoke(kid:str,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    k=s.scalar(select(ApiKey).where(ApiKey.id==kid,ApiKey.tenant_id==ctx["tenant"]));
    if not k: raise HTTPException(404,"not_found")
    k.revoked=True; audit(s,ctx,"api_key.revoked"); s.commit()
@app.get("/v1/domains")
def domains(ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Domain).where(Domain.tenant_id==ctx["tenant"])).all()
@app.post("/v1/domains")
def domain_add(x:DomainIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    d=Domain(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],domain=x.domain.lower(),token=secrets.token_urlsafe(24)); s.add(d); s.commit(); return {"id":d.id,"domain":d.domain,"verified":False,"dns":{"type":"TXT","name":"_klyrow-verification."+d.domain,"value":"klyrow="+d.token}}
@app.post("/v1/domains/{did}/verify")
def domain_verify(did:str,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    import socket
    d=s.scalar(select(Domain).where(Domain.id==did,Domain.tenant_id==ctx["tenant"]));
    if not d: raise HTTPException(404,"not_found")
    try:
        import dns.resolver; values=[str(r).strip('"') for r in dns.resolver.resolve("_klyrow-verification."+d.domain,"TXT")]; d.verified=("klyrow="+d.token) in values
    except Exception: d.verified=False
    s.commit(); return {"verified":d.verified}
@app.post("/v1/email/send",status_code=202)
async def send(x:MailIn,ctx=Depends(auth),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    if not idempotency_key: raise HTTPException(400,"idempotency_key_required")
    request_hash=sha(x.model_dump_json())
    prior=s.scalar(select(Idempotency).where(Idempotency.key==idempotency_key,Idempotency.tenant_id==ctx["tenant"]))
    if prior:
        if prior.request_hash!=request_hash:raise HTTPException(409,"idempotency_key_payload_mismatch")
        return json.loads(prior.response_json)
    if s.scalar(select(Suppression).where(Suppression.tenant_id==ctx["tenant"],Suppression.email==x.to.lower())): raise HTTPException(422,"recipient_suppressed")
    from .saas import Consent,Preference,Profile,UsageLedger
    profile=s.scalar(select(Profile).where(Profile.tenant_id==ctx["tenant"],Profile.email==x.to.lower()))
    if x.stream=="marketing":
        if not profile:raise HTTPException(422,"marketing_consent_required")
        pref=s.scalar(select(Preference).where(Preference.tenant_id==ctx["tenant"],Preference.profile_id==profile.id,Preference.topic==x.topic))
        latest=s.scalar(select(Consent).where(Consent.tenant_id==ctx["tenant"],Consent.profile_id==profile.id,Consent.topic==x.topic).order_by(Consent.occurred_at.desc()))
        if not pref or not pref.subscribed or not latest or latest.status!="granted":raise HTTPException(422,"marketing_consent_required")
    domain=x.sender.rsplit("@",1)[1]; allowed=s.scalar(select(Domain).where(Domain.tenant_id==ctx["tenant"],Domain.domain==domain,Domain.verified==True))
    if not allowed: raise HTTPException(422,"sender_domain_not_verified")
    since=datetime.now(timezone.utc)-timedelta(days=1); count=len(s.scalars(select(Message).where(Message.tenant_id==ctx["tenant"],Message.created_at>=since)).all()); tenant=s.get(Tenant,ctx["tenant"])
    if count>=tenant.quota: raise HTTPException(429,"daily_quota_exceeded")
    mid=str(uuid.uuid4()); status="accepted_test" if SAFE_MODE else "queued"
    if not SAFE_MODE:
        headers={"X-Server-API-Key":os.environ["KLYROW_POSTAL_API_KEY"]}; payload={"to":[x.to],"from":x.sender,"subject":x.subject,"html_body":x.html,"plain_body":x.text}
        async with httpx.AsyncClient(timeout=10) as c: r=await c.post(os.environ["KLYROW_POSTAL_API_URL"]+"/api/v1/send/message",headers=headers,json=payload); r.raise_for_status()
    result={"id":mid,"status":status,"safe_mode":SAFE_MODE,"stream":x.stream}; s.add(Message(id=mid,tenant_id=ctx["tenant"],recipient=x.to.lower(),sender=x.sender.lower(),subject=x.subject,status=status)); s.add(Event(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],message_id=mid,kind="klyrow.email.queued",payload=json.dumps({"stream":x.stream}))); s.add(Idempotency(key=idempotency_key,tenant_id=ctx["tenant"],request_hash=request_hash,resource_id=mid,response_json=json.dumps(result)));s.add(UsageLedger(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],kind="message."+x.stream,quantity=1,reference=mid)); s.commit(); MAIL.labels("queued").inc(); await emit_middleware("klyrow.email.queued",{"customer_id":ctx["tenant"],"message_id":mid,"recipient":x.to.lower(),"sender":x.sender.lower(),"status":status,"provider":"postal","metadata":{"stream":x.stream}}); return result

@app.post("/v1/email/bulk",status_code=202)
async def bulk(x:BulkMailIn,ctx=Depends(auth),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    if not idempotency_key: raise HTTPException(400,"idempotency_key_required")
    results=[]
    for index,item in enumerate(x.messages): results.append(await send(item,ctx,s,f"{idempotency_key}:{index}"))
    return {"accepted":len(results),"messages":results}
@app.get("/v1/email/{mid}")
def message(mid:str,ctx=Depends(auth),s:Session=Depends(db)):
    m=s.scalar(select(Message).where(Message.id==mid,Message.tenant_id==ctx["tenant"]));
    if not m: raise HTTPException(404,"not_found")
    return m
@app.get("/v1/messages/{mid}")
def message_alias(mid:str,ctx=Depends(auth),s:Session=Depends(db)):
    return message(mid,ctx,s)
@app.get("/v1/email/{mid}/events")
def events(mid:str,ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Event).where(Event.message_id==mid,Event.tenant_id==ctx["tenant"])).all()
@app.post("/v1/webhooks/postal",status_code=202)
async def postal_hook(request:Request,x_klyrow_timestamp:str=Header(),x_klyrow_event_id:str=Header(),x_klyrow_signature:str=Header(),s:Session=Depends(db)):
    body=await request.body(); secret=os.environ.get("KLYROW_WEBHOOK_SECRET","").encode()
    try: ts=int(x_klyrow_timestamp)
    except: raise HTTPException(401,"invalid_timestamp")
    if abs(time.time()-ts)>300: raise HTTPException(401,"expired_signature")
    expected=hmac.new(secret,x_klyrow_timestamp.encode()+b"."+x_klyrow_event_id.encode()+b"."+body,hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(expected,x_klyrow_signature): raise HTTPException(401,"invalid_signature")
    if s.get(Replay,x_klyrow_event_id): raise HTTPException(409,"replayed_event")
    s.add(Replay(id=x_klyrow_event_id)); payload=json.loads(body); mid=payload.get("message_id"); tenant=payload.get("tenant_id")
    if mid and tenant: s.add(Event(id=str(uuid.uuid4()),tenant_id=tenant,message_id=mid,kind=payload.get("event","email.unknown"),payload=body.decode()))
    event_type=payload.get("event","klyrow.email.unknown"); event_type=event_type if event_type.startswith("klyrow.") else "klyrow."+event_type
    if event_type in {"klyrow.email.bounced","klyrow.email.complained","klyrow.email.unsubscribed"} and tenant and payload.get("recipient"):
        if not s.scalar(select(Suppression).where(Suppression.tenant_id==tenant,Suppression.email==payload["recipient"].lower())): s.add(Suppression(id=str(uuid.uuid4()),tenant_id=tenant,email=payload["recipient"].lower(),reason=event_type.rsplit(".",1)[-1]))
    s.commit(); await emit_middleware(event_type,{**payload,"event_id":x_klyrow_event_id,"customer_id":tenant}); return {"accepted":True}

@app.get("/v1/contacts")
def contacts(ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Contact).where(Contact.tenant_id==ctx["tenant"])).all()
@app.post("/v1/contacts")
def contact_upsert(x:ContactIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    item=s.scalar(select(Contact).where(Contact.tenant_id==ctx["tenant"],Contact.email==x.email.lower())) or Contact(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],email=x.email.lower()); item.name=x.name; item.subscribed=x.subscribed; item.metadata_json=json.dumps(x.metadata); s.add(item); audit(s,ctx,"contact.upserted"); s.commit(); return item
@app.get("/v1/campaigns")
def campaigns(ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Campaign).where(Campaign.tenant_id==ctx["tenant"])).all()
@app.post("/v1/campaigns",status_code=201)
async def campaign_create(x:CampaignIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    if not idempotency_key: raise HTTPException(400,"idempotency_key_required")
    request_hash=sha(x.model_dump_json())
    prior=s.scalar(select(Idempotency).where(Idempotency.key==idempotency_key,Idempotency.tenant_id==ctx["tenant"]));
    if prior:
        if prior.request_hash!=request_hash:raise HTTPException(409,"idempotency_key_payload_mismatch")
        return json.loads(prior.response_json)
    c=Campaign(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],name=x.name,subject=x.subject); result={"id":c.id,"name":c.name,"status":c.status}; s.add(c); s.add(Idempotency(key=idempotency_key,tenant_id=ctx["tenant"],request_hash=request_hash,resource_id=c.id,response_json=json.dumps(result))); audit(s,ctx,"campaign.created"); s.commit(); return result
@app.get("/v1/campaigns/{cid}")
def campaign_get(cid:str,ctx=Depends(auth),s:Session=Depends(db)):
    c=s.scalar(select(Campaign).where(Campaign.id==cid,Campaign.tenant_id==ctx["tenant"]));
    if not c:raise HTTPException(404,"not_found")
    return c
@app.get("/v1/suppressions")
def suppressions(ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Suppression).where(Suppression.tenant_id==ctx["tenant"])).all()
@app.get("/v1/audit")
def audits(ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)): return s.scalars(select(Audit).where(Audit.tenant_id==ctx["tenant"]).order_by(Audit.created_at.desc()).limit(200)).all()
@app.get("/v1/usage")
def usage(ctx=Depends(auth),s:Session=Depends(db)): return {"sent_24h":len(s.scalars(select(Message).where(Message.tenant_id==ctx["tenant"],Message.created_at>=datetime.now(timezone.utc)-timedelta(days=1))).all()),"quota":s.get(Tenant,ctx["tenant"]).quota}
@app.post("/v1/webhooks")
def webhook_add(x:WebhookIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    raw=secrets.token_urlsafe(32); item=WebhookEndpoint(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],url=x.url,secret_hash=sha(raw)); s.add(item); audit(s,ctx,"webhook.created"); s.commit(); return {"id":item.id,"url":item.url,"secret":raw}
@app.get("/v1/admin/tenants")
def admin_tenants(ctx=Depends(require("platform_admin")),s:Session=Depends(db)): return s.scalars(select(Tenant)).all()
@app.post("/v1/admin/tenants",status_code=201)
def admin_tenant_create(x:TenantIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)): item=Tenant(id=str(uuid.uuid4()),name=x.name,quota=x.quota); s.add(item); audit(s,ctx,"tenant.created"); s.commit(); return item
@app.post("/v1/admin/tenants/{tid}/suspend")
def admin_suspend(tid:str,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    item=s.get(Tenant,tid)
    if not item:raise HTTPException(404,"not_found")
    item.enabled=False; audit(s,ctx,"tenant.suspended"); s.commit(); return {"id":tid,"enabled":False}
@app.post("/v1/admin/tenants/{tid}/quota")
def admin_quota(tid:str,x:QuotaIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    item=s.get(Tenant,tid)
    if not item:raise HTTPException(404,"not_found")
    item.quota=x.quota; audit(s,ctx,"tenant.quota_changed"); s.commit(); return {"id":tid,"quota":item.quota}
@app.get("/",response_class=HTMLResponse)
def portal(): return Path(__file__).with_name("portal.html").read_text()
@app.get("/assets/portal.js",include_in_schema=False)
def portal_js():return FileResponse(Path(__file__).with_name("portal.js"),media_type="application/javascript")

from .saas import router as saas_router
app.include_router(saas_router)
