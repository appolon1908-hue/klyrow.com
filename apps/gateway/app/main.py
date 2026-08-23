import asyncio, base64, hashlib, hmac, ipaddress, json, os, secrets, socket, ssl, time, uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx, jwt
from jwt import PyJWKClient
from argon2 import PasswordHasher
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, func, or_, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL=os.getenv("KLYROW_DATABASE_URL", "sqlite:///./klyrow.db")
def required_session_secret():
    path=os.getenv("KLYROW_SESSION_SECRET_FILE","")
    if path:
        try:value=Path(path).read_text(encoding="utf-8").strip()
        except OSError as exc:raise RuntimeError("KLYROW session secret file unavailable") from exc
    else:value=os.getenv("KLYROW_SESSION_SECRET","")
    if os.getenv("KLYROW_ENV", "development").lower()=="production" and not path:raise RuntimeError("production requires KLYROW_SESSION_SECRET_FILE")
    if not value:value=secrets.token_urlsafe(32)
    return value
SECRET=required_session_secret()
if len(SECRET) < 32: raise RuntimeError("KLYROW_SESSION_SECRET must contain at least 32 characters")
SAFE_MODE=os.getenv("KLYROW_SAFE_MODE", "true").lower()=="true" or os.getenv("KLYROW_PRODUCTION_GATE_APPROVED","false").lower()!="true"
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
DB=sessionmaker(engine, expire_on_commit=False)
ph=PasswordHasher()
app=FastAPI(title="Klyrow API", version="1.0.0", docs_url=None if os.getenv("KLYROW_ENV")=="production" else "/docs")
REQUESTS=Counter("klyrow_http_requests_total","Requests",["path","status"])
MAIL=Counter("klyrow_mail_total","Mail lifecycle",["event"])
LATENCY=Histogram("klyrow_http_request_duration_seconds","Request latency",["path"])
PROVIDER_QUEUE=Gauge("klyrow_provider_queue_messages","Provider messages by status",["status"])
PROVIDER_EVENTS=Gauge("klyrow_provider_events","Provider events by state",["state"])
PROVIDER_USAGE=Gauge("klyrow_provider_usage_events","Provider usage events by state",["state"])
OUTBOX_OLDEST=Gauge("klyrow_email_outbox_oldest_seconds","Age of oldest active email outbox item")
INTEGRATION_QUEUE=Gauge("klyrow_integration_outbox_items","Integration outbox items",["target","state"])
WEBHOOK_QUEUE=Gauge("klyrow_webhook_attempts","Customer webhook attempts",["state"])
DELIVERY_RATE=Gauge("klyrow_delivery_ratio","Delivery outcome ratio",["outcome"])
DNS_INVALID=Gauge("klyrow_domain_dns_invalid","Domains not currently verified for sending")
BILLING_DRIFT=Gauge("klyrow_billing_reconciliation_drift","Invoices whose ledger state disagrees with confirmed payments")
rate_buckets=defaultdict(deque)
_jwks_clients={}

class Base(DeclarativeBase): pass
class Tenant(Base):
    __tablename__="tenants"; id:Mapped[str]=mapped_column(String,primary_key=True); name:Mapped[str]=mapped_column(String); enabled:Mapped[bool]=mapped_column(Boolean,default=True); quota:Mapped[int]=mapped_column(Integer,default=10000)
class User(Base):
    __tablename__="users"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id")); email:Mapped[str]=mapped_column(String,unique=True,index=True); password_hash:Mapped[str]=mapped_column(String); role:Mapped[str]=mapped_column(String,default="tenant_user"); enabled:Mapped[bool]=mapped_column(Boolean,default=True); reset_hash:Mapped[Optional[str]]=mapped_column(String,nullable=True); reset_expires:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)
class ApiKey(Base):
    __tablename__="api_keys"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); name:Mapped[str]=mapped_column(String); key_hash:Mapped[str]=mapped_column(String,unique=True); revoked:Mapped[bool]=mapped_column(Boolean,default=False)
class Domain(Base):
    __tablename__="domains"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); domain:Mapped[str]=mapped_column(String); token:Mapped[str]=mapped_column(String); verified:Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint("tenant_id","domain",name="uq_domain_tenant_name"),)
class AllowedSender(Base):
    __tablename__="allowed_senders"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); address:Mapped[str]=mapped_column(String,index=True); role:Mapped[str]=mapped_column(String); enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    __table_args__=(UniqueConstraint("tenant_id","address",name="uq_allowed_sender_tenant_address"),)
class InboundRouteConfig(Base):
    __tablename__="inbound_route_configs"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); address:Mapped[str]=mapped_column(String,index=True); destination_kind:Mapped[str]=mapped_column(String); destination_ref:Mapped[Optional[str]]=mapped_column(String,nullable=True); verified:Mapped[bool]=mapped_column(Boolean,default=False); enabled:Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint("tenant_id","address",name="uq_inbound_route_tenant_address"),)
class Message(Base):
    __tablename__="messages"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); recipient:Mapped[str]=mapped_column(String); sender:Mapped[str]=mapped_column(String); subject:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Event(Base):
    __tablename__="events"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); message_id:Mapped[str]=mapped_column(String,index=True); kind:Mapped[str]=mapped_column(String); payload:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Suppression(Base):
    __tablename__="suppressions"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); email:Mapped[str]=mapped_column(String,index=True); reason:Mapped[str]=mapped_column(String)
class Replay(Base):
    __tablename__="webhook_replays"; id:Mapped[str]=mapped_column(String,primary_key=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class PostalEvent(Base):
    __tablename__="postal_events"; id:Mapped[str]=mapped_column(String,primary_key=True); event_type:Mapped[str]=mapped_column(String,index=True); correlation_id:Mapped[str]=mapped_column(String,index=True); message_id:Mapped[str]=mapped_column(String,index=True); tenant_id:Mapped[str]=mapped_column(String,index=True); payload:Mapped[str]=mapped_column(Text); state:Mapped[str]=mapped_column(String,default="pending",index=True); attempts:Mapped[int]=mapped_column(Integer,default=0); last_error:Mapped[Optional[str]]=mapped_column(String,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Audit(Base):
    __tablename__="audit_log"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); actor:Mapped[str]=mapped_column(String); action:Mapped[str]=mapped_column(String); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Contact(Base):
    __tablename__="contacts"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); email:Mapped[str]=mapped_column(String,index=True); name:Mapped[Optional[str]]=mapped_column(String,nullable=True); subscribed:Mapped[bool]=mapped_column(Boolean,default=True); metadata_json:Mapped[str]=mapped_column(Text,default="{}")
    __table_args__=(UniqueConstraint("tenant_id","email",name="uq_contact_tenant_email"),)
