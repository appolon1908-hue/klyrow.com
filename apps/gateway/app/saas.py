import base64, hashlib, hmac, html, ipaddress, json, math, os, re, secrets, socket, struct, time, uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import dns.resolver
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .main import Audit, Base, Domain, Event, Message, Suppression, Tenant, User, audit, auth, db, require

router=APIRouter(prefix="/v1",tags=["SaaS P0/P1"])
now=lambda: datetime.now(timezone.utc)

class Profile(Base):
    __tablename__="profiles"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); email:Mapped[Optional[str]]=mapped_column(String,index=True,nullable=True); phone:Mapped[Optional[str]]=mapped_column(String,nullable=True); external_id:Mapped[Optional[str]]=mapped_column(String,index=True,nullable=True); customer_id:Mapped[Optional[str]]=mapped_column(String,index=True,nullable=True); attributes_json:Mapped[str]=mapped_column(Text,default="{}"); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class CustomerEvent(Base):
    __tablename__="customer_events"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); profile_id:Mapped[str]=mapped_column(ForeignKey("profiles.id"),index=True); name:Mapped[str]=mapped_column(String,index=True); properties_json:Mapped[str]=mapped_column(Text,default="{}"); occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class Consent(Base):
    __tablename__="consents"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); profile_id:Mapped[str]=mapped_column(ForeignKey("profiles.id"),index=True); topic:Mapped[str]=mapped_column(String,default="marketing"); status:Mapped[str]=mapped_column(String); source:Mapped[str]=mapped_column(String); version:Mapped[str]=mapped_column(String); occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); proof_json:Mapped[str]=mapped_column(Text,default="{}")
class Preference(Base):
    __tablename__="preferences"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); profile_id:Mapped[str]=mapped_column(ForeignKey("profiles.id"),index=True); topic:Mapped[str]=mapped_column(String); subscribed:Mapped[bool]=mapped_column(Boolean,default=True); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Segment(Base):
    __tablename__="segments"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); name:Mapped[str]=mapped_column(String); rules_json:Mapped[str]=mapped_column(Text); kind:Mapped[str]=mapped_column(String,default="dynamic"); revision:Mapped[int]=mapped_column(Integer,default=1); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class SegmentAudit(Base):
    __tablename__="segment_audit"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); segment_id:Mapped[str]=mapped_column(String,index=True); revision:Mapped[int]=mapped_column(Integer); rules_json:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Journey(Base):
    __tablename__="journeys"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),index=True); name:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String,default="draft"); version:Mapped[int]=mapped_column(Integer,default=1); graph_json:Mapped[str]=mapped_column(Text); goal_event:Mapped[Optional[str]]=mapped_column(String,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class JourneyVersion(Base):
    __tablename__="journey_versions"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); journey_id:Mapped[str]=mapped_column(String,index=True); version:Mapped[int]=mapped_column(Integer); graph_json:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class JourneyRun(Base):
    __tablename__="journey_runs"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); journey_id:Mapped[str]=mapped_column(String,index=True); profile_id:Mapped[str]=mapped_column(String,index=True); status:Mapped[str]=mapped_column(String,default="running"); current_node:Mapped[Optional[str]]=mapped_column(String,nullable=True); history_json:Mapped[str]=mapped_column(Text,default="[]"); converted:Mapped[bool]=mapped_column(Boolean,default=False); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Onboarding(Base):
    __tablename__="onboarding"; tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.id"),primary_key=True); step:Mapped[int]=mapped_column(Integer,default=1); use_case:Mapped[Optional[str]]=mapped_column(String,nullable=True); checklist_json:Mapped[str]=mapped_column(Text,default="{}"); completed:Mapped[bool]=mapped_column(Boolean,default=False)
class MfaConfig(Base):
    __tablename__="mfa_configs"; user_id:Mapped[str]=mapped_column(ForeignKey("users.id"),primary_key=True); secret:Mapped[str]=mapped_column(String); enabled:Mapped[bool]=mapped_column(Boolean,default=False); recovery_hashes_json:Mapped[str]=mapped_column(Text,default="[]")
