"""Durable integration, support, export, closure, and operator controls."""
import json,uuid
from datetime import datetime,timedelta,timezone
from typing import Optional

from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import Boolean,DateTime,Integer,String,Text,UniqueConstraint,func,select
from sqlalchemy.orm import Mapped,Session,mapped_column

from .main import Audit,Base,EmailOutbox,Event,Message,PostalEvent,Tenant,audit,auth,db,require
from .messaging import DeliveryJob,WebhookAttempt

router=APIRouter(prefix="/v1",tags=["Operations and integrations"]);now=lambda:datetime.now(timezone.utc)

class IntegrationOutbox(Base):
    __tablename__="integration_outbox";id:Mapped[str]=mapped_column(String,primary_key=True);tenant_id:Mapped[str]=mapped_column(String,index=True);target:Mapped[str]=mapped_column(String,index=True);event_type:Mapped[str]=mapped_column(String,index=True);aggregate_id:Mapped[str]=mapped_column(String,index=True);payload_json:Mapped[str]=mapped_column(Text);idempotency_key:Mapped[str]=mapped_column(String);state:Mapped[str]=mapped_column(String,default="PENDING",index=True);attempts:Mapped[int]=mapped_column(Integer,default=0);next_attempt_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);last_error:Mapped[Optional[str]]=mapped_column(String,nullable=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);__table_args__=(UniqueConstraint("tenant_id","target","idempotency_key",name="uq_integration_outbox_key"),)
class IntegrationResult(Base):
    __tablename__="integration_results";id:Mapped[str]=mapped_column(String,primary_key=True);tenant_id:Mapped[str]=mapped_column(String,index=True);outbox_id:Mapped[str]=mapped_column(String,index=True);source:Mapped[str]=mapped_column(String);result_key:Mapped[str]=mapped_column(String,unique=True);payload_json:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class SupportTicket(Base):
    __tablename__="support_tickets";id:Mapped[str]=mapped_column(String,primary_key=True);tenant_id:Mapped[str]=mapped_column(String,index=True);created_by:Mapped[str]=mapped_column(String);category:Mapped[str]=mapped_column(String);subject:Mapped[str]=mapped_column(String);description:Mapped[str]=mapped_column(Text);status:Mapped[str]=mapped_column(String,default="OPEN");priority:Mapped[str]=mapped_column(String,default="NORMAL");odoo_reference:Mapped[Optional[str]]=mapped_column(String,nullable=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ExportJob(Base):
    __tablename__="tenant_export_jobs";id:Mapped[str]=mapped_column(String,primary_key=True);tenant_id:Mapped[str]=mapped_column(String,index=True);requested_by:Mapped[str]=mapped_column(String);scope_json:Mapped[str]=mapped_column(Text);state:Mapped[str]=mapped_column(String,default="PENDING");object_reference:Mapped[Optional[str]]=mapped_column(String,nullable=True);expires_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AccountClosure(Base):
    __tablename__="account_closures";id:Mapped[str]=mapped_column(String,primary_key=True);tenant_id:Mapped[str]=mapped_column(String,unique=True,index=True);requested_by:Mapped[str]=mapped_column(String);state:Mapped[str]=mapped_column(String,default="REQUESTED");confirmation_hash:Mapped[str]=mapped_column(String);grace_until:Mapped[datetime]=mapped_column(DateTime(timezone=True));billing_settled:Mapped[bool]=mapped_column(Boolean,default=False);retention_policy:Mapped[str]=mapped_column(String,default="STANDARD");confirmed_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True);closed_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)
