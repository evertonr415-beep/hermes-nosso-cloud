from pathlib import Path
import re

p=Path('/app/hermes-simple.py')
s=p.read_text()

helpers = r'''
ACCOUNT_MEMORY_CACHE={}
ACCOUNT_MEMORY_LOCK=threading.Lock()
ACCOUNT_MEMORY_CACHE_TTL=20

def _memory_username(headers):
    try:
        user=session_user(headers) or {}
        name=str(user.get("username") or "").strip()
        if name:
            return name
    except Exception:
        pass
    return str(USER or "owner").strip() or "owner"

def _memory_id(headers):
    username=_memory_username(headers)
    digest=hmac.new(b"hermes-account-memory-v1",username.encode("utf-8"),"sha256").hexdigest()[:24]
    return "hermes-memory-v1-"+digest

def _memory_default():
    return {"version":1,"notes":[],"recent":[],"updated":time.time()}

def load_account_memory(headers):
    key=_memory_id(headers)
    now=time.time()
    with ACCOUNT_MEMORY_LOCK:
        cached=ACCOUNT_MEMORY_CACHE.get(key)
        if cached and cached[0]>now:
            return dict(cached[1])
    mem=_memory_default()
    try:
        data,status=_persistent_media_call("get",{"id":key})
        if status==200 and data and data.get("data"):
            raw=base64.b64decode(data["data"])
            loaded=json.loads(raw.decode("utf-8","ignore") or "{}")
            if isinstance(loaded,dict):
                mem.update(loaded)
    except Exception as exc:
        print(f"[hermes-simple] memory load error={type(exc).__name__}",flush=True)
    if not isinstance(mem.get("notes"),list): mem["notes"]=[]
    if not isinstance(mem.get("recent"),list): mem["recent"]=[]
    with ACCOUNT_MEMORY_LOCK:
        ACCOUNT_MEMORY_CACHE[key]=(now+ACCOUNT_MEMORY_CACHE_TTL,dict(mem))
    return mem

def save_account_memory(headers, mem):
    key=_memory_id(headers)
    mem=dict(mem or {})
    mem["version"]=1
    mem["notes"]=(mem.get("notes") or [])[-80:]
    mem["recent"]=(mem.get("recent") or [])[-30:]
    mem["updated"]=time.time()
    raw=json.dumps(mem,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    ok=False
    try:
        data,status=_persistent_media_call("store",{
            "id":key,
            "mime":"image/png",
            "data":base64.b64encode(raw).decode("ascii"),
        })
        ok=(status==200)
        if not ok:
            print(f"[hermes-simple] memory save status={status}",flush=True)
    except Exception as exc:
        print(f"[hermes-simple] memory save error={type(exc).__name__}",flush=True)
    with ACCOUNT_MEMORY_LOCK:
        ACCOUNT_MEMORY_CACHE[key]=(time.time()+ACCOUNT_MEMORY_CACHE_TTL,dict(mem))
    return ok

def _normalize_memory_note(text):
    t=" ".join(str(text or "").strip().split())
    prefixes=(
        "lembre que ","lembre-se que ","guarde que ","memorize que ",
        "minha preferência é ","minha preferencia e ","prefiro que ",
        "a partir de agora ","sempre use ","sempre faça ","sempre faca "
    )
    low=t.lower()
    for pref in prefixes:
        if low.startswith(pref):
            t=t[len(pref):].strip()
            break
    return t[:1200]

def maybe_remember_explicit(headers, text):
    raw=" ".join(str(text or "").strip().split())
    low=raw.lower()
    triggers=(
        "lembre que ","lembre-se que ","guarde que ","memorize que ",
        "minha preferência é ","minha preferencia e ","prefiro que ",
        "a partir de agora ","sempre use ","sempre faça ","sempre faca "
    )
    if not any(low.startswith(x) for x in triggers):
        return False
    note=_normalize_memory_note(raw)
    if not note:
        return False
    mem=load_account_memory(headers)
    notes=mem.get("notes") or []
    normalized=note.lower()
    notes=[n for n in notes if str((n or {}).get("text") or "").strip().lower()!=normalized]
    notes.append({"id":uuid.uuid4().hex[:12],"text":note,"created":time.time()})
    mem["notes"]=notes[-80:]
    return save_account_memory(headers,mem)

def memory_record_exchange(headers, user_text, assistant_text):
    try:
        mem=load_account_memory(headers)
        recent=mem.get("recent") or []
        recent.append({
            "at":time.time(),
            "user":" ".join(str(user_text or "").split())[:1200],
            "assistant":" ".join(str(assistant_text or "").split())[:1600],
        })
        mem["recent"]=recent[-30:]
        save_account_memory(headers,mem)
    except Exception as exc:
        print(f"[hermes-simple] memory record error={type(exc).__name__}",flush=True)

def account_memory_instruction(headers):
    try:
        mem=load_account_memory(headers)
    except Exception:
        return ""
    notes=mem.get("notes") or []
    recent=mem.get("recent") or []
    if not notes and not recent:
        return ""
    lines=["[MEMÓRIA PERSISTENTE DA CONTA]","Use estes dados apenas quando forem relevantes ao pedido atual. Não invente fatos ausentes."]
    if notes:
        lines.append("Preferências/fatos salvos:")
        for n in notes[-24:]:
            txt=str((n or {}).get("text") or "").strip()
            if txt:
                lines.append("- "+txt[:700])
    if recent:
        lines.append("Contexto recente entre conversas:")
        for x in recent[-6:]:
            u=str((x or {}).get("user") or "").strip()
            a=str((x or {}).get("assistant") or "").strip()
            if u: lines.append("Usuário: "+u[:450])
            if a: lines.append("Hermes: "+a[:600])
    lines.append("[FIM DA MEMÓRIA]")
    return "\n".join(lines)+"\n\n"

'''