class SessionRecord(Base):
    __tablename__="sessions"; id:Mapped[str]=mapped_column(String,primary_key=True); user_id:Mapped[str]=mapped_column(String,index=True); tenant_id:Mapped[str]=mapped_column(String,index=True); revoked:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class DeliverabilitySnapshot(Base):
    __tablename__="deliverability_snapshots"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); domain_id:Mapped[str]=mapped_column(String,index=True); spf:Mapped[bool]=mapped_column(Boolean); dkim:Mapped[bool]=mapped_column(Boolean); dmarc:Mapped[bool]=mapped_column(Boolean); mx:Mapped[bool]=mapped_column(Boolean); ptr:Mapped[bool]=mapped_column(Boolean); tls:Mapped[bool]=mapped_column(Boolean); details_json:Mapped[str]=mapped_column(Text); checked_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Experiment(Base):
    __tablename__="experiments"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); name:Mapped[str]=mapped_column(String); variants_json:Mapped[str]=mapped_column(Text); metric:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String,default="draft")
class ExperimentAssignment(Base):
    __tablename__="experiment_assignments"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); experiment_id:Mapped[str]=mapped_column(String,index=True); profile_id:Mapped[str]=mapped_column(String,index=True); variant:Mapped[str]=mapped_column(String); converted:Mapped[bool]=mapped_column(Boolean,default=False)
class Integration(Base):
    __tablename__="integrations"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); kind:Mapped[str]=mapped_column(String); name:Mapped[str]=mapped_column(String); config_json:Mapped[str]=mapped_column(Text,default="{}"); enabled:Mapped[bool]=mapped_column(Boolean,default=False)
class Plan(Base):
    __tablename__="plans"; id:Mapped[str]=mapped_column(String,primary_key=True); name:Mapped[str]=mapped_column(String); messages:Mapped[int]=mapped_column(Integer); profiles:Mapped[int]=mapped_column(Integer); seats:Mapped[int]=mapped_column(Integer); api_per_minute:Mapped[int]=mapped_column(Integer)
class Subscription(Base):
    __tablename__="subscriptions"; tenant_id:Mapped[str]=mapped_column(String,primary_key=True); plan_id:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String,default="trial"); provider:Mapped[Optional[str]]=mapped_column(String,nullable=True); external_ref:Mapped[Optional[str]]=mapped_column(String,nullable=True)