class Campaign(Base):
    __tablename__="campaigns"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); name:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String,default="draft"); subject:Mapped[Optional[str]]=mapped_column(String,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Idempotency(Base):
    __tablename__="idempotency_keys"; id:Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); key:Mapped[str]=mapped_column(String); tenant_id:Mapped[str]=mapped_column(String,index=True); request_hash:Mapped[str]=mapped_column(String); resource_id:Mapped[str]=mapped_column(String); response_json:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); __table_args__=(UniqueConstraint("tenant_id","key",name="uq_idempotency_tenant_key"),)
class EmailOutbox(Base):
    __tablename__="email_outbox"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); message_id:Mapped[str]=mapped_column(String,unique=True,index=True); payload:Mapped[str]=mapped_column(Text); state:Mapped[str]=mapped_column(String,default="pending",index=True); attempts:Mapped[int]=mapped_column(Integer,default=0); provider_message_id:Mapped[Optional[str]]=mapped_column(String,nullable=True); last_error:Mapped[Optional[str]]=mapped_column(String,nullable=True); next_attempt_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class ProductionCanaryGate(Base):
    __tablename__="production_canary_gate"; gate_key:Mapped[str]=mapped_column(String,primary_key=True); reserved_deliveries:Mapped[int]=mapped_column(Integer,default=0); claimed_deliveries:Mapped[int]=mapped_column(Integer,default=0); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class WebhookEndpoint(Base):
    __tablename__="webhook_endpoints"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); url:Mapped[str]=mapped_column(String); enabled:Mapped[bool]=mapped_column(Boolean,default=True); secret_hash:Mapped[str]=mapped_column(String)

def db():
    with DB() as s: yield s
def sha(v): return hashlib.sha256(v.encode()).hexdigest()
def token(user,s):
    from .saas import SessionRecord
    sid=str(uuid.uuid4());s.add(SessionRecord(id=sid,user_id=user.id,tenant_id=user.tenant_id));s.commit();return jwt.encode({"sub":user.id,"tenant":user.tenant_id,"role":user.role,"sid":sid,"exp":datetime.now(timezone.utc)+timedelta(hours=8)},SECRET,algorithm="HS256")
def audit(s, ctx, action): s.add(Audit(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],actor=ctx["sub"],action=action))
def safe_webhook_url(value:str)->str:
    from urllib.parse import urlsplit
    parsed=urlsplit(value)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:raise HTTPException(422,"unsafe_webhook_url")
    try: addresses={item[4][0] for item in socket.getaddrinfo(parsed.hostname,parsed.port or 443,type=socket.SOCK_STREAM)}
    except OSError:raise HTTPException(422,"webhook_dns_unavailable")
    if not addresses or any(ipaddress.ip_address(address).is_private or ipaddress.ip_address(address).is_loopback or ipaddress.ip_address(address).is_link_local or ipaddress.ip_address(address).is_reserved or ipaddress.ip_address(address).is_unspecified for address in addresses):raise HTTPException(422,"unsafe_webhook_destination")
    return value
def auth_rate(request:Request,action:str):
    identity=request.client.host if request.client else "unknown";now=time.time();bucket=rate_buckets[("auth",action,identity)]
    while bucket and bucket[0]<now-60:bucket.popleft()
    limit=int(os.getenv("KLYROW_AUTH_RATE_PER_MINUTE","10"))
    if len(bucket)>=limit:raise HTTPException(429,"rate_limit_exceeded")
    bucket.append(now)
def auth(request:Request,authorization:str=Header(default=""),x_klyrow_tenant_id:Optional[str]=Header(default=None),s:Session=Depends(db)):
    if not authorization.startswith("Bearer "): raise HTTPException(401,"authentication_required")
    raw=authorization[7:]
    try:
        resolver=os.getenv("KLYROW_TENANT_RESOLVER_URL","").strip()
        if resolver:
            if any(name.lower() in {"x-codestra-tenant-id","x-codestra-identity-id","x-codestra-tenant","x-codestra-subject"} for name in request.headers):raise HTTPException(403,"not_found")
            permission="klyrow.webhook" if "webhook" in request.url.path else "klyrow.send" if request.method not in {"GET","HEAD","OPTIONS"} else "klyrow.read"
            headers={"Authorization":"Bearer "+raw,"X-Codestra-Required-Permission":permission}
            if x_klyrow_tenant_id:headers["X-Klyrow-Tenant-Id"]=x_klyrow_tenant_id
            response=httpx.get(resolver,headers=headers,timeout=5,follow_redirects=False)
            if response.status_code==401:raise HTTPException(401,"invalid_credentials")
            if response.status_code==404:raise HTTPException(404,"not_found")
            if response.status_code!=200:raise HTTPException(403,"not_found")
            resolved=response.json()
            if not resolved.get("authorized") or resolved.get("permission")!=permission:raise HTTPException(403,"not_found")
            ctx={"sub":resolved["identity_id"],"tenant":resolved["tenant_id"],"role":resolved.get("role","tenant_user"),"service":True,"permissions":[permission]}
            tenant=s.get(Tenant,ctx["tenant"])
            if not tenant or not tenant.enabled:raise HTTPException(403,"tenant_suspended")
        else:
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
                header=jwt.get_unverified_header(raw)
                if header.get("alg")=="HS256":
                    if os.getenv("KLYROW_ENV","development").lower()=="production" or os.getenv("KLYROW_LOCAL_AUTH_ENABLED","true").lower()!="true":raise HTTPException(401,"canonical_oidc_required")
                    ctx=jwt.decode(raw,SECRET,algorithms=["HS256"])
                    from .saas import SessionRecord
                    session=s.get(SessionRecord,ctx.get("sid")) if ctx.get("sid") else None
                    if ctx.get("sid") and (not session or session.revoked):raise HTTPException(401,"session_revoked")
                else:
                    issuer="https://auth.codestra.co/realms/codestra"
                    if os.getenv("KLYROW_OIDC_ISSUER",issuer)!=issuer:raise HTTPException(503,"canonical_oidc_misconfigured")
                    client=_jwks_clients.setdefault(issuer,PyJWKClient(issuer+"/protocol/openid-connect/certs",cache_keys=True,lifespan=300))
                    signing_key=client.get_signing_key_from_jwt(raw)
                    audience=os.getenv("KLYROW_OIDC_AUDIENCE","klyrow-api")
                    claims=jwt.decode(raw,signing_key.key,algorithms=["RS256","ES256"],audience=audience,issuer=issuer,options={"require":["exp","iat","sub","iss","aud"]})
                    from .tenancy import OidcIdentity,TenantMember
                    identity=s.scalar(select(OidcIdentity).where(OidcIdentity.issuer==issuer,OidcIdentity.subject==claims["sub"],OidcIdentity.enabled==True))
                    if not identity:raise HTTPException(403,"oidc_identity_not_registered")
                    tenant_id=x_klyrow_tenant_id or identity.default_tenant_id
                    membership=s.scalar(select(TenantMember).where(TenantMember.tenant_id==tenant_id,TenantMember.user_id==identity.user_id,TenantMember.active==True)) if tenant_id else None
                    if not membership:raise HTTPException(403,"tenant_membership_required")
                    ctx={"sub":identity.user_id,"oidc_sub":claims["sub"],"tenant":tenant_id,"role":membership.role,"identity_type":identity.identity_type,"scopes":set(str(claims.get("scope","")).split())}
                tenant=s.get(Tenant,ctx["tenant"])
                if not tenant or not tenant.enabled:raise HTTPException(403,"account_suspended")
    except HTTPException: raise
    except Exception: raise HTTPException(401,"invalid_credentials")
    now=time.time(); q=rate_buckets[ctx["tenant"]]
    while q and q[0]<now-60:q.popleft()
    if len(q)>=int(os.getenv("KLYROW_RATE_PER_MINUTE","60")): raise HTTPException(429,"rate_limit_exceeded")
    q.append(now); return ctx

