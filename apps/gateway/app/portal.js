let token=sessionStorage.token||"";
const $=id=>document.getElementById(id);
const base64url=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
const randomValue=()=>base64url(crypto.getRandomValues(new Uint8Array(32)));
async function oidcConfig(){const response=await fetch("/v1/auth/oidc/config",{cache:"no-store"});if(!response.ok)throw Error("Identity service unavailable");return response.json()}
async function beginLogin(){
  const config=await oidcConfig(),verifier=randomValue(),state=randomValue();
  const challenge=base64url(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(verifier)));
  sessionStorage.pkceVerifier=verifier;sessionStorage.oidcState=state;
  const query=new URLSearchParams({client_id:config.client_id,response_type:"code",scope:config.scopes.join(" "),redirect_uri:location.origin+"/",code_challenge:challenge,code_challenge_method:"S256",state});
  location.assign(config.authorization_endpoint+"?"+query);
}
async function finishLogin(){
  const query=new URLSearchParams(location.search),code=query.get("code");if(!code)return false;
  if(!query.get("state")||query.get("state")!==sessionStorage.oidcState)throw Error("Invalid identity response state");
  const config=await oidcConfig(),body=new URLSearchParams({grant_type:"authorization_code",client_id:config.client_id,code,redirect_uri:location.origin+"/",code_verifier:sessionStorage.pkceVerifier||""});
  const response=await fetch(config.token_endpoint,{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});
  const result=await response.json();if(!response.ok||!result.access_token)throw Error("Identity token exchange failed");
  token=result.access_token;sessionStorage.token=token;sessionStorage.removeItem("pkceVerifier");sessionStorage.removeItem("oidcState");history.replaceState({},"",location.pathname);return true;
}
async function api(path,options={}){options.headers={...(options.headers||{}),Authorization:`Bearer ${token}`,"Content-Type":"application/json"};const response=await fetch(path,options);const body=await response.json().catch(()=>({}));if(!response.ok)throw Error(body.detail||response.status);return body}
const show=(id,x)=>$(id).textContent=JSON.stringify(x,null,2);
async function load(){const x=await api("/v1/analytics/overview");$("messages").textContent=x.messages;$("profileCount").textContent=x.profiles;$("deliveryRate").textContent=(x.delivery_rate*100).toFixed(1)+"%";$("conversions").textContent=x.conversions;$("login").hidden=true;$("app").hidden=false}
$("signin").textContent="Continue with Keycloak";
for(const id of ["email","password","otp"]){const field=$(id);if(field)field.hidden=true}
$("signin").onclick=()=>beginLogin().catch(e=>$("message").textContent=e.message);
$("logout").onclick=()=>{sessionStorage.clear();location.assign("/")};
$("nav").onclick=e=>{if(!e.target.dataset.view)return;document.querySelectorAll("nav button,.view").forEach(x=>x.classList.remove("active"));e.target.classList.add("active");document.querySelector(`.view[data-view="${e.target.dataset.view}"]`).classList.add("active");$("title").textContent=e.target.textContent};
const act=(id,fn)=>$(id).onclick=async()=>{try{await fn();$("error").textContent=""}catch(e){$("error").textContent=e.message}};
act("saveOnboarding",async()=>show("onboardingOut",await api("/v1/onboarding",{method:"PUT",body:JSON.stringify({step:+$("onboardStep").value,use_case:$("useCase").value,checklist:{}})})));
act("createProfile",async()=>{const x=await api("/v1/profiles",{method:"POST",body:JSON.stringify({email:$("profileEmail").value,attributes:JSON.parse($("profileAttrs").value||"{}")})});$("consentProfile").value=x.id;show("profilesOut",x)});
act("recordConsent",async()=>show("profilesOut",await api("/v1/consents",{method:"POST",body:JSON.stringify({profile_id:$("consentProfile").value,topic:"marketing",status:$("consentStatus").value,source:$("consentSource").value,version:"current"})})));
act("createSegment",async()=>{const x=await api("/v1/segments",{method:"POST",body:JSON.stringify({name:$("segmentName").value,rules:JSON.parse($("segmentRules").value)})});show("segmentOut",await api(`/v1/segments/${x.id}/preview`))});
act("createJourney",async()=>show("journeyOut",await api("/v1/journeys",{method:"POST",body:JSON.stringify({name:$("journeyName").value,graph:JSON.parse($("journeyGraph").value)})})));
act("checkDomain",async()=>show("deliveryOut",await api(`/v1/deliverability/domains/${$("domainId").value}/check`,{method:"POST"})));
act("setupMfa",async()=>show("securityOut",await api("/v1/auth/mfa/setup",{method:"POST"})));
(async()=>{try{await finishLogin();if(token)await load()}catch(e){sessionStorage.removeItem("token");$("message").textContent=e.message}})();