class UsageLedger(Base):
    __tablename__="usage_ledger"; id:Mapped[str]=mapped_column(String,primary_key=True); tenant_id:Mapped[str]=mapped_column(String,index=True); kind:Mapped[str]=mapped_column(String); quantity:Mapped[int]=mapped_column(Integer); reference:Mapped[Optional[str]]=mapped_column(String,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class ProfileIn(BaseModel): email:Optional[str]=None; phone:Optional[str]=None; external_id:Optional[str]=None; customer_id:Optional[str]=None; attributes:dict[str,Any]=Field(default_factory=dict)
class EventIn(BaseModel): profile_id:str; name:str=Field(min_length=1,max_length=100); properties:dict[str,Any]=Field(default_factory=dict); occurred_at:Optional[datetime]=None
class ConsentIn(BaseModel): profile_id:str; topic:str="marketing"; status:str=Field(pattern="^(granted|revoked|pending)$"); source:str; version:str; proof:dict[str,Any]=Field(default_factory=dict)
class PreferenceIn(BaseModel): topic:str; subscribed:bool
class SegmentIn(BaseModel): name:str; rules:dict[str,Any]; kind:str=Field(default="dynamic",pattern="^(dynamic|manual|exclusion)$")
class JourneyIn(BaseModel): name:str; graph:dict[str,Any]; goal_event:Optional[str]=None
class RunIn(BaseModel): profile_id:str
class OnboardingIn(BaseModel): step:int=Field(ge=1,le=12); use_case:Optional[str]=None; checklist:dict[str,bool]=Field(default_factory=dict)
class MfaEnableIn(BaseModel): code:str
class ExperimentIn(BaseModel): name:str; variants:list[dict[str,Any]]=Field(min_length=2,max_length=10); metric:str="conversion"
class IntegrationIn(BaseModel): kind:str=Field(pattern="^(middleware|odoo|n8n|google|webhook|csv|rest)$"); name:str; config:dict[str,Any]=Field(default_factory=dict)
class PlanIn(BaseModel): name:str; messages:int=Field(ge=0); profiles:int=Field(ge=0); seats:int=Field(ge=1); api_per_minute:int=Field(ge=1)
class AiIn(BaseModel): capability:str=Field(pattern="^(subject|draft|rewrite|segment|journey|summary)$"); prompt:str=Field(min_length=3,max_length=10000); context:dict[str,Any]=Field(default_factory=dict)
class RenderIn(BaseModel): html:str=Field(max_length=100000); variables:dict[str,Any]=Field(default_factory=dict)

def get_profile(s,tenant,pid):
    p=s.scalar(select(Profile).where(Profile.id==pid,Profile.tenant_id==tenant))
    if not p: raise HTTPException(404,"profile_not_found")
    return p
def attrs(p): return json.loads(p.attributes_json or "{}")
def match_rule(s,p,rule):
    if "all" in rule:return all(match_rule(s,p,r) for r in rule["all"])
    if "any" in rule:return any(match_rule(s,p,r) for r in rule["any"])
    if "not" in rule:return not match_rule(s,p,rule["not"])
    field=rule.get("field"); op=rule.get("op","eq"); value=rule.get("value"); actual={"email":p.email,"phone":p.phone,"external_id":p.external_id,"customer_id":p.customer_id,**attrs(p)}.get(field)
    if field=="event":
        q=select(func.count(CustomerEvent.id)).where(CustomerEvent.tenant_id==p.tenant_id,CustomerEvent.profile_id==p.id,CustomerEvent.name==rule.get("name"))
        if rule.get("within_days"):q=q.where(CustomerEvent.occurred_at>=now()-timedelta(days=rule["within_days"]))
        actual=s.scalar(q) or 0; value=rule.get("count",1)
    if op=="eq":return actual==value
    if op=="neq":return actual!=value
    if op=="contains":return str(value).lower() in str(actual).lower()
    if op=="gt":return actual is not None and actual>value
    if op=="gte":return actual is not None and actual>=value
    if op=="lt":return actual is not None and actual<value
    if op=="in":return isinstance(value,(list,tuple,set)) and actual in value
    return False
def segment_members(s,seg): return [p for p in s.scalars(select(Profile).where(Profile.tenant_id==seg.tenant_id)).all() if match_rule(s,p,json.loads(seg.rules_json)) and not s.scalar(select(Suppression).where(Suppression.tenant_id==seg.tenant_id,Suppression.email==p.email))]

@router.post("/profiles",status_code=201)
def profile_upsert(x:ProfileIn,ctx=Depends(auth),s:Session=Depends(db)):
    if not any((x.email,x.phone,x.external_id,x.customer_id)):raise HTTPException(422,"identifier_required")
    clauses=[]
    for key,val in ((Profile.email,x.email),(Profile.phone,x.phone),(Profile.external_id,x.external_id),(Profile.customer_id,x.customer_id)):
        if val:clauses.append(key==val.lower() if key==Profile.email else key==val)
    from sqlalchemy import or_
    matches=s.scalars(select(Profile).where(Profile.tenant_id==ctx["tenant"],or_(*clauses))).all(); p=matches[0] if matches else Profile(id=str(uuid.uuid4()),tenant_id=ctx["tenant"])
    for duplicate in matches[1:]:
        for ev in s.scalars(select(CustomerEvent).where(CustomerEvent.profile_id==duplicate.id)).all():ev.profile_id=p.id
        s.delete(duplicate)
    p.email=x.email.lower() if x.email else p.email; p.phone=x.phone or p.phone; p.external_id=x.external_id or p.external_id; p.customer_id=x.customer_id or p.customer_id; p.attributes_json=json.dumps({**attrs(p),**x.attributes}); p.updated_at=now(); s.add(p); audit(s,ctx,"profile.upserted"); s.commit(); return {"id":p.id,"email":p.email,"attributes":attrs(p),"merged":len(matches)>1}
@router.get("/profiles/{pid}")
def profile_get(pid:str,ctx=Depends(auth),s:Session=Depends(db)): p=get_profile(s,ctx["tenant"],pid); return {"id":p.id,"email":p.email,"phone":p.phone,"external_id":p.external_id,"customer_id":p.customer_id,"attributes":attrs(p)}
@router.post("/events",status_code=202)
def ingest(x:EventIn,ctx=Depends(auth),s:Session=Depends(db)):
    get_profile(s,ctx["tenant"],x.profile_id); e=CustomerEvent(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],profile_id=x.profile_id,name=x.name,properties_json=json.dumps(x.properties),occurred_at=x.occurred_at or now()); s.add(e)
    for run in s.scalars(select(JourneyRun).where(JourneyRun.tenant_id==ctx["tenant"],JourneyRun.profile_id==x.profile_id,JourneyRun.status=="running")).all():
        j=s.get(Journey,run.journey_id)
        if j and j.goal_event==x.name:run.converted=True;run.status="completed";run.history_json=json.dumps(json.loads(run.history_json)+[{"event":"goal","name":x.name,"at":now().isoformat()}])
    s.commit(); return {"id":e.id,"accepted":True}