def beyvra_service_auth(authorization:str=Header(default=""),x_service_identity:str=Header(default=""),x_service_scopes:str=Header(default=""),s:Session=Depends(db)):
    """Dedicated Server A identity that grants email send/status only."""
    token_file=os.getenv("BEYVRA_EMAIL_SERVICE_TOKEN_FILE","")
    try: expected=Path(token_file).read_text(encoding="utf-8").strip()
    except OSError: raise HTTPException(503,"service_identity_unavailable")
    supplied=authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    scopes=set(x_service_scopes.split())
    if not expected or not hmac.compare_digest(supplied,expected):raise HTTPException(401,"invalid_service_identity")
    if x_service_identity!="codestra-server-a:beyvra-email-production":raise HTTPException(403,"wrong_service_identity")
    if "email.send" not in scopes:raise HTTPException(403,"email_send_scope_required")
    tenant_id=os.getenv("BEYVRA_EMAIL_TENANT_ID","");tenant=s.get(Tenant,tenant_id) if tenant_id else None
    if not tenant or not tenant.enabled:raise HTTPException(403,"beyvra_tenant_unavailable")
    return {"sub":"beyvra-email-production","tenant":tenant.id,"role":"email_service","service":True,"scopes":scopes}
def require(*roles):
    def inner(ctx=Depends(auth)):
        if ctx["role"] not in roles: raise HTTPException(403,"insufficient_role")
        return ctx
    return inner

def canary_configuration()->tuple[str,str,str,int]:
    try:maximum=int(os.getenv("KLYROW_CANARY_MAX_DELIVERIES","0"))
    except (TypeError,ValueError):maximum=-1
    return (os.getenv("KLYROW_CANARY_ALLOWED_DOMAIN","").lower(),os.getenv("KLYROW_CANARY_ALLOWED_SENDER","").lower(),os.getenv("KLYROW_CANARY_ALLOWED_RECIPIENT","").lower(),maximum)

def canary_gate_key()->str:return os.getenv("KLYROW_CANARY_GATE_KEY","klyrow-single-domain")

def canary_configuration_valid()->bool:
    domain,sender,recipient,maximum=canary_configuration()
    return bool(domain and sender and recipient and maximum==1 and sender.endswith("@"+domain))

def production_gate_open(s:Session)->bool:
    if SAFE_MODE or os.getenv("KLYROW_PRODUCTION_GATE_APPROVED","false").lower()!="true" or not canary_configuration_valid():return False
    gate=s.get(ProductionCanaryGate,canary_gate_key())
    maximum=canary_configuration()[3]
    return bool(gate and gate.reserved_deliveries<maximum and gate.claimed_deliveries<=gate.reserved_deliveries)

def canary_payload_allowed(payload:dict)->bool:
    domain,sender,recipient,maximum=canary_configuration()
    recipients=payload.get("to")
    normalized_recipients=[value.lower() for value in recipients] if isinstance(recipients,list) and all(isinstance(value,str) for value in recipients) else []
    allowed_campaign=os.getenv("KLYROW_CANARY_ALLOWED_CAMPAIGN","")
    return canary_configuration_valid() and bool(allowed_campaign) and payload.get("campaign_id")==allowed_campaign and payload.get("from","").lower()==sender and normalized_recipients==[recipient]

def enforce_production_canary(x,s):
    if SAFE_MODE:return
    domain,sender,recipient,maximum=canary_configuration()
    if not canary_configuration_valid():raise HTTPException(503,"production_canary_configuration_invalid")
    allowed_campaign=os.getenv("KLYROW_CANARY_ALLOWED_CAMPAIGN","")
    if x.stream!="transactional" or not allowed_campaign or x.campaign_id!=allowed_campaign:raise HTTPException(403,"canary_campaign_denied")
    if x.sender.lower()!=sender or x.sender.lower().rsplit("@",1)[1]!=domain:raise HTTPException(403,"canary_sender_denied")
    if str(x.to).lower()!=recipient:raise HTTPException(403,"canary_recipient_denied")
    gate=s.scalar(select(ProductionCanaryGate).where(ProductionCanaryGate.gate_key==canary_gate_key()).with_for_update())
    if not gate:raise HTTPException(503,"production_canary_ledger_missing")
    if gate.reserved_deliveries>=maximum:raise HTTPException(409,"production_canary_limit_reached")
    gate.reserved_deliveries+=1;gate.updated_at=datetime.now(timezone.utc)

class Login(BaseModel): email:EmailStr; password:str; otp:Optional[str]=None
class ResetRequest(BaseModel): email:EmailStr
class Reset(BaseModel): token:str; password:str=Field(min_length=14)
class KeyIn(BaseModel): name:str=Field(min_length=1,max_length=80)
class DomainIn(BaseModel): domain:str=Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")
class MailIn(BaseModel):
    customer_id:Optional[str]=None; to:EmailStr; sender:EmailStr; reply_to:Optional[EmailStr]=None; subject:str=Field(max_length=998); html:str=Field(max_length=100000); text:Optional[str]=None; template_id:Optional[str]=None; campaign_id:Optional[str]=None; tags:list[str]=Field(default_factory=list,max_length=50); tracking:dict=Field(default_factory=dict); callback_metadata:dict=Field(default_factory=dict); stream:str=Field(default="transactional",pattern="^(marketing|transactional|security|system|bulk)$"); topic:str="marketing"
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