if 'def load_account_memory(headers):' not in s:
    anchor='def bridge_smoke():\n'
    if anchor not in s:
        raise SystemExit('memory helper anchor not found')
    s=s.replace(anchor,helpers+anchor,1)

memory_html = r'''MEMORY_HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hermes · Memória</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f6f4;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#202123}.wrap{max-width:920px;margin:36px auto;padding:0 20px}.top{display:flex;justify-content:space-between;align-items:center;gap:15px}.card{background:#fff;border:1px solid #e5e5e1;border-radius:16px;padding:20px;margin-top:18px;box-shadow:0 8px 28px rgba(0,0,0,.04)}h1,h3{margin-top:0}.muted{color:#777;font-size:13px;line-height:1.45}.item{padding:12px 0;border-top:1px solid #eee}.item:first-child{border-top:0}.row{display:flex;gap:8px;align-items:flex-start}.grow{flex:1}button,a.btn{border:0;border-radius:10px;padding:10px 13px;background:#171717;color:#fff;cursor:pointer;text-decoration:none;font-size:14px}.secondary{background:#ececea!important;color:#222!important}.danger{background:#8d2020!important}textarea{width:100%;min-height:90px;padding:12px;border:1px solid #d8d8d3;border-radius:10px;resize:vertical}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px}.small{font-size:12px;color:#888}@media(max-width:650px){.top{align-items:flex-start;flex-direction:column}}</style></head><body><div class="wrap"><div class="top"><div><h1>Memória do Hermes</h1><div class="muted">Memória persistente da conta. Continua disponível em outro dispositivo e depois de novos deployments.</div></div><a class="btn secondary" href="/">Voltar</a></div>
<div class="card"><h3>Adicionar memória</h3><textarea id="note" maxlength="1200" placeholder="Ex.: Prefiro respostas diretas e, quando eu pedir sistema, quero código funcional e teste completo."></textarea><div class="actions"><button id="add">Salvar memória</button><span id="msg" class="small"></span></div></div>
<div class="card"><h3>Memórias salvas</h3><div id="notes" class="muted">Carregando…</div></div>
<div class="card"><h3>Contexto recente</h3><div class="muted">O Hermes mantém um histórico resumido das conversas recentes para dar continuidade entre chats.</div><div id="recent" style="margin-top:10px"></div><div class="actions"><button class="secondary" id="clearRecent">Limpar contexto recente</button><button class="danger" id="clearAll">Limpar todas as memórias</button></div></div>
</div><script>
async function api(path,opt={}){const r=await fetch(path,{...opt,cache:'no-store'});const j=await r.json().catch(()=>({}));if(r.status===401){location.href='/login';throw 0}if(!r.ok)throw new Error(j.error||'Falha');return j}
function esc(s){return String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function load(){try{const j=await api('/api/memory');const m=j.memory||{};const ns=m.notes||[];notes.innerHTML=ns.length?ns.map(n=>'<div class="item row"><div class="grow">'+esc(n.text)+'</div><button class="secondary" onclick="delNote(\''+esc(n.id)+'\')">Excluir</button></div>').join(''):'Nenhuma memória manual salva.';const rs=m.recent||[];recent.innerHTML=rs.length?rs.slice(-10).reverse().map(x=>'<div class="item"><div><b>Você:</b> '+esc(x.user)+'</div><div class="small" style="margin-top:5px"><b>Hermes:</b> '+esc(x.assistant)+'</div></div>').join(''):'<div class="muted">Sem contexto recente.</div>'}catch(e){notes.textContent=e.message||'Falha';}}
add.onclick=async()=>{const t=note.value.trim();if(!t)return;msg.textContent='Salvando…';try{await api('/api/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'add',text:t})});note.value='';msg.textContent='Salvo.';load()}catch(e){msg.textContent=e.message||'Falha'}};
window.delNote=async id=>{await api('/api/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'delete',id})});load()};
clearRecent.onclick=async()=>{if(!confirm('Limpar somente o contexto recente?'))return;await api('/api/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'clear_recent'})});load()};
clearAll.onclick=async()=>{if(!confirm('Apagar todas as memórias e o contexto recente desta conta?'))return;await api('/api/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'clear_all'})});load()};
load();
</script></body></html>"""
'''