@router.get("/profiles/{pid}/timeline")
def timeline(pid:str,ctx=Depends(auth),s:Session=Depends(db)): get_profile(s,ctx["tenant"],pid); return s.scalars(select(CustomerEvent).where(CustomerEvent.tenant_id==ctx["tenant"],CustomerEvent.profile_id==pid).order_by(CustomerEvent.occurred_at.desc())).all()

@router.post("/consents",status_code=201)
def consent(x:ConsentIn,ctx=Depends(auth),s:Session=Depends(db)):
    get_profile(s,ctx["tenant"],x.profile_id); c=Consent(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],profile_id=x.profile_id,topic=x.topic,status=x.status,source=x.source,version=x.version,proof_json=json.dumps(x.proof)); s.add(c)
    pref=s.scalar(select(Preference).where(Preference.tenant_id==ctx["tenant"],Preference.profile_id==x.profile_id,Preference.topic==x.topic)) or Preference(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],profile_id=x.profile_id,topic=x.topic); pref.subscribed=x.status=="granted";pref.updated_at=now();s.add(pref)
    if x.status=="revoked":
        p=get_profile(s,ctx["tenant"],x.profile_id)
        if p.email and not s.scalar(select(Suppression).where(Suppression.tenant_id==ctx["tenant"],Suppression.email==p.email)):s.add(Suppression(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],email=p.email,reason="consent_revoked"))
    audit(s,ctx,"consent."+x.status);s.commit();return {"id":c.id,"status":c.status}
@router.put("/profiles/{pid}/preferences/{topic}")
def preference(pid:str,topic:str,x:PreferenceIn,ctx=Depends(auth),s:Session=Depends(db)):
    get_profile(s,ctx["tenant"],pid); p=s.scalar(select(Preference).where(Preference.tenant_id==ctx["tenant"],Preference.profile_id==pid,Preference.topic==topic)) or Preference(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],profile_id=pid,topic=topic);p.subscribed=x.subscribed;p.updated_at=now();s.add(p);audit(s,ctx,"preference.changed");s.commit();return {"topic":topic,"subscribed":p.subscribed}