async def emit_middleware(event_type:str,payload:dict)->bool:
    base=os.getenv("KLYROW_MIDDLEWARE_URL","").rstrip("/"); key=os.getenv("KLYROW_MIDDLEWARE_API_KEY",""); secret=os.getenv("KLYROW_WEBHOOK_SECRET","")
    if not base or not key or not secret:return False
    event_id=payload.get("event_id") or str(uuid.uuid4()); payload={"event_id":event_id,"source_system":"klyrow","event_type":event_type,"timestamp":datetime.now(timezone.utc).isoformat(),**payload}
    body=json.dumps(payload,separators=(",",":"),sort_keys=True).encode(); ts=str(int(time.time())); canonical=ts.encode()+b"\n"+event_id.encode()+b"\nklyrow\n"+body
    signature=hmac.new(secret.encode(),canonical,hashlib.sha256).hexdigest(); headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","X-Source-System":"klyrow","X-Klyrow-Timestamp":ts,"X-Klyrow-Event-Id":event_id,"X-Klyrow-Signature":"sha256="+signature}
    path={"klyrow.email.bounced":"bounces","klyrow.email.complained":"complaints","klyrow.email.unsubscribed":"unsubscribes"}.get(event_type,"events")
    targets=[f"{base}/api/v1/klyrow/{path}"]
    email_target=os.getenv("KLYROW_EMAIL_EVENT_URL","").strip()
    if email_target:targets.append(email_target)
    try:
        if any(not target.lower().startswith("https://") for target in targets):
            raise RuntimeError("plaintext_middleware_target_denied")
        ca_file=os.getenv("KLYROW_SERVER_A_CA_FILE","").strip()
        cert_file=os.getenv("KLYROW_SERVER_A_CLIENT_CERT_FILE","").strip()
        key_file=os.getenv("KLYROW_SERVER_A_CLIENT_KEY_FILE","").strip()
        if not ca_file or not cert_file or not key_file:
            raise RuntimeError("middleware_mtls_material_required")
        for path_value in (ca_file,cert_file,key_file):
            if not Path(path_value).is_file():raise RuntimeError("middleware_mtls_material_unavailable")
        tls_context=ssl.create_default_context(cafile=ca_file)
        tls_context.minimum_version=ssl.TLSVersion.TLSv1_2
        tls_context.load_cert_chain(certfile=cert_file,keyfile=key_file)
        async with httpx.AsyncClient(timeout=3,trust_env=False,verify=tls_context) as client:
            for target in targets:
                response=await client.post(target,headers=headers,content=body)
                response.raise_for_status()
        return True
    except Exception as exc:
        print(json.dumps({"level":"warning","system":"klyrow","event_id":event_id,"message_id":payload.get("message_id"),"event":"middleware_delivery_failed","error":type(exc).__name__}))
        return False

POSTAL_EVENTS={
    "MessageSent":"email.delivered", "MessageDeliveryFailed":"email.bounced",
    "MessageBounced":"email.bounced", "MessageDelayed":"email.deferred",
    "MessageHeld":"email.held", "MessageLoaded":"email.opened",
    "MessageLinkClicked":"email.clicked",
}

TERMINAL_MESSAGE_STATUSES={
    "email.sent":"sent", "email.delivered":"delivered", "email.soft_bounce":"soft_bounce",
    "email.deferred":"soft_bounce",
    "email.hard_bounce":"hard_bounce", "email.bounced":"hard_bounce",
    "email.complained":"complaint", "email.complaint":"complaint",
    "email.rejected":"rejected", "email.failed":"failed",
}
SUPPRESSION_STATUSES={"hard_bounce", "complaint"}

def persist_email_event(s:Session, *, event_id:str, tenant_id:str, message_id:str, correlation_id:str, event_type:str, recipient:Optional[str], raw_status:Optional[str], payload:str):
    canonical_status=TERMINAL_MESSAGE_STATUSES.get(event_type,event_type.rsplit(".",1)[-1])
    local_message=s.get(Message,message_id) or s.get(Message,correlation_id)
    if local_message:local_message.status=canonical_status
    from .provider import ProviderMessage
    provider_message=s.scalar(select(ProviderMessage).where(ProviderMessage.tenant_id==tenant_id,
        or_(ProviderMessage.id==message_id,ProviderMessage.provider_message_id==message_id,
            ProviderMessage.correlation_id==correlation_id)))
    if provider_message:
        provider_status={"sent":"SENT","delivered":"DELIVERED","soft_bounce":"BOUNCED_SOFT",
            "hard_bounce":"BOUNCED_HARD","complaint":"COMPLAINED","failed":"FAILED",
            "rejected":"FAILED"}.get(canonical_status,canonical_status.upper())
        if provider_status in {"SENT","DELIVERED","BOUNCED_SOFT","BOUNCED_HARD","COMPLAINED","FAILED","DEFERRED"}:
            provider_message.status=provider_status;provider_message.updated_at=datetime.now(timezone.utc)
    if not s.get(Event,event_id):
        s.add(Event(id=event_id,tenant_id=tenant_id,message_id=local_message.id if local_message else message_id,kind="klyrow."+event_type,payload=payload))
        s.add(Audit(id=str(uuid.uuid4()),tenant_id=tenant_id,actor="provider:postal",action="email.status."+canonical_status))
    if canonical_status in SUPPRESSION_STATUSES and recipient:
        email=recipient.lower()
        suppression=s.scalar(select(Suppression).where(Suppression.tenant_id==tenant_id,Suppression.email==email))
        if not suppression:s.add(Suppression(id=str(uuid.uuid4()),tenant_id=tenant_id,email=email,reason=canonical_status))
        elif suppression.reason!=canonical_status:suppression.reason=canonical_status
    s.commit()
    return canonical_status

def verify_postal_signature(body:bytes,signature:str):
    key_path=os.getenv("KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY","")
    if not key_path or not signature:raise HTTPException(401,"postal_signature_required")
    try:
        public_key=serialization.load_pem_public_key(Path(key_path).read_bytes())
        public_key.verify(base64.b64decode(signature,validate=True),body,padding.PKCS1v15(),hashes.SHA256())
    except (OSError,ValueError,TypeError,InvalidSignature):raise HTTPException(401,"invalid_postal_signature")