if 'MEMORY_HTML = r' not in s:
    anchor='RULES_HTML = r'
    if anchor in s:
        s=s.replace(anchor,memory_html+anchor,1)
    else:
        anchor='def _cookie_token(headers):\n'
        if anchor not in s:
            raise SystemExit('memory html anchor not found')
        s=s.replace(anchor,memory_html+anchor,1)

if 'href="/admin/memory"' not in s:
    anchor='href="/admin/rules">⚙ Regras do Hermes</a>'
    if anchor in s:
        s=s.replace(anchor,anchor+'<br><a class="advanced" href="/admin/memory">🧠 Memória</a>',1)
    else:
        s=s.replace('</aside>','  <div class="sidebottom"><a class="advanced" href="/admin/memory">🧠 Memória</a></div>\n  </aside>',1)

get_anchor='        if path=="/api/chat/status":\n'
get_insert='''        if path=="/admin/memory":
            return self.sendb(200,MEMORY_HTML,"text/html; charset=utf-8")
        if path=="/api/memory":
            return self.sendb(200,json.dumps({"ok":True,"memory":load_account_memory(self.headers)},ensure_ascii=False))
        if path=="/api/chat/status":
'''
if 'path=="/admin/memory"' not in s:
    if get_anchor not in s:
        raise SystemExit('memory GET anchor not found')
    s=s.replace(get_anchor,get_insert,1)

post_anchor='        if path=="/api/chat/start":\n'
post_insert='''        if path=="/api/memory":
            try:
                n=int(self.headers.get("Content-Length","0"))
                msg=json.loads(self.rfile.read(n) or b"{}") if n else {}
                action=str(msg.get("action") or "").strip()
                mem=load_account_memory(self.headers)
                if action=="add":
                    note=_normalize_memory_note(msg.get("text") or "")
                    if not note: return self.sendb(400,json.dumps({"error":"Memória vazia"},ensure_ascii=False))
                    notes=mem.get("notes") or []
                    notes.append({"id":uuid.uuid4().hex[:12],"text":note,"created":time.time()})
                    mem["notes"]=notes[-80:]
                elif action=="delete":
                    nid=str(msg.get("id") or "")
                    mem["notes"]=[x for x in (mem.get("notes") or []) if str((x or {}).get("id") or "")!=nid]
                elif action=="clear_recent":
                    mem["recent"]=[]
                elif action=="clear_all":
                    mem=_memory_default()
                else:
                    return self.sendb(400,json.dumps({"error":"Ação inválida"},ensure_ascii=False))
                save_account_memory(self.headers,mem)
                return self.sendb(200,json.dumps({"ok":True,"memory":mem},ensure_ascii=False))
            except Exception as exc:
                print(f"[hermes-simple] memory api error={type(exc).__name__}",flush=True)
                return self.sendb(400,json.dumps({"error":"Não foi possível atualizar a memória."},ensure_ascii=False))
        if path=="/api/chat/start":
'''
if 'if path=="/api/memory":' not in s[s.find('def do_POST'):]:
    if post_anchor not in s:
        raise SystemExit('memory POST anchor not found')
    s=s.replace(post_anchor,post_insert,1)

# Observe explicit "remember" instructions as soon as the message enters the worker.
empty_anchor='''            if not text:
                return self.sendb(400,'{"error":"Mensagem vazia"}')
'''
empty_new=empty_anchor+'            maybe_remember_explicit(self.headers,text)\n'
if 'maybe_remember_explicit(self.headers,text)' not in s:
    if empty_anchor not in s:
        raise SystemExit('memory observe anchor not found')
    s=s.replace(empty_anchor,empty_new,1)

# Inject memory after owner rules so every normal text/multimodal request receives it.
s=s.replace(
    'owner_mode + client_rules_instruction(self.headers) + text',
    'owner_mode + client_rules_instruction(self.headers) + account_memory_instruction(self.headers) + text'
)
s=s.replace(
    'owner_mode + client_rules_instruction(self.headers) + paid_text',
    'owner_mode + client_rules_instruction(self.headers) + account_memory_instruction(self.headers) + paid_text'
)

# Store the completed general answer into cross-chat recent memory.
route_anchor='            route_meta=classify_route(text, route)\n'
if 'memory_record_exchange(self.headers,text,out)' not in s:
    if route_anchor not in s:
        raise SystemExit('memory record anchor not found')
    s=s.replace(route_anchor,'            memory_record_exchange(self.headers,text,out)\n'+route_anchor,1)

p.write_text(s)
print('persistent account memory patch applied')
