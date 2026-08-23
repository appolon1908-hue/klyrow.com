const token=sessionStorage.getItem("token")||"",error=document.getElementById("error"),admin=document.getElementById("admin");
document.getElementById("signin").onclick=()=>location.assign("/");
async function request(path,method="GET"){const r=await fetch(path,{method,headers:{Authorization:`Bearer ${token}`}}),x=await r.json().catch(()=>({}));if(!r.ok)throw Error(x.detail||`Denied (${r.status})`);return x}
document.addEventListener("click",async e=>{const b=e.target.closest("button[data-path]");if(!b)return;try{document.getElementById(b.dataset.out).textContent=JSON.stringify(await request(b.dataset.path,b.dataset.method),null,2)}catch(x){error.textContent=x.message}});
(async()=>{try{await request("/v1/admin/operations");admin.hidden=false}catch(e){error.textContent=token?"Platform administrator permission required.":"Authenticate in the customer portal first."}})();