class TenantSendGate(Base):
    __tablename__="tenant_send_gates";tenant_id:Mapped[str]=mapped_column(String,primary_key=True);enabled:Mapped[bool]=mapped_column(Boolean,default=True);reason:Mapped[str]=mapped_column(String,default="ACTIVE");updated_by:Mapped[str]=mapped_column(String);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ReconciliationRun(Base):
    __tablename__="reconciliation_runs";id:Mapped[str]=mapped_column(String,primary_key=True);tenant_id:Mapped[Optional[str]]=mapped_column(String,nullable=True,index=True);kind:Mapped[str]=mapped_column(String);state:Mapped[str]=mapped_column(String);drift_count:Mapped[int]=mapped_column(Integer,default=0);details_json:Mapped[str]=mapped_column(Text,default="[]");started_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);completed_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)

class SupportIn(BaseModel):category:str=Field(pattern="^(technical|deliverability|billing|account|abuse|domain)$");subject:str=Field(min_length=3,max_length=200);description:str=Field(min_length=3,max_length=10000);priority:str=Field(default="NORMAL",pattern="^(LOW|NORMAL|HIGH|URGENT)$")
class AutomationIn(BaseModel):event_type:str=Field(min_length=3,max_length=120);aggregate_id:str=Field(min_length=1,max_length=200);payload:dict=Field(default_factory=dict);idempotency_key:str=Field(min_length=8,max_length=200)
class ResultIn(BaseModel):outbox_id:str;result_key:str=Field(min_length=8,max_length=200);payload:dict=Field(default_factory=dict)
class ExportIn(BaseModel):scopes:list[str]=Field(min_length=1,max_length=20)
class ClosureIn(BaseModel):grace_days:int=Field(default=30,ge=7,le=365);retention_policy:str=Field(default="STANDARD",pattern="^(STANDARD|LEGAL_HOLD|MINIMAL)$")
class ConfirmIn(BaseModel):confirmation:str
class KillIn(BaseModel):enabled:bool;reason:str=Field(min_length=3,max_length=300)
class RecoverIn(BaseModel):reason:str=Field(min_length=3,max_length=500)

def owned(s,model,item_id,tenant):
    item=s.scalar(select(model).where(model.id==item_id,model.tenant_id==tenant))
    if not item:raise HTTPException(404,"not_found")
    return item
def enqueue(s,ctx,target,event_type,aggregate_id,payload,key):
    prior=s.scalar(select(IntegrationOutbox).where(IntegrationOutbox.tenant_id==ctx["tenant"],IntegrationOutbox.target==target,IntegrationOutbox.idempotency_key==key))
    if prior:return prior,True
    item=IntegrationOutbox(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],target=target,event_type=event_type,aggregate_id=aggregate_id,payload_json=json.dumps(payload,separators=(",",":"),sort_keys=True),idempotency_key=key);s.add(item);return item,False

@router.post("/support/tickets",status_code=201)
def support(x:SupportIn,ctx=Depends(auth),s:Session=Depends(db)):
    ticket=SupportTicket(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],created_by=ctx["sub"],category=x.category,subject=x.subject,description=x.description,priority=x.priority);s.add(ticket);outbox,_=enqueue(s,ctx,"ODOO","SupportTicketCreatedV1",ticket.id,{"ticket_id":ticket.id,"category":x.category,"subject":x.subject,"priority":x.priority},"support:"+ticket.id);audit(s,ctx,"support.ticket.created");s.commit();return {"id":ticket.id,"status":ticket.status,"odoo_sync":"QUEUED","outbox_id":outbox.id}
@router.get("/support/tickets")
def support_list(ctx=Depends(auth),s:Session=Depends(db)):return s.scalars(select(SupportTicket).where(SupportTicket.tenant_id==ctx["tenant"]).order_by(SupportTicket.created_at.desc())).all()
@router.post("/automation/events",status_code=202)
def automation(x:AutomationIn,ctx=Depends(auth),s:Session=Depends(db)):
    item,duplicate=enqueue(s,ctx,"N8N",x.event_type,x.aggregate_id,x.payload,x.idempotency_key);s.commit();return {"id":item.id,"state":item.state,"duplicate":duplicate,"direct_database_write":False}