@app.post("/v1/webhooks/postal-native",status_code=202)
async def postal_native_hook(request:Request,x_postal_signature_256:str=Header(default=""),s:Session=Depends(db)):
    body=await request.body(); verify_postal_signature(body,x_postal_signature_256)
    try: raw=json.loads(body)
    except ValueError:raise HTTPException(400,"invalid_json")
    event_id=str(raw.get("uuid") or "")
    if not event_id:raise HTTPException(400,"event_id_required")
    try: event_timestamp=float(raw.get("timestamp"))
    except (TypeError,ValueError):raise HTTPException(401,"invalid_postal_timestamp")
    # Postal's native retry schedule can legitimately deliver an older event;
    # reject future timestamps and stale captures outside one bounded day.
    if event_timestamp>time.time()+300 or event_timestamp<time.time()-86400:raise HTTPException(401,"expired_postal_event")
    event_name=str(raw.get("event") or ""); canonical=POSTAL_EVENTS.get(event_name)
    if not canonical:raise HTTPException(422,"unsupported_postal_event")
    payload=raw.get("payload") or {}; message=payload.get("message") or payload.get("original_message") or {}
    tenant=os.getenv("KLYROW_POSTAL_TENANT_ID","")
    if not tenant:raise HTTPException(503,"postal_tenant_not_configured")
    message_id=str(message.get("id") or message.get("message_id") or "")
    correlation=str(payload.get("correlation_id") or message.get("tag") or message.get("message_id") or event_id)
    normalized={"event":canonical,"event_id":event_id,"tenant_id":tenant,"message_id":message_id,"correlation_id":correlation,"recipient":message.get("to"),"sender":message.get("from"),"provider":"postal","status":payload.get("status"),"occurred_at":event_timestamp,"provider_event":event_name,"provider_message_token":message.get("token")}
    item=s.get(PostalEvent,event_id)
    if item and item.state=="delivered":return {"accepted":True,"duplicate":True}
    if not item:
        item=PostalEvent(id=event_id,event_type=canonical,correlation_id=correlation,message_id=message_id,tenant_id=tenant,payload=json.dumps(normalized,separators=(",",":"),sort_keys=True)); s.add(item)
    item.attempts=(item.attempts or 0)+1; item.updated_at=datetime.now(timezone.utc); s.commit()
    canonical_status=persist_email_event(s,event_id=event_id,tenant_id=tenant,message_id=message_id,correlation_id=correlation,event_type=canonical,recipient=normalized.get("recipient"),raw_status=normalized.get("status"),payload=item.payload)
    normalized["canonical_status"]=canonical_status
    delivered=await emit_middleware("klyrow."+canonical,{**normalized,"customer_id":tenant})
    item=s.get(PostalEvent,event_id)
    if delivered:
        item.state="delivered"; item.last_error=None; s.commit(); MAIL.labels(canonical.rsplit(".",1)[-1]).inc(); return {"accepted":True}
    item.state="dlq" if item.attempts>=5 else "retry"; item.last_error="middleware_delivery_failed"; s.commit()
    raise HTTPException(503,"middleware_delivery_pending")

@app.on_event("startup")
def startup():
    if os.getenv("KLYROW_ENV","development").lower()=="production":
        required=os.getenv("KLYROW_REQUIRED_SCHEMA_VERSION","")
        if not required:raise RuntimeError("production requires KLYROW_REQUIRED_SCHEMA_VERSION")
        with engine.connect() as connection:
            present=connection.execute(text("SELECT count(*) FROM klyrow_schema_migrations WHERE version=:version"),{"version":required}).scalar_one()
        if present!=1:raise RuntimeError("required database migration is not applied")
    else:
        Base.metadata.create_all(engine)
    with DB() as s:
        if not s.scalar(select(User).limit(1)):
            email=os.getenv("KLYROW_ADMIN_EMAIL"); password=os.getenv("KLYROW_ADMIN_PASSWORD")
            if email and password and len(password)>=14:
                t=Tenant(id=str(uuid.uuid4()),name="Klyrow",quota=int(os.getenv("KLYROW_DAILY_QUOTA","10000"))); s.add(t); s.add(User(id=str(uuid.uuid4()),tenant_id=t.id,email=email.lower(),password_hash=ph.hash(password),role="platform_admin")); s.commit()

async def postal_retry_loop():
    while True:
        await asyncio.sleep(5)
        try:
            with DB() as s:
                pending=list(s.scalars(select(PostalEvent).where(PostalEvent.state=="retry",PostalEvent.attempts<5).order_by(PostalEvent.updated_at).limit(20)).all())
            for snapshot in pending:
                updated=snapshot.updated_at
                if updated.tzinfo is None:updated=updated.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc)-updated).total_seconds()<min(60,2**max(snapshot.attempts,1)):continue
                payload=json.loads(snapshot.payload)
                delivered=await emit_middleware("klyrow."+snapshot.event_type,{**payload,"customer_id":snapshot.tenant_id})
                with DB() as s:
                    item=s.get(PostalEvent,snapshot.id)
                    if not item or item.state!="retry":continue
                    item.attempts=(item.attempts or 0)+1;item.updated_at=datetime.now(timezone.utc)
                    if delivered:
                        item.state="delivered";item.last_error=None
                    elif item.attempts>=5:
                        item.state="dlq";item.last_error="middleware_delivery_failed"
                    s.commit()
        except Exception as exc:
            print(json.dumps({"level":"warning","system":"klyrow","event":"postal_retry_worker_error","error":type(exc).__name__}))

async def email_outbox_loop():
    while True:
        await asyncio.sleep(2)
        if SAFE_MODE:continue
        snapshot=None
        try:
            with DB() as s:
                stale=datetime.now(timezone.utc)-timedelta(minutes=5)
                current=datetime.now(timezone.utc)
                item=s.scalar(select(EmailOutbox).where(or_(EmailOutbox.state=="pending",(EmailOutbox.state=="retry") & (or_(EmailOutbox.next_attempt_at.is_(None),EmailOutbox.next_attempt_at<=current)),(EmailOutbox.state=="sending") & (EmailOutbox.updated_at<stale)),EmailOutbox.attempts<5).order_by(EmailOutbox.created_at).with_for_update(skip_locked=True))
                if not item:continue
                try:payload=json.loads(item.payload)
                except (TypeError,ValueError):
                    item.state="quarantined";item.last_error="invalid_outbox_payload";item.updated_at=current;s.commit();continue
                if not isinstance(payload,dict):
                    item.state="quarantined";item.last_error="invalid_outbox_payload";item.updated_at=current;s.commit();continue
                gate=s.scalar(select(ProductionCanaryGate).where(ProductionCanaryGate.gate_key==canary_gate_key()).with_for_update())
                maximum=canary_configuration()[3]
                first_attempt=(item.attempts or 0)==0
                reservation_denied=(not gate or (first_attempt and
                    (gate.claimed_deliveries>=gate.reserved_deliveries or gate.claimed_deliveries>=maximum)))
                if not canary_payload_allowed(payload) or reservation_denied:
                    item.state="quarantined";item.last_error="production_canary_policy_denied";item.updated_at=current
                    message=s.get(Message,item.message_id)
                    if message:message.status="quarantined"
                    s.commit();continue
                if first_attempt:
                    gate.claimed_deliveries+=1;gate.updated_at=current
                item.state="sending";item.attempts+=1;item.next_attempt_at=None;item.updated_at=current;snapshot=(item.id,item.message_id,item.payload);s.commit()
            key_file=os.getenv("KLYROW_POSTAL_API_KEY_FILE","")
            key=Path(key_file).read_text(encoding="utf-8").strip() if key_file else ""
            if not key:raise RuntimeError("postal credential unavailable")
            headers={"X-Server-API-Key":key,"Idempotency-Key":"klyrow:"+snapshot[1]}
            async with httpx.AsyncClient(timeout=10,trust_env=False,follow_redirects=False) as client:
                response=await client.post(os.environ["KLYROW_POSTAL_API_URL"]+"/api/v1/send/message",headers=headers,json=json.loads(snapshot[2]));response.raise_for_status();provider_id=str(response.json().get("data",{}).get("message_id") or snapshot[1])
            with DB() as s:
                item=s.get(EmailOutbox,snapshot[0]);message=s.get(Message,snapshot[1])
                if item:item.state="delivered";item.provider_message_id=provider_id;item.last_error=None;item.updated_at=datetime.now(timezone.utc)
                if message:message.status="accepted"
                s.commit()
        except Exception as exc:
            with DB() as s:
                if snapshot is not None:
                    item=s.get(EmailOutbox,snapshot[0])
                    if item:
                        failed=item.attempts>=5;item.state="failed" if failed else "retry";item.last_error=type(exc).__name__;item.updated_at=datetime.now(timezone.utc);item.next_attempt_at=None if failed else item.updated_at+timedelta(seconds=min(300,2**max(item.attempts,1)))
                        if failed:
                            message=s.get(Message,item.message_id)
                            if message:message.status="failed"
                            s.add(Event(id=str(uuid.uuid4()),tenant_id=item.tenant_id,message_id=item.message_id,kind="klyrow.email.failed",payload=json.dumps({"reason":"provider_retry_exhausted"})))
                        s.commit()
            print(json.dumps({"level":"warning","system":"klyrow","event":"email_outbox_delivery_failed","error":type(exc).__name__}))