@router.get("/profiles/{pid}/preferences")
def preferences(pid:str,ctx=Depends(auth),s:Session=Depends(db)):get_profile(s,ctx["tenant"],pid);return s.scalars(select(Preference).where(Preference.tenant_id==ctx["tenant"],Preference.profile_id==pid)).all()

@router.post("/segments",status_code=201)
def segment_create(x:SegmentIn,ctx=Depends(auth),s:Session=Depends(db)):seg=Segment(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],name=x.name,rules_json=json.dumps(x.rules),kind=x.kind);s.add(seg);s.add(SegmentAudit(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],segment_id=seg.id,revision=1,rules_json=seg.rules_json));audit(s,ctx,"segment.created");s.commit();return {"id":seg.id,"revision":1}
@router.get("/segments/{sid}/preview")
def segment_preview(sid:str,ctx=Depends(auth),s:Session=Depends(db)):
    seg=s.scalar(select(Segment).where(Segment.id==sid,Segment.tenant_id==ctx["tenant"]));
    if not seg:raise HTTPException(404,"segment_not_found")
    members=segment_members(s,seg);return {"estimated_size":len(members),"sample":[{"id":p.id,"email":p.email} for p in members[:20]],"revision":seg.revision}

VALID_NODES={"trigger","segment_entry","event","wait","wait_until","email","condition","percentage_split","ab_branch","goal","update_profile","webhook","middleware_event","add_segment","remove_segment","unsubscribe","suppress","exit"}
def validate_graph(g):
    nodes=g.get("nodes",[]); ids={n.get("id") for n in nodes}
    if not nodes or len(ids)!=len(nodes) or any(n.get("type") not in VALID_NODES for n in nodes):raise HTTPException(422,"invalid_journey_graph")
    if any(e.get("from") not in ids or e.get("to") not in ids for e in g.get("edges",[])):raise HTTPException(422,"invalid_journey_edge")
@router.post("/journeys",status_code=201)
def journey_create(x:JourneyIn,ctx=Depends(auth),s:Session=Depends(db)):validate_graph(x.graph);j=Journey(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],name=x.name,graph_json=json.dumps(x.graph),goal_event=x.goal_event);s.add(j);s.add(JourneyVersion(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],journey_id=j.id,version=1,graph_json=j.graph_json));audit(s,ctx,"journey.created");s.commit();return {"id":j.id,"status":j.status,"version":j.version}
def journey_action(jid:str,action:str,ctx,s):
    j=s.scalar(select(Journey).where(Journey.id==jid,Journey.tenant_id==ctx["tenant"]));
    if not j:raise HTTPException(404,"journey_not_found")
    j.status={"publish":"active","pause":"paused","resume":"active","rollback":"draft"}[action];audit(s,ctx,"journey."+action);s.commit();return {"status":j.status,"version":j.version}
@router.post("/journeys/{jid}/publish")
def journey_publish(jid:str,ctx=Depends(auth),s:Session=Depends(db)):return journey_action(jid,"publish",ctx,s)
@router.post("/journeys/{jid}/pause")
def journey_pause(jid:str,ctx=Depends(auth),s:Session=Depends(db)):return journey_action(jid,"pause",ctx,s)
@router.post("/journeys/{jid}/resume")
def journey_resume(jid:str,ctx=Depends(auth),s:Session=Depends(db)):return journey_action(jid,"resume",ctx,s)
@router.post("/journeys/{jid}/rollback")
def journey_rollback(jid:str,ctx=Depends(auth),s:Session=Depends(db)):return journey_action(jid,"rollback",ctx,s)
@router.post("/journeys/{jid}/runs",status_code=201)
def journey_run(jid:str,x:RunIn,ctx=Depends(auth),s:Session=Depends(db)):
    j=s.scalar(select(Journey).where(Journey.id==jid,Journey.tenant_id==ctx["tenant"]));get_profile(s,ctx["tenant"],x.profile_id)
    if not j or j.status!="active":raise HTTPException(409,"journey_not_active")
    first=json.loads(j.graph_json)["nodes"][0]["id"];r=JourneyRun(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],journey_id=jid,profile_id=x.profile_id,current_node=first,history_json=json.dumps([{"node":first,"at":now().isoformat()}]));s.add(r);s.commit();return {"id":r.id,"status":r.status,"current_node":first}
