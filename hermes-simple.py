import base64, hmac, json, os, time, threading, urllib.request, urllib.error, re, uuid, tempfile, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.getenv("PORT", "9119"))
USER = os.getenv("HERMES_DASHBOARD_BASIC_AUTH_USERNAME", "everton")
PASSWORD = os.getenv("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD", "")
DIRECT_UPSTREAM = os.getenv("HERMES_SIMPLE_DIRECT_UPSTREAM", "http://hermes-cloud.railway.internal:8642").rstrip("/")
DIRECT_KEY = os.getenv("API_SERVER_KEY", "")
BRIDGE_UPSTREAM = os.getenv("HERMES_SIMPLE_BRIDGE_UPSTREAM", "http://hermes-chatgpt-bridge-v2.railway.internal:9120").rstrip("/")
BRIDGE_KEY = os.getenv("HERMES_BRIDGE_KEY", "")
ADVANCED_URL = os.getenv("HERMES_ADVANCED_URL", "https://hermes-cloud-production-13fb.up.railway.app")
MEDIA_STORE={}
MEDIA_LOCK=threading.Lock()
MEDIA_TTL=60*60

HTML = r'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Hermes</title>
<style>
:root{
  --bg:#f7f7f5;--panel:#fff;--text:#202123;--muted:#6b6f76;--line:#e6e6e2;
  --accent:#111827;--soft:#f0f1ef;--user:#ececf1;--shadow:0 10px 35px rgba(0,0,0,.06);
}
*{box-sizing:border-box} html,body{height:100%;margin:0}
body{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
button,input,textarea,select{font:inherit}
.app{height:100%;display:grid;grid-template-columns:260px 1fr}
.sidebar{background:#171717;color:#eee;padding:14px 12px;display:flex;flex-direction:column;gap:12px}
.brand{display:flex;align-items:center;gap:10px;padding:8px 9px 14px;font-weight:650}
.logo{width:30px;height:30px;border-radius:9px;background:#fff;color:#111;display:grid;place-items:center;font-weight:800}
.newchat{border:1px solid #3a3a3a;background:#242424;color:#fff;border-radius:10px;padding:11px 12px;text-align:left;cursor:pointer}
.newchat:hover{background:#303030}
.history{overflow:auto;flex:1}
.hist{display:flex;align-items:center;gap:8px;width:100%;border:0;background:transparent;color:#ddd;border-radius:8px;padding:9px 10px;text-align:left;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hist:hover,.hist.active{background:#2b2b2b;color:#fff}
.histrow{display:flex;align-items:center;gap:4px}
.histrow .hist{flex:1;min-width:0}
.delchat{border:0;background:transparent;color:#777;cursor:pointer;border-radius:7px;padding:7px 8px;font-size:14px}
.delchat:hover{background:#3a2323;color:#ffb4b4}
.sidebottom{border-top:1px solid #333;padding-top:10px}
.advanced{display:block;color:#aaa;text-decoration:none;padding:9px 10px;border-radius:8px;font-size:14px}
.advanced:hover{background:#2b2b2b;color:#fff}
.main{min-width:0;display:flex;flex-direction:column;height:100vh}
.topbar{height:58px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.88);backdrop-filter:blur(10px);display:flex;align-items:center;padding:0 18px;gap:12px;position:relative;z-index:3}
.menu{display:none;border:0;background:transparent;font-size:22px;cursor:pointer}
.model{border:1px solid var(--line);background:#fff;border-radius:9px;padding:7px 10px;color:#333}
.status{margin-left:auto;font-size:12px;color:var(--muted)}
.chatwrap{flex:1;overflow:auto}
.chat{max-width:820px;margin:0 auto;padding:34px 22px 160px}
.empty{min-height:60vh;display:grid;place-items:center;text-align:center;color:#34363a}
.empty h1{font-size:30px;margin:0 0 8px}.empty p{color:var(--muted);margin:0}
.msg{display:flex;margin:22px 0}
.msg.user{justify-content:flex-end}
.bubble{max-width:min(78%,720px);line-height:1.55;white-space:pre-wrap;word-wrap:break-word}
.user .bubble{background:var(--user);padding:11px 15px;border-radius:18px 18px 4px 18px}
.assistant .bubble{padding:2px 0}
.role{font-size:12px;color:var(--muted);margin-bottom:5px}
.tool{font-size:12px;color:#8b5e00;background:#fff6d8;border:1px solid #f1df9e;border-radius:8px;padding:7px 9px;margin:6px 0}
.routebadges{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 7px}
.routebadge{font-size:11px;line-height:1;border:1px solid #deded8;background:#f6f6f3;color:#555b63;border-radius:999px;padding:5px 7px}
.routebadge.provider{background:#eef5ff;border-color:#d7e5fb;color:#34506f}
.routebadge.skill{background:#f5f0ff;border-color:#e4d8fb;color:#5b3d86}
.generated-image{display:block;max-width:min(100%,720px);height:auto;border-radius:14px;border:1px solid var(--line);margin-top:10px;box-shadow:var(--shadow);cursor:pointer}
.generated-video{display:block;max-width:min(100%,720px);width:100%;border-radius:14px;border:1px solid var(--line);margin-top:10px;box-shadow:var(--shadow);background:#000}
.attach{width:38px;height:38px;border:0;border-radius:12px;background:#f1f1ef;color:#333;cursor:pointer;font-size:18px}
.attachstate{max-width:820px;margin:6px auto 0;font-size:12px;color:#4b5563}
.zerocost{font-size:11px;border:1px solid #cfe8d5;background:#eefbf1;color:#276738;border-radius:999px;padding:5px 8px}
.inline-link{color:#2563eb;text-decoration:underline;word-break:break-all}
.composerbar{position:fixed;left:260px;right:0;bottom:0;padding:18px 22px 24px;background:linear-gradient(transparent,var(--bg) 32%)}
.composer{max-width:820px;margin:0 auto;background:#fff;border:1px solid #dadad6;border-radius:18px;box-shadow:var(--shadow);padding:9px 10px 9px 14px;display:flex;align-items:flex-end;gap:8px}
textarea{flex:1;border:0;outline:none;resize:none;min-height:38px;max-height:180px;padding:8px 2px;background:transparent;line-height:1.45}
.send{width:38px;height:38px;border:0;border-radius:12px;background:#111;color:#fff;cursor:pointer;font-size:18px}
.send:disabled{opacity:.35;cursor:not-allowed}
.note{max-width:820px;margin:7px auto 0;text-align:center;color:#8b8e93;font-size:11px}
.err{background:#fff1f1;border:1px solid #f1c5c5;color:#9e2525;border-radius:10px;padding:10px 12px}
.typing{display:inline-flex;gap:5px;padding:8px 0}.dot{width:6px;height:6px;background:#8c8f93;border-radius:50%;animation:b 1.1s infinite}.dot:nth-child(2){animation-delay:.15s}.dot:nth-child(3){animation-delay:.3s}@keyframes b{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
@media(max-width:760px){
 .app{grid-template-columns:1fr}.sidebar{position:fixed;z-index:10;left:0;top:0;bottom:0;width:270px;transform:translateX(-100%);transition:.2s}.sidebar.open{transform:none}.menu{display:block}.composerbar{left:0}.chat{padding-top:22px}.bubble{max-width:90%}
}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar" id="sidebar">
    <div class="brand"><div class="logo">H</div><div>Hermes</div></div>
    <button class="newchat" id="newchat">＋ Nova conversa</button>
    <div class="history" id="history"></div>
    <div class="sidebottom"><a class="advanced" href="__ADVANCED_URL__" target="_blank">⚙ Avançado</a></div>
  </aside>
  <main class="main">
    <header class="topbar">
      <button class="menu" id="menu">☰</button>
      <select class="model" id="model">
        <option value="auto">Automático · GPT-6 Sol</option>
        <option value="matrix">Matrix</option>
        <option value="local">Hermes Local</option>
        <option value="global-public">DeepSeek V4 · Público (sem chave)</option>
      </select>
      <span class="zerocost">Zero Cost Mode</span><div class="status" id="status">pronto · estável</div>
    </header>
    <div class="chatwrap" id="chatwrap"><div class="chat" id="chat"></div></div>
    <div class="composerbar">
      <div class="composer">
        <input id="fileinput" type="file" accept="image/*" hidden>
        <button class="attach" id="attach" type="button" aria-label="Anexar imagem">＋</button>
        <textarea id="input" rows="1" placeholder="Pergunte alguma coisa ao Hermes..."></textarea>
        <button class="send" id="send" aria-label="Enviar">↑</button>
      </div>
      <div class="attachstate" id="attachstate"></div>
      <div class="note">Zero Cost Mode: vídeo com imagem anexada é gerado localmente. Provider pago não é usado nesse caminho.</div>
    </div>
  </main>
</div>
<script>
const $=s=>document.querySelector(s);
const chat=$('#chat'), input=$('#input'), send=$('#send'), historyEl=$('#history'), statusEl=$('#status'), fileInput=$('#fileinput'), attachBtn=$('#attach'), attachState=$('#attachstate');
let pendingAttachment=null;
const key='hermes-simple-conversations-v2';
const activeKey='hermes-simple-active-v2';
let conversations=[];
try{
  const raw=localStorage.getItem(key);
  conversations=raw?JSON.parse(raw):[];
  if(!Array.isArray(conversations))conversations=[];
}catch(e){
  conversations=[];
  localStorage.removeItem(key);
}
let active=localStorage.getItem(activeKey)||'';
function uid(){return (crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(16).slice(2))}
function save(){localStorage.setItem(key,JSON.stringify(conversations));localStorage.setItem(activeKey,active);renderHistory()}
function current(){return conversations.find(c=>c.id===active)}
function ensure(){
 if(!current()){const c={id:uid(),title:'Nova conversa',messages:[],created:Date.now()};conversations.unshift(c);active=c.id;save()}
}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function renderHistory(){
 historyEl.innerHTML=conversations.map(c=>'<div class="histrow"><button class="hist '+(c.id===active?'active':'')+'" data-id="'+c.id+'" title="'+esc(c.title)+'">💬 '+esc(c.title)+'</button><button class="delchat" data-del="'+c.id+'" title="Excluir conversa">×</button></div>').join('');
 historyEl.querySelectorAll('.hist').forEach(b=>b.onclick=()=>{active=b.dataset.id;save();render();$('#sidebar').classList.remove('open')});
 historyEl.querySelectorAll('.delchat').forEach(b=>b.onclick=e=>{
   e.stopPropagation();
   const id=b.dataset.del;
   conversations=conversations.filter(c=>c.id!==id);
   if(active===id)active=conversations[0]?.id||'';
   save();render();
 });
}
function linkifyText(text){
 const safe=esc(text||'');
 return safe.replace(/(https?:\/\/[^\s<]+)/g,'<a class="inline-link" href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}
function firstUrl(text){
 const m=(text||'').match(/https?:\/\/[^\s<>"']+/);
 return m?m[0]:null;
}
function render(){
 ensure(); const c=current();
 if(!c.messages.length){chat.innerHTML='<div class="empty"><div><h1>Como posso ajudar?</h1><p>Converse com o Hermes de forma simples.</p></div></div>';return}
 chat.innerHTML=c.messages.map(m=>{
   const role=m.role==='assistant'?'<div class="role">Hermes</div>':'';
   const body=m.error?'<div class="err">'+esc(m.text)+'</div>':linkifyText(m.text);
   let media='';
   const u=m.imageUrl || ((m.role==='assistant' && m.routeMeta && m.routeMeta.category==='Imagem')?firstUrl(m.text):null);
   if(u) media+='<img class="generated-image" src="'+esc(u)+'" alt="Imagem" onclick="window.open(this.src, \'_blank\')" onerror="this.style.display=\'none\'"/>';
   if(m.videoUrl) media+='<video class="generated-video" src="'+esc(m.videoUrl)+'" controls playsinline preload="metadata"></video>';
   if(m.attachmentUrl) media+='<img class="generated-image" src="'+esc(m.attachmentUrl)+'" alt="Imagem anexada"/>';
   return '<div class="msg '+m.role+'"><div class="bubble">'+role+body+media+'</div></div>';
 }).join('');
 requestAnimationFrame(()=>{$('#chatwrap').scrollTop=$('#chatwrap').scrollHeight})
}
function titleFrom(s){s=(s||'').trim().replace(/\s+/g,' ');return s.length>38?s.slice(0,38)+'…':s||'Nova conversa'}
attachBtn.onclick=()=>fileInput.click();
fileInput.onchange=async()=>{
 const file=fileInput.files&&fileInput.files[0]; if(!file)return;
 if(!file.type.startsWith('image/')){attachState.textContent='Envie uma imagem.';return}
 if(file.size>12*1024*1024){attachState.textContent='Imagem muito grande (máx. 12 MB).';return}
 attachState.textContent='Enviando imagem…';
 try{
   const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file)});
   const res=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name,mime:file.type,data})});
   const j=await res.json().catch(()=>({}));
   if(!res.ok)throw new Error(j.error||'Falha no upload');
   pendingAttachment={id:j.id,url:j.url,name:file.name};
   attachState.textContent='📎 '+file.name+' · pronto';
 }catch(e){pendingAttachment=null;attachState.textContent=e.message||'Falha no upload'}
};
async function submit(){
 const text=input.value.trim(); if(!text||send.disabled)return;
 ensure(); const c=current(); c.messages.push({role:'user',text,attachmentUrl:pendingAttachment?pendingAttachment.url:null});
 if(c.title==='Nova conversa')c.title=titleFrom(text);
 input.value=''; input.style.height='auto'; send.disabled=true; statusEl.textContent='pensando…'; save(); render();
 const holder=document.createElement('div');holder.className='msg assistant';holder.innerHTML='<div class="bubble"><div class="role">Hermes</div><div class="typing"><i class="dot"></i><i class="dot"></i><i class="dot"></i></div></div>';chat.appendChild(holder);$('#chatwrap').scrollTop=$('#chatwrap').scrollHeight;
 try{
  const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation:'web-'+c.id,input:text,route:$('#model').value,attachmentId:pendingAttachment?pendingAttachment.id:null})});
  const data=await res.json().catch(()=>({}));
  holder.remove();
  if(!res.ok)throw new Error(data.error||'Falha ao conversar com o Hermes');
  c.messages.push({role:'assistant',text:data.text||'(sem resposta)',routeMeta:data.routeMeta||null,imageUrl:data.imageUrl||null,videoUrl:data.videoUrl||null});
 }catch(e){holder.remove();c.messages.push({role:'assistant',text:e.message||'Erro de conexão',error:true})}
 finally{pendingAttachment=null;fileInput.value='';attachState.textContent='';send.disabled=false;statusEl.textContent='pronto · estável';save();render();input.focus()}
}
$('#newchat').onclick=()=>{const c={id:uid(),title:'Nova conversa',messages:[],created:Date.now()};conversations.unshift(c);active=c.id;save();render();input.focus();$('#sidebar').classList.remove('open')};
send.onclick=submit;
input.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit()}};
input.oninput=()=>{input.style.height='auto';input.style.height=Math.min(input.scrollHeight,180)+'px'};
$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');
ensure();renderHistory();render();
</script>
</body></html>'''.replace("__ADVANCED_URL__", ADVANCED_URL)

def auth_ok(headers):
    if not USER or not PASSWORD:
        return False
    h = headers.get("Authorization", "")
    if not h.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(h[6:]).decode("utf-8")
        u, p = decoded.split(":", 1)
        return hmac.compare_digest(u, USER) and hmac.compare_digest(p, PASSWORD)
    except Exception:
        return False

def call_public_deepseek(prompt):
    """Explicit opt-in: forward only current public text, never user memory/history."""
    if not isinstance(prompt,str) or not (1 <= len(prompt) <= 8000):
        raise ValueError("Mensagem pública fora do limite")
    url="https://q5dh1rfszfym23hj.us-east-2.aws.endpoints.huggingface.cloud/v1/chat/completions"
    body=json.dumps({
        "model":"deepseek-ai/DeepSeek-V4-Flash-0731",
        "messages":[{"role":"user","content":prompt}],
        "temperature":0.6,
        "max_tokens":768
    },ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(url,data=body,method="POST",headers={
        "Content-Type":"application/json","Accept":"application/json"
    })
    with urllib.request.urlopen(req,timeout=35) as res:
        obj=json.loads(res.read(4*1024*1024))
    answer=obj["choices"][0]["message"]["content"]
    if not isinstance(answer,str) or not answer.strip():
        raise ValueError("Resposta pública inválida")
    return answer

def hf_official_chat(prompt):
    """Official Hugging Face endpoint for ordinary text; HTTPS + bounded output."""
    token=os.getenv("HF_TOKEN","").strip()
    if not token.startswith("hf_") or len(token)<23:
        raise RuntimeError("HF_TOKEN not configured")
    model=os.getenv("HERMES_HF_MODEL","Qwen/Qwen2.5-72B-Instruct")
    allowed={"Qwen/Qwen2.5-72B-Instruct","meta-llama/Meta-Llama-3.1-8B-Instruct","Qwen/Qwen2.5-7B-Instruct-1M"}
    if model not in allowed:
        model="Qwen/Qwen2.5-72B-Instruct"
    body=json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],
                     "max_tokens":384,"stream":False}).encode("utf-8")
    req=urllib.request.Request("https://router.huggingface.co/v1/chat/completions",
        data=body,method="POST",headers={"Authorization":"Bearer "+token,
        "Content-Type":"application/json","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=14) as resp:
        result=json.loads(resp.read(2*1024*1024))
    answer=result["choices"][0]["message"]["content"]
    if not isinstance(answer,str) or not answer.strip():
        raise ValueError("Empty provider response")
    return answer,model

def call_upstream(payload):
    """Use the isolated bridge as the single stable chat path."""
    if not BRIDGE_KEY:
        raise RuntimeError("Bridge Hermes não configurado")
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/responses", data=body, method="POST", headers={
        "Authorization": "Bearer " + BRIDGE_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=900) as res:
            return json.load(res), "bridge"
    except urllib.error.HTTPError as e:
        raw = e.read(8192)
        raise RuntimeError(f"bridge HTTP {e.code}: " + raw.decode("utf-8","ignore")[:400]) from e

def bridge_smoke():
    """One bounded startup self-test. Never logs credentials."""
    if not BRIDGE_KEY:
        print("[hermes-simple] bridge-smoke skipped: missing bridge key", flush=True)
        return
    try:
        req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/models", headers={
            "Authorization": "Bearer " + BRIDGE_KEY,
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.load(res)
        models_ok = bool(data.get("data"))
        print(f"[hermes-simple] bridge-models status=200 models_ok={str(models_ok).lower()}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"[hermes-simple] bridge-models status={e.code}", flush=True)
        return
    except Exception as e:
        print(f"[hermes-simple] bridge-models error={type(e).__name__}", flush=True)
        return

    try:
        body = json.dumps({
            "model": "hermes-agent",
            "messages": [{"role": "user", "content": "Reply only: HERMES_SIMPLE_OK"}],
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/chat/completions", data=body, method="POST", headers={
            "Authorization": "Bearer " + BRIDGE_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=90) as res:
            data = json.load(res)
        text = str((((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""))
        print(f"[hermes-simple] bridge-chat status=200 ok={str('HERMES_SIMPLE_OK' in text).lower()}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"[hermes-simple] bridge-chat status={e.code}", flush=True)
    except Exception as e:
        print(f"[hermes-simple] bridge-chat error={type(e).__name__}", flush=True)


def classify_route(text, route="auto"):
    """Best-effort display metadata only; execution still happens in Hermes."""
    t = (text or "").lower()

    def has(*terms):
        return any(term in t for term in terms)

    category, skill, provider = "Geral", "", ""
    if has("vídeo", "video", "animar", "animação", "reels", "shorts"):
        category = "Vídeo"
        if has("matem", "equação", "algorit", "explicativo", "explicação técnica", "3blue1brown"):
            skill, provider = "manim-video", "Manim"
        else:
            skill, provider = "video-local", "Local · custo zero"
    elif has("imagem", "foto", "foto ", "editar foto", "remover fundo", "recortar", "upscale"):
        category, skill, provider = "Imagem", "image-editing", "Gerador de imagem"
    elif has("gráfico", "grafico", "dashboard", "estatística", "estatistica", "plot"):
        category, skill, provider = "Dados", "jupyter-live-kernel", "Python/Jupyter"
    elif has("excel", "xlsx", "planilha"):
        category, skill, provider = "Planilha", "xlsx", "Excel"
    elif has("site", "website", "landing page", "frontend", "web app", "página web", "pagina web"):
        category, skill, provider = "Site", "popular-web-designs", "Web/Vercel"
    elif has("supabase", "autenticação", "autenticacao", "login", "rls", "postgres"):
        category, skill, provider = "Backend", "supabase", "Supabase"
    elif has("github", "pull request", " pr ", "issue", "repositório", "repositorio"):
        category, skill, provider = "Código", "github", "GitHub"
    elif has("pdf"):
        category, skill, provider = "Documento", "pdf", "PDF"
    elif has("docx", "word"):
        category, skill, provider = "Documento", "docx", "Word"
    elif has("powerpoint", "pptx", "slides", "apresentação", "apresentacao"):
        category, skill, provider = "Apresentação", "powerpoint", "PowerPoint"
    elif has("mapa", "endereços", "enderecos", "geográfico", "geografico"):
        category, skill, provider = "Mapa", "maps", "Mapas"
    elif has("pesquise", "pesquisar", "pesquisa", "procure na web", "notícias", "noticias"):
        category, skill, provider = "Pesquisa", "web-research", "Web"
    elif has("navegador", "browser", "clique", "preencha", "interface"):
        category, skill, provider = "Automação", "computer-use", "Browser"
    elif has("música", "musica", "áudio", "audio", "som", "efeito sonoro", "voz"):
        category, skill, provider = "Áudio", "songwriting-and-ai-music", "Áudio/externo"
    elif has("código", "codigo", "bug", "erro", "debug", "programa", "script"):
        category, skill, provider = "Código", "systematic-debugging", "Hermes"

    if route == "matrix":
        provider = "Matrix" if category == "Geral" else provider
    elif route == "local":
        provider = "Hermes Local" if category == "Geral" else provider
    elif route == "auto" and category == "Geral":
        provider = "GPT-6 Sol"

    return {"category": category, "skill": skill, "provider": provider}

def cache_image_from_text(text):
    urls=re.findall(r'https?://[^\s<>"\']+', text or "")
    for raw_url in urls[:3]:
        url=raw_url.rstrip(").,;]")
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"image/*,*/*;q=0.8"})
            with urllib.request.urlopen(req,timeout=12) as res:
                ctype=(res.headers.get("Content-Type","") or "").split(";",1)[0].strip().lower()
                if not ctype.startswith("image/"):
                    continue
                length=res.headers.get("Content-Length")
                if length and int(length)>15*1024*1024:
                    continue
                raw=res.read(15*1024*1024+1)
                if len(raw)>15*1024*1024:
                    continue
            mid=uuid.uuid4().hex
            now=time.time()
            with MEDIA_LOCK:
                for key,val in list(MEDIA_STORE.items()):
                    if now-val["created"]>MEDIA_TTL:
                        MEDIA_STORE.pop(key,None)
                MEDIA_STORE[mid]={"bytes":raw,"mime":ctype or "image/png","created":now}
            print(f"[hermes-simple] cached inline image bytes={len(raw)}",flush=True)
            return mid
        except Exception as e:
            print(f"[hermes-simple] inline image fetch skipped type={type(e).__name__}",flush=True)
    return None

def store_media(raw, mime):
    mid=uuid.uuid4().hex
    now=time.time()
    with MEDIA_LOCK:
        for key,val in list(MEDIA_STORE.items()):
            if now-val["created"]>MEDIA_TTL:
                MEDIA_STORE.pop(key,None)
        MEDIA_STORE[mid]={"bytes":raw,"mime":mime,"created":now}
    return mid

def is_video_request(text):
    t=(text or "").lower()
    return any(x in t for x in ("vídeo","video","animar","animação","animacao","reels","transforme em vídeo","transforme em video"))

def generate_local_video(image_bytes, mime):
    suffix=".png"
    if "jpeg" in mime or "jpg" in mime: suffix=".jpg"
    elif "webp" in mime: suffix=".webp"
    with tempfile.TemporaryDirectory() as td:
        src=os.path.join(td,"input"+suffix)
        out=os.path.join(td,"output.mp4")
        with open(src,"wb") as fh: fh.write(image_bytes)
        vf=("scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
            "zoompan=z='min(zoom+0.0008,1.10)':d=150:s=1080x1920:fps=30,"
            "format=yuv420p")
        cmd=["ffmpeg","-y","-loop","1","-i",src,"-vf",vf,"-t","5","-c:v","libx264","-preset","veryfast","-crf","23","-movflags","+faststart",out]
        p=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=90)
        if p.returncode!=0: raise RuntimeError("ffmpeg_failed")
        with open(out,"rb") as fh: raw=fh.read()
    return store_media(raw,"video/mp4")

def response_text(data):
    parts=[]
    for item in data.get("output",[]) or []:
        if item.get("type")=="message":
            for c in item.get("content",[]) or []:
                if c.get("type") in ("output_text","text") and c.get("text"):
                    parts.append(c["text"])
    if parts:
        return "\n".join(parts).strip()
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()
    return ""

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self, fmt, *args):
        print("[hermes-simple] "+(fmt%args), flush=True)
    def sendb(self,status,body,ctype="application/json; charset=utf-8"):
        if isinstance(body,str): body=body.encode()
        self.send_response(status)
        self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def require_auth(self):
        if auth_ok(self.headers): return True
        self.send_response(401)
        self.send_header("WWW-Authenticate",'Basic realm="Hermes"')
        self.send_header("Content-Length","0")
        self.end_headers()
        return False
    def do_GET(self):
        if self.path=="/health":
            return self.sendb(200,'{"status":"ok"}')
        if not self.require_auth(): return
        path=self.path.split("?",1)[0]
        if path.startswith("/api/media/"):
            mid=path.rsplit("/",1)[-1]
            with MEDIA_LOCK:
                item=MEDIA_STORE.get(mid)
            if not item:
                return self.sendb(404,'{"error":"media_not_found"}')
            return self.sendb(200,item["bytes"],item["mime"])
        if self.path.split("?",1)[0] in ("/","/index.html","/chat"):
            return self.sendb(200,HTML,"text/html; charset=utf-8")
        return self.sendb(404,'{"error":"not_found"}')
    def do_POST(self):
        if not self.require_auth(): return
        if self.path not in ("/api/chat","/api/upload"):
            return self.sendb(404,'{"error":"not_found"}')
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n>18*1024*1024:
                return self.sendb(413,'{"error":"Arquivo muito grande"}')
            msg=json.loads(self.rfile.read(n) or b"{}")
            if self.path=="/api/upload":
                data=(msg.get("data") or "")
                mime=(msg.get("mime") or "image/png").lower()
                if not mime.startswith("image/") or "," not in data:
                    return self.sendb(400,'{"error":"Imagem inválida"}')
                raw=base64.b64decode(data.split(",",1)[1],validate=False)
                if len(raw)>12*1024*1024:
                    return self.sendb(413,'{"error":"Imagem muito grande"}')
                mid=store_media(raw,mime)
                return self.sendb(200,json.dumps({"id":mid,"url":"/api/media/"+mid},ensure_ascii=False))
            text=(msg.get("input") or "").strip()
            conv=(msg.get("conversation") or "").strip()
            route=(msg.get("route") or "auto").strip()
            attachment_id=(msg.get("attachmentId") or "").strip()
            if not text:
                return self.sendb(400,'{"error":"Mensagem vazia"}')
            if attachment_id and is_video_request(text):
                with MEDIA_LOCK:
                    item=MEDIA_STORE.get(attachment_id)
                if not item or not str(item.get("mime","")).startswith("image/"):
                    return self.sendb(400,json.dumps({"error":"A imagem anexada não está mais disponível. Anexe novamente."},ensure_ascii=False))
                vid=generate_local_video(item["bytes"],item["mime"])
                meta={"category":"Vídeo","skill":"video-local","provider":"Local · custo zero"}
                return self.sendb(200,json.dumps({"text":"Vídeo criado localmente em 5 segundos, sem usar provider pago.","via":"local-ffmpeg","routeMeta":meta,"videoUrl":"/api/media/"+vid},ensure_ascii=False))
            if route=="global-public":
                if attachment_id:
                    return self.sendb(400,json.dumps({"error":"A rota pública não aceita anexos ou histórico privado. Selecione Automático para isso."},ensure_ascii=False))
                result=call_public_deepseek(text)
                return self.sendb(200,json.dumps({"text":result,"via":"DeepSeek V4 Flash · público",
                    "routeMeta":{"category":"IA pública","skill":"hermes-worldwide-model-router","provider":"DeepSeek V4 Flash · endpoint público"},
                    "imageUrl":None},ensure_ascii=False))
            # Once HF_TOKEN is supplied in Railway Shared Variables, route normal
            # text chat to official HF. Execution/media/tool tasks retain bridge.
            if route=="auto" and not attachment_id and 0<len(text)<=8000 and classify_route(text,route).get("category")=="Geral":
                if os.getenv("HF_TOKEN","").startswith("hf_"):
                    try:
                        hf_text,hf_model=hf_official_chat(text)
                        return self.sendb(200,json.dumps({"text":hf_text,"via":"huggingface-official",
                            "routeMeta":{"category":"Geral","skill":"hermes-worldwide-model-router",
                                         "provider":"Hugging Face · "+hf_model},
                            "imageUrl":None},ensure_ascii=False))
                    except Exception as ex:
                        # Never log sensitive text, upstream error body or HF token.
                        print("[hermes-simple] HF official unavailable: "+type(ex).__name__+"; continuing private bridge",flush=True)
            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="matrix":
                payload.update({"provider":"matrix","model":"claude-opus-5"})
            elif route=="local":
                payload.update({"provider":"hermes-local","model":"hermes-agent"})
            data, via=call_upstream(payload)
            out=response_text(data)
            if not out:
                out="O Hermes concluiu a execução, mas não retornou texto."
            route_meta=classify_route(text, route)
            image_url=None
            if route_meta.get("category")=="Imagem":
                mid=cache_image_from_text(out)
                if mid:
                    image_url="/api/media/"+mid
            return self.sendb(200,json.dumps({"text":out,"via":via,"routeMeta":route_meta,"imageUrl":image_url},ensure_ascii=False))
        except Exception as e:
            print("[hermes-simple] chat error "+type(e).__name__+": "+str(e)[:500],flush=True)
            return self.sendb(502,json.dumps({"error":"Não consegui falar com o Hermes agora. Tente novamente.","type":type(e).__name__},ensure_ascii=False))

if __name__=="__main__":
    if not PASSWORD:
        raise SystemExit("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD missing")
    print(f"[hermes-simple] listening on 0.0.0.0:{PORT}",flush=True)
    threading.Thread(target=bridge_smoke, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