@router.post("/billing/odoo-sync",status_code=202)
def billing_sync(x:AutomationIn,ctx=Depends(auth),s:Session=Depends(db)):
    item,duplicate=enqueue(s,ctx,"ODOO","KlyrowBillingSyncV1",x.aggregate_id,x.payload,x.idempotency_key);s.commit();return {"id":item.id,"state":item.state,"duplicate":duplicate,"direct_odoo_database_write":False}
@router.post("/integrations/results",status_code=202)
def result(x:ResultIn,ctx=Depends(auth),s:Session=Depends(db)):
    outbox=owned(s,IntegrationOutbox,x.outbox_id,ctx["tenant"]);prior=s.scalar(select(IntegrationResult).where(IntegrationResult.result_key==x.result_key))
    if prior:return {"id":prior.id,"duplicate":True}
    item=IntegrationResult(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],outbox_id=outbox.id,source=outbox.target,result_key=x.result_key,payload_json=json.dumps(x.payload,sort_keys=True));outbox.state="COMPLETED";outbox.updated_at=now();s.add(item);s.commit();return {"id":item.id,"duplicate":False}

@router.post("/exports",status_code=202)
def export(x:ExportIn,ctx=Depends(auth),s:Session=Depends(db)):
    allowed={"account","contacts","domains","billing","audit","message_metadata"}
    if not set(x.scopes)<=allowed:raise HTTPException(422,"invalid_export_scope")
    item=ExportJob(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],requested_by=ctx["sub"],scope_json=json.dumps(sorted(set(x.scopes))));s.add(item);audit(s,ctx,"tenant.export.requested");s.commit();return {"id":item.id,"state":item.state,"asynchronous":True}
@router.post("/account/closure",status_code=202)
def closure(x:ClosureIn,ctx=Depends(auth),s:Session=Depends(db)):
    if s.scalar(select(AccountClosure).where(AccountClosure.tenant_id==ctx["tenant"],AccountClosure.state.notin_(["CANCELLED","CLOSED"]))):raise HTTPException(409,"closure_already_requested")
    raw=str(uuid.uuid4());item=AccountClosure(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],requested_by=ctx["sub"],confirmation_hash=__import__('hashlib').sha256(raw.encode()).hexdigest(),grace_until=now()+timedelta(days=x.grace_days),retention_policy=x.retention_policy);s.add(item);gate=s.get(TenantSendGate,ctx["tenant"]) or TenantSendGate(tenant_id=ctx["tenant"],updated_by=ctx["sub"]);gate.enabled=False;gate.reason="ACCOUNT_CLOSURE_REQUESTED";gate.updated_by=ctx["sub"];gate.updated_at=now();s.add(gate);audit(s,ctx,"account.closure.requested");s.commit();return {"id":item.id,"confirmation":raw,"state":item.state,"grace_until":item.grace_until,"sending_enabled":False}
@router.post("/account/closure/{item_id}/confirm")
def closure_confirm(item_id:str,x:ConfirmIn,ctx=Depends(auth),s:Session=Depends(db)):
    import hashlib,hmac
    item=owned(s,AccountClosure,item_id,ctx["tenant"])
    if not hmac.compare_digest(item.confirmation_hash,hashlib.sha256(x.confirmation.encode()).hexdigest()):raise HTTPException(401,"closure_confirmation_invalid")
    item.state="CONFIRMED";item.confirmed_at=now();audit(s,ctx,"account.closure.confirmed");s.commit();return {"state":item.state,"grace_until":item.grace_until,"data_erased":False}
@router.put("/settings/send-gate")
def kill_switch(x:KillIn,ctx=Depends(auth),s:Session=Depends(db)):
    gate=s.get(TenantSendGate,ctx["tenant"]) or TenantSendGate(tenant_id=ctx["tenant"],updated_by=ctx["sub"]);gate.enabled=x.enabled;gate.reason=x.reason;gate.updated_by=ctx["sub"];gate.updated_at=now();s.add(gate);audit(s,ctx,"tenant.send_gate."+("enabled" if x.enabled else "disabled"));s.commit();return {"sending_enabled":gate.enabled,"reason":gate.reason,"effective_immediately":True}