@app.on_event("startup")
async def start_postal_retry_worker():
    asyncio.create_task(postal_retry_loop())
    asyncio.create_task(email_outbox_loop())

@app.middleware("http")
async def headers(request, call_next):
    started=time.monotonic();request_id=request.headers.get("X-Request-Id") or str(uuid.uuid4())
    try: response=await call_next(request)
    except Exception: REQUESTS.labels(request.url.path,"500").inc(); raise
    response.headers.update({"X-Request-Id":request_id,"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Permissions-Policy":"camera=(), microphone=(), geolocation=()","Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"})
    REQUESTS.labels(request.url.path,str(response.status_code)).inc();LATENCY.labels(request.url.path).observe(time.monotonic()-started); return response

@app.get("/v1/health")
def health(s:Session=Depends(db)):
    s.execute(select(1));active=s.scalar(select(func.count()).select_from(EmailOutbox).where(EmailOutbox.state.in_(("pending","sending","retry"))))
    return {"status":"ok","safe_mode":SAFE_MODE,"production_gate_approved":os.getenv("KLYROW_PRODUCTION_GATE_APPROVED","false").lower()=="true","production_gate_open":production_gate_open(s),"database":"healthy","outbox":"healthy","outbox_active":active}
@app.get("/healthz")
def healthz(s:Session=Depends(db)):s.execute(select(1));return {"status":"ok"}
@app.get("/readyz")
def readyz(s:Session=Depends(db)):s.execute(select(1));return {"status":"ready","safe_mode":SAFE_MODE}
@app.get("/version")
def version():
    return {
        "service":"klyrow-gateway",
        "version":os.getenv("KLYROW_RELEASE_VERSION","development"),
        "revision":os.getenv("KLYROW_RELEASE_SHA","unknown"),
    }
@app.get("/metrics")
def metrics(authorization:str=Header(default="")):
    token_file=os.getenv("KLYROW_METRICS_TOKEN_FILE","")
    try:expected=Path(token_file).read_text(encoding="utf-8").strip()
    except OSError:raise HTTPException(404,"not_found")
    supplied=authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    if not expected or not hmac.compare_digest(supplied,expected):raise HTTPException(404,"not_found")
    from .provider import ProviderEvent, ProviderMessage, ProviderUsageEvent
    from .billing import Invoice,Payment,Refund,expected_invoice_status,money
    from .messaging import DomainClaim,WebhookAttempt
    from .operations import IntegrationOutbox
    with DB() as s:
        for status in ("QUEUED","PROCESSING","DEFERRED","FAILED","DEAD_LETTER"):
            PROVIDER_QUEUE.labels(status).set(s.scalar(select(func.count()).select_from(ProviderMessage).where(ProviderMessage.status==status)) or 0)
        for state in ("PENDING","RETRY","DELIVERED","DEAD_LETTER"):
            PROVIDER_EVENTS.labels(state).set(s.scalar(select(func.count()).select_from(ProviderEvent).where(ProviderEvent.state==state)) or 0)
            PROVIDER_USAGE.labels(state).set(s.scalar(select(func.count()).select_from(ProviderUsageEvent).where(ProviderUsageEvent.state==state)) or 0)
        active=s.scalars(select(EmailOutbox).where(EmailOutbox.state.in_(("pending","sending","retry")))).all()
        ages=[]
        for item in active:
            created=item.created_at if item.created_at.tzinfo else item.created_at.replace(tzinfo=timezone.utc)
            ages.append(max(0,(datetime.now(timezone.utc)-created).total_seconds()))
        OUTBOX_OLDEST.set(max(ages,default=0))
        for target in ("N8N","ODOO"):
            for state in ("PENDING","RETRY","COMPLETED","DEAD_LETTER"):
                INTEGRATION_QUEUE.labels(target,state).set(s.scalar(select(func.count()).select_from(IntegrationOutbox).where(IntegrationOutbox.target==target,IntegrationOutbox.state==state)) or 0)
        for state in ("PENDING","RETRY","DELIVERED","DEAD_LETTER"):
            WEBHOOK_QUEUE.labels(state).set(s.scalar(select(func.count()).select_from(WebhookAttempt).where(WebhookAttempt.state==state)) or 0)
        total=s.scalar(select(func.count()).select_from(Message)) or 0
        for outcome,kinds in {"delivered":("email.delivered","klyrow.email.delivered"),"bounced":("email.bounced","klyrow.email.bounced"),"complained":("email.complained","klyrow.email.complained")}.items():
            count=s.scalar(select(func.count()).select_from(Event).where(Event.kind.in_(kinds))) or 0
            DELIVERY_RATE.labels(outcome).set(count/total if total else 0)
        DNS_INVALID.set(s.scalar(select(func.count()).select_from(DomainClaim).where(DomainClaim.state.notin_(("VERIFIED","SENDING_ENABLED")))) or 0)
        drift=0
        for invoice in s.scalars(select(Invoice)).all():
            paid=money(s.scalar(select(func.sum(Payment.amount)).where(Payment.invoice_id==invoice.id,Payment.status=="CONFIRMED")) or 0)
            refunded=money(s.scalar(select(func.sum(Refund.amount)).where(Refund.payment_id.in_(select(Payment.id).where(Payment.invoice_id==invoice.id)),Refund.status=="CONFIRMED")) or 0)
            expected=expected_invoice_status(invoice.status,invoice.total,paid,refunded)
            drift+=int(invoice.status!=expected)
        BILLING_DRIFT.set(drift)
    from fastapi.responses import Response; return Response(generate_latest(),media_type="text/plain")