@router.get("/journeys/{jid}/runs")
def journey_runs(jid:str,ctx=Depends(auth),s:Session=Depends(db)):return s.scalars(select(JourneyRun).where(JourneyRun.journey_id==jid,JourneyRun.tenant_id==ctx["tenant"])).all()

def txt(name):
    try:return [b"".join(r.strings).decode() for r in dns.resolver.resolve(name,"TXT")]
    except Exception:return []
@router.post("/deliverability/domains/{did}/check")
def deliverability(did:str,ctx=Depends(auth),s:Session=Depends(db)):
    d=s.scalar(select(Domain).where(Domain.id==did,Domain.tenant_id==ctx["tenant"]));
    if not d:raise HTTPException(404,"domain_not_found")
    try:mx=bool(list(dns.resolver.resolve(d.domain,"MX")))
    except Exception:mx=False
    spf=any(v.startswith("v=spf1") for v in txt(d.domain));dkim=any(v.startswith("v=DKIM1") for v in txt("postal._domainkey."+d.domain));dmarc=any(v.startswith("v=DMARC1") for v in txt("_dmarc."+d.domain))
    try:
        mail_host = ("mail." + d.domain).rstrip(".").lower()
        reverse_name = ipaddress.ip_address(socket.gethostbyname(mail_host)).reverse_pointer
        ptr = any(
            str(record).rstrip(".").lower() == mail_host
            for record in dns.resolver.resolve(reverse_name, "PTR")
        )
    except Exception:ptr=False
    tls=False;details={"mx":mx,"spf":spf,"dkim":dkim,"dmarc":dmarc,"ptr":ptr,"tls":tls};alerts=[{"severity":"critical" if k in {"dkim","ptr","tls"} else "warning","code":k+"_missing"} for k,v in details.items() if not v];snap=DeliverabilitySnapshot(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],domain_id=d.id,spf=spf,dkim=dkim,dmarc=dmarc,mx=mx,ptr=ptr,tls=tls,details_json=json.dumps({**details,"alerts":alerts}));s.add(snap);s.commit();return {**details,"alerts":alerts,"launch_ready":all(details.values()),"checked_at":snap.checked_at}
@router.get("/deliverability")
def deliverability_all(ctx=Depends(auth),s:Session=Depends(db)):return s.scalars(select(DeliverabilitySnapshot).where(DeliverabilitySnapshot.tenant_id==ctx["tenant"]).order_by(DeliverabilitySnapshot.checked_at.desc())).all()

@router.get("/analytics/overview")
def analytics(ctx=Depends(auth),s:Session=Depends(db)):
    kinds=dict(s.execute(select(Event.kind,func.count(Event.id)).where(Event.tenant_id==ctx["tenant"]).group_by(Event.kind)).all());messages=s.scalar(select(func.count(Message.id)).where(Message.tenant_id==ctx["tenant"])) or 0;profiles=s.scalar(select(func.count(Profile.id)).where(Profile.tenant_id==ctx["tenant"])) or 0
    val=lambda *names:sum(kinds.get(n,0) for n in names)
    delivered=val("email.delivered","klyrow.email.delivered");bounced=val("email.bounced","klyrow.email.bounced");return {"messages":messages,"profiles":profiles,"events":kinds,"delivered":delivered,"bounced":bounced,"delivery_rate":delivered/messages if messages else 0,"bounce_rate":bounced/messages if messages else 0,"conversions":s.scalar(select(func.count(CustomerEvent.id)).where(CustomerEvent.tenant_id==ctx["tenant"],CustomerEvent.name=="conversion")) or 0}