@router.get("/settings/send-gate")
def send_gate(ctx=Depends(auth),s:Session=Depends(db)):
    gate=s.get(TenantSendGate,ctx["tenant"]);return {"sending_enabled":gate.enabled if gate else True,"reason":gate.reason if gate else "ACTIVE"}

@router.post("/admin/operations/delivery-jobs/{item_id}/recover")
def recover_delivery(item_id:str,x:RecoverIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    item=s.get(DeliveryJob,item_id)
    if not item or item.state!="DEAD_LETTER":raise HTTPException(404,"dead_letter_not_found")
    item.state="RETRY";item.next_attempt_at=now();item.dead_lettered_at=None;item.lease_owner=None;item.lease_expires_at=None;audit(s,{**ctx,"tenant":item.tenant_id},"delivery.dead_letter_recovered:"+x.reason);s.commit();return {"state":item.state,"attempts":item.attempts}
@router.post("/admin/operations/webhooks/{item_id}/replay")
def replay_webhook(item_id:str,x:RecoverIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    item=s.get(WebhookAttempt,item_id)
    if not item:raise HTTPException(404,"webhook_attempt_not_found")
    item.state="PENDING";item.next_attempt_at=now();item.last_error=None;audit(s,{**ctx,"tenant":item.tenant_id},"webhook.replay_requested:"+x.reason);s.commit();return {"state":item.state,"attempts":item.attempts}
@router.post("/admin/operations/integrations/{item_id}/fail")
def fail_integration(item_id:str,x:RecoverIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    item=s.get(IntegrationOutbox,item_id)
    if not item or item.state=="COMPLETED":raise HTTPException(404,"pending_integration_not_found")
    item.attempts+=1;item.last_error=x.reason;item.state="DEAD_LETTER" if item.attempts>=8 else "RETRY";item.next_attempt_at=now()+timedelta(seconds=min(900,2**item.attempts));item.updated_at=now();audit(s,{**ctx,"tenant":item.tenant_id},"integration.delivery_failed:"+item.target);s.commit();return {"state":item.state,"attempts":item.attempts,"target":item.target}
@router.post("/admin/operations/integrations/{item_id}/recover")
def recover_integration(item_id:str,x:RecoverIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    item=s.get(IntegrationOutbox,item_id)
    if not item or item.state not in {"RETRY","DEAD_LETTER"}:raise HTTPException(404,"recoverable_integration_not_found")
    item.state="PENDING";item.next_attempt_at=now();item.last_error=None;item.updated_at=now();audit(s,{**ctx,"tenant":item.tenant_id},"integration.delivery_recovered:"+item.target+":"+x.reason);s.commit();return {"state":item.state,"attempts":item.attempts,"target":item.target}
@router.post("/admin/reconciliation",status_code=201)
def reconcile(ctx=Depends(require("platform_admin")),s:Session=Depends(db)):
    details=[]
    for message in s.scalars(select(Message)).all():
        outbox=s.scalar(select(EmailOutbox).where(EmailOutbox.message_id==message.id))
        if message.status in {"queued","QUEUED"} and not outbox:details.append({"kind":"missing_email_outbox","message_id":message.id,"tenant_id":message.tenant_id})
    run=ReconciliationRun(id=str(uuid.uuid4()),tenant_id=None,kind="PLATFORM",state="PASS" if not details else "DRIFT",drift_count=len(details),details_json=json.dumps(details),completed_at=now());s.add(run);audit(s,ctx,"platform.reconciliation.completed");s.commit();return {"id":run.id,"state":run.state,"drift_count":run.drift_count,"auto_corrected":False}