@app.post("/v1/auth/login")
def login(x:Login,request:Request,s:Session=Depends(db)):
    if os.getenv("KLYROW_ENV","development").lower()=="production" or os.getenv("KLYROW_LOCAL_AUTH_ENABLED","true").lower()!="true":raise HTTPException(410,"use_canonical_oidc")
    auth_rate(request,"login")
    u=s.scalar(select(User).where(User.email==x.email.lower()))
    try: valid=u and u.enabled and ph.verify(u.password_hash,x.password)
    except Exception: valid=False
    if not valid: raise HTTPException(401,"invalid_credentials")
    from .saas import MfaConfig,verify_totp
    m=s.get(MfaConfig,u.id)
    if m and m.enabled and (not x.otp or not verify_totp(m.secret,x.otp)):raise HTTPException(401,"mfa_required")
    audit(s,{"tenant":u.tenant_id,"sub":u.id},"session.login");s.commit();return {"access_token":token(u,s),"token_type":"bearer","role":u.role,"tenant_id":u.tenant_id}
@app.post("/v1/auth/logout",status_code=204)
def logout(ctx=Depends(auth),s:Session=Depends(db)):
    from .saas import SessionRecord
    if ctx.get("sid"):
        session=s.get(SessionRecord,ctx["sid"])
        if session:session.revoked=True;audit(s,ctx,"session.logout");s.commit()
    return None
@app.post("/v1/auth/forgot-password",status_code=202)
def forgot(x:ResetRequest,request:Request,s:Session=Depends(db)):
    auth_rate(request,"forgot-password")
    u=s.scalar(select(User).where(User.email==x.email.lower()))
    if u: raw=secrets.token_urlsafe(32); u.reset_hash=sha(raw); u.reset_expires=datetime.now(timezone.utc)+timedelta(minutes=30);audit(s,{"tenant":u.tenant_id,"sub":u.id},"password.reset.requested");s.commit()
    return {"detail":"If the account exists, reset instructions will be delivered."}
@app.post("/v1/auth/reset-password")
def reset(x:Reset,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.reset_hash==sha(x.token)))
    if not u or not u.reset_expires or u.reset_expires.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise HTTPException(400,"invalid_or_expired_token")
    u.password_hash=ph.hash(x.password); u.reset_hash=None; u.reset_expires=None
    from .saas import SessionRecord
    for session in s.scalars(select(SessionRecord).where(SessionRecord.user_id==u.id,SessionRecord.revoked==False)).all():session.revoked=True
    audit(s,{"tenant":u.tenant_id,"sub":u.id},"password.reset.sessions_revoked");s.commit(); return {"status":"reset"}
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
@app.post("/v1/messages",status_code=202)
@app.post("/v1/email/send",status_code=202,include_in_schema=False)
async def send(x:MailIn,ctx=Depends(auth),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    return await _send(x,ctx,s,idempotency_key)

@app.post("/v1/internal/email/beyvra/send",status_code=202)
async def beyvra_send(x:MailIn,ctx=Depends(beyvra_service_auth),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    if x.stream!="transactional":raise HTTPException(403,"transactional_only")
    allowed={"no-reply@beyvra.com","security@beyvra.com","trading@beyvra.com","statements@beyvra.com","support@beyvra.com"}
    if x.sender.lower() not in allowed:raise HTTPException(403,"sender_spoofing_denied")
    return await _send(x,ctx,s,idempotency_key)

async def _send(x:MailIn,ctx,s,idempotency_key):
    if not idempotency_key: raise HTTPException(400,"idempotency_key_required")
    from .operations import enforce_tenant_send_gate
    enforce_tenant_send_gate(s,ctx["tenant"])
    from .agent_mailboxes import authorize_agent_sender
    authorize_agent_sender(s,ctx,x.sender,x.campaign_id,x.reply_to)
    request_hash=sha(x.model_dump_json())
    prior=s.scalar(select(Idempotency).where(Idempotency.key==idempotency_key,Idempotency.tenant_id==ctx["tenant"]))
    if prior:
        if prior.request_hash!=request_hash:raise HTTPException(409,"idempotency_key_payload_mismatch")
        return json.loads(prior.response_json)
    enforce_production_canary(x,s)
    from .preferences import enforce_suppression
    enforce_suppression(s,ctx["tenant"],x.to.lower(),x.stream,x.campaign_id)
    from .saas import Consent,Preference,Profile,UsageLedger
    profile=s.scalar(select(Profile).where(Profile.tenant_id==ctx["tenant"],Profile.email==x.to.lower()))
    if x.stream=="marketing":
        if not profile:raise HTTPException(422,"marketing_consent_required")
        pref=s.scalar(select(Preference).where(Preference.tenant_id==ctx["tenant"],Preference.profile_id==profile.id,Preference.topic==x.topic))
        latest=s.scalar(select(Consent).where(Consent.tenant_id==ctx["tenant"],Consent.profile_id==profile.id,Consent.topic==x.topic).order_by(Consent.occurred_at.desc()))
        if not pref or not pref.subscribed or not latest or latest.status!="granted":raise HTTPException(422,"marketing_consent_required")
    sender=x.sender.lower();domain=sender.rsplit("@",1)[1]
    from .delivery_controls import enforce_delivery_controls
    enforce_delivery_controls(s,ctx["tenant"],sender,x.stream)
    allowed=s.scalar(select(Domain).where(Domain.tenant_id==ctx["tenant"],Domain.domain==domain,Domain.verified==True))
    if not allowed: raise HTTPException(422,"sender_domain_not_verified")
    if ctx.get("role")!="codestra-email-agent":
        exact=s.scalar(select(AllowedSender).where(AllowedSender.tenant_id==ctx["tenant"],AllowedSender.address==sender,AllowedSender.enabled==True))
        if not exact:raise HTTPException(403,"sender_address_not_allowed")
    since=datetime.now(timezone.utc)-timedelta(days=1); count=len(s.scalars(select(Message).where(Message.tenant_id==ctx["tenant"],Message.created_at>=since)).all()); tenant=s.get(Tenant,ctx["tenant"])
    if count>=tenant.quota: raise HTTPException(429,"daily_quota_exceeded")
    mid=str(uuid.uuid4()); status="accepted_test" if SAFE_MODE else "queued"
    result={"id":mid,"provider_message_id":mid,"status":status,"safe_mode":SAFE_MODE,"stream":x.stream}; s.add(Message(id=mid,tenant_id=ctx["tenant"],recipient=x.to.lower(),sender=x.sender.lower(),subject=x.subject,status=status)); s.add(Event(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],message_id=mid,kind="klyrow.email.queued",payload=json.dumps({"stream":x.stream}))); s.add(Idempotency(key=idempotency_key,tenant_id=ctx["tenant"],request_hash=request_hash,resource_id=mid,response_json=json.dumps(result)));s.add(UsageLedger(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],kind="message."+x.stream,quantity=1,reference=mid))
    if not SAFE_MODE:s.add(EmailOutbox(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],message_id=mid,payload=json.dumps({"to":[str(x.to)],"from":str(x.sender),"subject":x.subject,"html_body":x.html,"plain_body":x.text,"campaign_id":x.campaign_id},separators=(",",":"),sort_keys=True)))
    s.commit(); MAIL.labels("queued").inc(); await emit_middleware("klyrow.email.queued",{"customer_id":ctx["tenant"],"message_id":mid,"recipient":x.to.lower(),"sender":x.sender.lower(),"status":status,"provider":"postal","metadata":{"stream":x.stream}}); return result