@router.get("/onboarding")
def onboarding_get(ctx=Depends(auth),s:Session=Depends(db)):o=s.get(Onboarding,ctx["tenant"]) or Onboarding(tenant_id=ctx["tenant"]);s.add(o);s.commit();return {"step":o.step,"use_case":o.use_case,"checklist":json.loads(o.checklist_json),"completed":o.completed,"production_gate":False}
@router.put("/onboarding")
def onboarding_put(x:OnboardingIn,ctx=Depends(auth),s:Session=Depends(db)):o=s.get(Onboarding,ctx["tenant"]) or Onboarding(tenant_id=ctx["tenant"]);o.step=x.step;o.use_case=x.use_case or o.use_case;o.checklist_json=json.dumps(x.checklist);o.completed=x.step==12 and all(x.checklist.values()) and False;s.add(o);audit(s,ctx,"onboarding.updated");s.commit();return {"step":o.step,"completed":o.completed,"production_gate":False}

def totp(secret,counter=None):
    key=base64.b32decode(secret);counter=counter if counter is not None else int(time.time())//30;digest=hmac.new(key,struct.pack(">Q",counter),hashlib.sha1).digest();offset=digest[-1]&15;return str((struct.unpack(">I",digest[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
def verify_totp(secret,code):return any(hmac.compare_digest(totp(secret,int(time.time())//30+d),code) for d in (-1,0,1))
@router.post("/auth/mfa/setup")
def mfa_setup(ctx=Depends(auth),s:Session=Depends(db)):secret=base64.b32encode(secrets.token_bytes(20)).decode();m=s.get(MfaConfig,ctx["sub"]) or MfaConfig(user_id=ctx["sub"],secret=secret);m.secret=secret;m.enabled=False;s.add(m);s.commit();return {"secret":secret,"otpauth_uri":f"otpauth://totp/Klyrow?secret={secret}&issuer=Klyrow"}
@router.post("/auth/mfa/enable")
def mfa_enable(x:MfaEnableIn,ctx=Depends(auth),s:Session=Depends(db)):
    m=s.get(MfaConfig,ctx["sub"])
    if not m or not verify_totp(m.secret,x.code):raise HTTPException(400,"invalid_mfa_code")
    recovery=[secrets.token_urlsafe(10) for _ in range(8)];m.enabled=True;m.recovery_hashes_json=json.dumps([hashlib.sha256(v.encode()).hexdigest() for v in recovery]);audit(s,ctx,"mfa.enabled");s.commit();return {"enabled":True,"recovery_codes":recovery}
@router.get("/auth/sessions")
def sessions(ctx=Depends(auth),s:Session=Depends(db)):return s.scalars(select(SessionRecord).where(SessionRecord.user_id==ctx["sub"],SessionRecord.revoked==False)).all()
@router.delete("/auth/sessions/{sid}",status_code=204)
def session_revoke(sid:str,ctx=Depends(auth),s:Session=Depends(db)):
    item=s.scalar(select(SessionRecord).where(SessionRecord.id==sid,SessionRecord.user_id==ctx["sub"]))
    if not item:raise HTTPException(404,"session_not_found")
    item.revoked=True;audit(s,ctx,"session.revoked");s.commit()
@router.get("/developer/openapi.json")
def developer_openapi():from .main import app;return app.openapi()
@router.post("/content/render")
def content_render(x:RenderIn,ctx=Depends(auth)):
    if re.search(r"<(script|iframe|object|embed)\b|on\w+\s*=|javascript:",x.html,re.I):raise HTTPException(422,"unsafe_html")
    rendered=x.html
    for key,value in x.variables.items():rendered=rendered.replace("{{"+key+"}}",html.escape(str(value),quote=True))
    return {"html":rendered,"plain_text":re.sub(r"<[^>]+>","",rendered),"personalized":True}

# P1 foundations: deterministic experiments, disabled-by-default AI, connectors, billing.
@router.post("/experiments",status_code=201)
def experiment_create(x:ExperimentIn,ctx=Depends(auth),s:Session=Depends(db)):e=Experiment(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],name=x.name,variants_json=json.dumps(x.variants),metric=x.metric);s.add(e);s.commit();return {"id":e.id,"status":e.status}
@router.post("/experiments/{eid}/assign/{pid}")
def experiment_assign(eid:str,pid:str,ctx=Depends(auth),s:Session=Depends(db)):
    e=s.scalar(select(Experiment).where(Experiment.id==eid,Experiment.tenant_id==ctx["tenant"]));get_profile(s,ctx["tenant"],pid)
    if not e:raise HTTPException(404,"experiment_not_found")
    old=s.scalar(select(ExperimentAssignment).where(ExperimentAssignment.experiment_id==eid,ExperimentAssignment.profile_id==pid,ExperimentAssignment.tenant_id==ctx["tenant"]));
    if old:return {"variant":old.variant}
    variants=json.loads(e.variants_json);variant=variants[int(hashlib.sha256((eid+pid).encode()).hexdigest(),16)%len(variants)]["name"];s.add(ExperimentAssignment(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],experiment_id=eid,profile_id=pid,variant=variant));s.commit();return {"variant":variant}
@router.get("/experiments/{eid}/results")
def experiment_results(eid:str,ctx=Depends(auth),s:Session=Depends(db)):
    rows=s.scalars(select(ExperimentAssignment).where(ExperimentAssignment.experiment_id==eid,ExperimentAssignment.tenant_id==ctx["tenant"])).all();out={}
    for r in rows:out.setdefault(r.variant,{"assigned":0,"converted":0});out[r.variant]["assigned"]+=1;out[r.variant]["converted"]+=int(r.converted)
    for v in out.values():v["rate"]=v["converted"]/v["assigned"] if v["assigned"] else 0
    return {"variants":out,"winner":max(out,key=lambda k:out[k]["rate"]) if out else None,"confidence":"insufficient_data" if len(rows)<100 else "directional"}
@router.post("/ai/assist")
def ai_assist(x:AiIn,ctx=Depends(auth)):
    if os.getenv("KLYROW_AI_ENABLED","false").lower()!="true":raise HTTPException(503,"ai_provider_not_configured")
    return {"draft":x.prompt.strip(),"provider":"local","requires_confirmation":True,"sent":False}
@router.post("/integrations",status_code=201)
def integration_create(x:IntegrationIn,ctx=Depends(auth),s:Session=Depends(db)):i=Integration(id=str(uuid.uuid4()),tenant_id=ctx["tenant"],kind=x.kind,name=x.name,config_json=json.dumps(x.config),enabled=False);s.add(i);audit(s,ctx,"integration.created");s.commit();return {"id":i.id,"enabled":False}
@router.post("/admin/plans",status_code=201)
def plan_create(x:PlanIn,ctx=Depends(require("platform_admin")),s:Session=Depends(db)):p=Plan(id=str(uuid.uuid4()),name=x.name,messages=x.messages,profiles=x.profiles,seats=x.seats,api_per_minute=x.api_per_minute);s.add(p);s.commit();return p
@router.get("/legacy/billing/usage",deprecated=True)
def billing_usage(ctx=Depends(auth),s:Session=Depends(db)):return {"entries":s.scalars(select(UsageLedger).where(UsageLedger.tenant_id==ctx["tenant"])).all(),"billing_active":False}
@router.get("/admin/operations")
def admin_operations(ctx=Depends(require("platform_admin")),s:Session=Depends(db)):return {"tenants":s.scalar(select(func.count(Tenant.id))),"suspended":s.scalar(select(func.count(Tenant.id)).where(Tenant.enabled==False)),"messages":s.scalar(select(func.count(Message.id))),"safe_mode":os.getenv("KLYROW_SAFE_MODE","true").lower()=="true"}