@app.post("/v1/email/bulk",status_code=202)
async def bulk(x:BulkMailIn,ctx=Depends(auth),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    if not SAFE_MODE:raise HTTPException(403,"bulk_delivery_disabled_during_canary")
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
@app.get("/v1/messages")
def messages(ctx=Depends(auth),s:Session=Depends(db),status:Optional[str]=None,limit:int=50,offset:int=0):
    limit=max(1,min(limit,200));offset=max(0,offset);query=select(Message).where(Message.tenant_id==ctx["tenant"])
    if status:query=query.where(Message.status==status)
    return s.scalars(query.order_by(Message.created_at.desc()).offset(offset).limit(limit)).all()
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
    if s.get(Replay,x_klyrow_event_id): return {"accepted":True,"duplicate":True}
    s.add(Replay(id=x_klyrow_event_id)); payload=json.loads(body); mid=str(payload.get("message_id") or ""); tenant=payload.get("tenant_id")
    event_type=payload.get("event","klyrow.email.unknown"); event_type=event_type if event_type.startswith("klyrow.") else "klyrow."+event_type
    local_type=event_type.removeprefix("klyrow.")
    correlation=str(payload.get("correlation_id") or mid or x_klyrow_event_id)
    if tenant:persist_email_event(s,event_id=x_klyrow_event_id,tenant_id=tenant,message_id=mid,correlation_id=correlation,event_type=local_type,recipient=payload.get("recipient"),raw_status=payload.get("status"),payload=body.decode())
    else:s.commit()
    normalized={**payload,"event_id":x_klyrow_event_id,"customer_id":tenant,"canonical_status":TERMINAL_MESSAGE_STATUSES.get(local_type,local_type.rsplit(".",1)[-1])}
    delivery=s.get(PostalEvent,x_klyrow_event_id)
    if not delivery:
        delivery=PostalEvent(id=x_klyrow_event_id,event_type=local_type,correlation_id=correlation,message_id=mid,tenant_id=tenant,payload=json.dumps(normalized,separators=(",",":"),sort_keys=True),state="pending",attempts=0);s.add(delivery)
    delivery.attempts=(delivery.attempts or 0)+1;delivery.updated_at=datetime.now(timezone.utc);s.commit()
    if await emit_middleware(event_type,normalized):
        delivery=s.get(PostalEvent,x_klyrow_event_id);delivery.state="delivered";delivery.last_error=None;s.commit();return {"accepted":True,"duplicate":False}
    delivery=s.get(PostalEvent,x_klyrow_event_id);delivery.state="dlq" if delivery.attempts>=5 else "retry";delivery.last_error="middleware_delivery_failed";s.commit();raise HTTPException(503,"middleware_delivery_pending")

@app.get("/v1/contacts")
def contacts(ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Contact).where(Contact.tenant_id==ctx["tenant"])).all()
@app.post("/v1/contacts")
def contact_upsert(x:ContactIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db)):
    item=s.scalar(select(Contact).where(Contact.tenant_id==ctx["tenant"],Contact.email==x.email.lower())) or Contact(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],email=x.email.lower()); item.name=x.name; item.subscribed=x.subscribed; item.metadata_json=json.dumps(x.metadata); s.add(item); audit(s,ctx,"contact.upserted"); s.commit(); return item
@app.get("/v1/campaigns")
def campaigns(ctx=Depends(auth),s:Session=Depends(db)): return s.scalars(select(Campaign).where(Campaign.tenant_id==ctx["tenant"])).all()
@app.post("/v1/campaigns",status_code=201)
async def campaign_create(x:CampaignIn,ctx=Depends(require("platform_admin","tenant_admin")),s:Session=Depends(db),idempotency_key:Optional[str]=Header(default=None)):
    if not SAFE_MODE:raise HTTPException(403,"campaign_delivery_disabled_during_canary")
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
    url=safe_webhook_url(x.url);raw=secrets.token_urlsafe(32); item=WebhookEndpoint(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],url=url,secret_hash=sha(raw)); s.add(item); audit(s,ctx,"webhook.created"); s.commit(); return {"id":item.id,"url":item.url,"secret":raw}
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
@app.get("/admin",response_class=HTMLResponse,include_in_schema=False)
def admin_portal():return Path(__file__).with_name("admin.html").read_text()
@app.get("/assets/admin.js",include_in_schema=False)
def admin_js():return FileResponse(Path(__file__).with_name("admin.js"),media_type="application/javascript")

from .saas import router as saas_router
app.include_router(saas_router)
from .agent_mailboxes import router as agent_mailbox_router
app.include_router(agent_mailbox_router)
from .billing import router as billing_router
app.include_router(billing_router)
from .tenancy import router as tenancy_router
app.include_router(tenancy_router)
from .messaging import router as messaging_router
app.include_router(messaging_router)
from .operations import router as operations_router
app.include_router(operations_router)
from .reseller import router as reseller_router
app.include_router(reseller_router)
from .delivery_controls import router as delivery_controls_router
app.include_router(delivery_controls_router)
from .preferences import router as preferences_router
app.include_router(preferences_router)
from .provider import provider_worker_loop, reconcile_legacy_registry, router as provider_router, status_router as provider_status_router
app.include_router(provider_router)
app.include_router(provider_status_router)

@app.on_event("startup")
def reconcile_provider_registry_on_startup():
    with DB() as s:
        reconcile_legacy_registry(s)

@app.on_event("startup")
async def start_provider_worker():
    asyncio.create_task(provider_worker_loop())
