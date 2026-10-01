from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Shared auth service configuration.
anchor='ADVANCED_URL = os.getenv("HERMES_ADVANCED_URL", "https://hermes-cloud-production-13fb.up.railway.app")\n'
insert='''ADVANCED_URL = os.getenv("HERMES_ADVANCED_URL", "https://hermes-cloud-production-13fb.up.railway.app")
AUTH_EDGE_URL = os.getenv("HERMES_AUTH_EDGE_URL", "").rstrip("/")
AUTH_EDGE_SECRET = os.getenv("HERMES_AUTH_EDGE_SECRET", "")
AUTH_BOOTSTRAP_SECRET = os.getenv("HERMES_AUTH_BOOTSTRAP_SECRET", "")
AUTH_CACHE = {}
AUTH_CACHE_LOCK = threading.Lock()
AUTH_CACHE_TTL = 60
'''
if anchor not in s:
    raise SystemExit('auth config anchor not found')
s=s.replace(anchor,insert,1)

old='''def auth_ok(headers):
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
'''
new=r'''LOGIN_HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hermes · Login</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f6f6f4;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#202123}.card{width:min(92vw,390px);background:#fff;border:1px solid #e5e5e1;border-radius:20px;padding:30px;box-shadow:0 16px 50px rgba(0,0,0,.08)}.logo{width:44px;height:44px;border-radius:13px;background:#171717;color:#fff;display:grid;place-items:center;font-weight:800;font-size:20px;margin-bottom:18px}h1{font-size:25px;margin:0 0 6px}p{color:#73767b;margin:0 0 24px;font-size:14px}label{display:block;font-size:13px;margin:13px 0 6px}input{width:100%;padding:12px 13px;border:1px solid #d8d8d3;border-radius:10px;outline:none}input:focus{border-color:#111}button{width:100%;margin-top:18px;border:0;border-radius:11px;padding:12px;background:#171717;color:#fff;font-weight:650;cursor:pointer}.err{min-height:20px;margin-top:12px;color:#b42318;font-size:13px}</style></head><body><div class="card"><div class="logo">H</div><h1>Hermes</h1><p>Acesso privado. Entre com uma conta autorizada.</p><form id="f"><label>Usuário</label><input id="u" autocomplete="username" required><label>Senha</label><input id="p" type="password" autocomplete="current-password" required><button id="b">Entrar</button><div class="err" id="e"></div></form></div><script>f.onsubmit=async(ev)=>{ev.preventDefault();e.textContent='';b.disabled=true;try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.error==='invalid_credentials'?'Usuário ou senha incorretos.':'Não foi possível entrar.');location.href='/';}catch(x){e.textContent=x.message}finally{b.disabled=false}}</script></body></html>'''

ADMIN_HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hermes · Usuários</title><style>*{box-sizing:border-box}body{margin:0;background:#f6f6f4;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#202123}.wrap{max-width:850px;margin:40px auto;padding:0 20px}.top{display:flex;justify-content:space-between;align-items:center}.card{background:#fff;border:1px solid #e5e5e1;border-radius:16px;padding:20px;margin-top:18px}input{padding:10px 12px;border:1px solid #d8d8d3;border-radius:9px;margin-right:7px}button,a.btn{border:0;border-radius:9px;padding:10px 12px;background:#171717;color:#fff;cursor:pointer;text-decoration:none;font-size:14px}.secondary{background:#ececea!important;color:#222!important}.danger{background:#9b1c1c!important}.row{display:flex;align-items:center;gap:10px;padding:12px 0;border-top:1px solid #eee}.row:first-child{border-top:0}.name{flex:1}.meta{font-size:12px;color:#777}.msg{font-size:13px;margin-top:10px}</style></head><body><div class="wrap"><div class="top"><div><h1>Usuários do Hermes</h1><div class="meta">Somente o proprietário pode criar e administrar acessos.</div></div><a class="btn secondary" href="/">Voltar ao Hermes</a></div><div class="card"><h3>Criar usuário</h3><input id="u" placeholder="Usuário"><input id="p" type="password" placeholder="Senha (mín. 8 caracteres)"><button onclick="createUser()">Criar acesso</button><div class="msg" id="msg"></div></div><div class="card"><h3>Acessos</h3><div id="list">Carregando…</div></div></div><script>
async function api(path,opt={}){const r=await fetch(path,opt);const j=await r.json().catch(()=>({}));if(r.status===401){location.href='/login';throw 0}if(!r.ok)throw new Error(j.error||'Falha');return j}
async function load(){try{const j=await api('/api/admin/users');list.innerHTML=j.users.map(x=>`<div class="row"><div class="name"><b>${esc(x.username)}</b><div class="meta">${x.role==='owner'?'Proprietário':'Usuário'} · ${x.active?'Ativo':'Bloqueado'}</div></div>${x.role==='owner'?'':`<button class="secondary" onclick="toggle('${x.id}',${!x.active})">${x.active?'Bloquear':'Ativar'}</button><button class="danger" onclick="del('${x.id}')">Excluir</button>`}</div>`).join('')}catch(e){list.textContent=e.message||'Sem acesso'}}
function esc(s){return String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function createUser(){msg.textContent='';try{await api('/api/admin/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});u.value='';p.value='';msg.textContent='Usuário criado.';load()}catch(e){msg.textContent=e.message==='username_exists'?'Esse usuário já existe.':e.message}}
async function toggle(id,active){await api('/api/admin/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:id,active})});load()}
async function del(id){if(!confirm('Excluir este usuário?'))return;await api('/api/admin/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:id})});load()}load();</script></body></html>'''

def _cookie_token(headers):
    raw=headers.get("Cookie","") or ""
    for part in raw.split(";"):
        k,sep,v=part.strip().partition("=")
        if sep and k=="hermes_session": return v
    return ""

def _auth_call(action, payload=None, bootstrap=False):
    if not AUTH_EDGE_URL or not AUTH_EDGE_SECRET:
        raise RuntimeError("Hermes auth service not configured")
    body=dict(payload or {}); body["action"]=action
    headers={"Content-Type":"application/json","Accept":"application/json","X-Hermes-Auth":AUTH_EDGE_SECRET}
    if bootstrap: headers["X-Hermes-Bootstrap"]=AUTH_BOOTSTRAP_SECRET
    req=urllib.request.Request(AUTH_EDGE_URL,data=json.dumps(body).encode("utf-8"),method="POST",headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=20) as res:
            return json.load(res),res.status
    except urllib.error.HTTPError as e:
        raw=e.read(8192)
        try: data=json.loads(raw.decode("utf-8","ignore") or "{}")
        except Exception: data={"error":"auth_http_%s"%e.code}
        return data,e.code

def session_user(headers):
    token=_cookie_token(headers)
    if not token: return None
    now=time.time()
    with AUTH_CACHE_LOCK:
        cached=AUTH_CACHE.get(token)
        if cached and cached[0]>now: return cached[1]
    data,status=_auth_call("verify",{"token":token})
    user=data.get("user") if status==200 and data.get("ok") else None
    if user:
        with AUTH_CACHE_LOCK: AUTH_CACHE[token]=(now+AUTH_CACHE_TTL,user)
    return user

def auth_ok(headers):
    return bool(session_user(headers))

def bootstrap_owner():
    if not (USER and PASSWORD and AUTH_BOOTSTRAP_SECRET):
        print("[hermes-simple] private-auth bootstrap skipped",flush=True); return
    try:
        data,status=_auth_call("bootstrap",{"username":USER,"password":PASSWORD},bootstrap=True)
        print(f"[hermes-simple] private-auth bootstrap status={status} created={str(bool(data.get('created'))).lower()}",flush=True)
    except Exception as exc:
        print(f"[hermes-simple] private-auth bootstrap error={type(exc).__name__}",flush=True)
'''
if old not in s:
    raise SystemExit('auth function anchor not found')
s=s.replace(old,new,1)

old_req='''    def require_auth(self):
        if auth_ok(self.headers): return True
        self.send_response(401)
        self.send_header("WWW-Authenticate",'Basic realm="Hermes"')
        self.send_header("Content-Length","0")
        self.end_headers()
        return False
'''
new_req='''    def require_auth(self):
        user=session_user(self.headers)
        if user:
            self.current_user=user
            return True
        if self.command=="GET":
            self.send_response(302)
            self.send_header("Location","/login")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        else:
            self.sendb(401,json.dumps({"error":"login_required"},ensure_ascii=False))
        return False
'''
if old_req not in s:
    raise SystemExit('require_auth anchor not found')
s=s.replace(old_req,new_req,1)

old_get='''    def do_GET(self):
        if self.path=="/health":
            return self.sendb(200,'{"status":"ok"}')
        if not self.require_auth(): return
        path=self.path.split("?",1)[0]
'''
new_get='''    def do_GET(self):
        path=self.path.split("?",1)[0]
        if path=="/health":
            return self.sendb(200,'{"status":"ok"}')
        if path=="/login":
            if session_user(self.headers):
                self.send_response(302); self.send_header("Location","/"); self.send_header("Content-Length","0"); self.end_headers(); return
            return self.sendb(200,LOGIN_HTML,"text/html; charset=utf-8")
        if not self.require_auth(): return
        if path=="/api/session":
            return self.sendb(200,json.dumps({"ok":True,"user":self.current_user},ensure_ascii=False))
        if path=="/admin":
            if self.current_user.get("role")!="owner": return self.sendb(403,'{"error":"owner_required"}')
            return self.sendb(200,ADMIN_HTML,"text/html; charset=utf-8")
        if path=="/api/admin/users":
            if self.current_user.get("role")!="owner": return self.sendb(403,'{"error":"owner_required"}')
            data,status=_auth_call("list_users",{"token":_cookie_token(self.headers)})
            return self.sendb(status,json.dumps(data,ensure_ascii=False))
'''
if old_get not in s:
    raise SystemExit('do_GET anchor not found')
s=s.replace(old_get,new_get,1)

old_post='''    def do_POST(self):
        if not self.require_auth(): return
        if self.path not in ("/api/chat","/api/upload"):
            return self.sendb(404,'{"error":"not_found"}')
        try:
'''
new_post='''    def do_POST(self):
        path=self.path.split("?",1)[0]
        if path=="/api/login":
            try:
                n=int(self.headers.get("Content-Length","0")); msg=json.loads(self.rfile.read(n) or b"{}")
                data,status=_auth_call("login",{"username":str(msg.get("username") or ""),"password":str(msg.get("password") or "")})
                if status==200 and data.get("token"):
                    body=json.dumps({"ok":True,"user":data.get("user")},ensure_ascii=False).encode()
                    self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("Set-Cookie","hermes_session="+data["token"]+"; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=604800"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
                return self.sendb(status,json.dumps(data,ensure_ascii=False))
            except Exception as exc:
                print(f"[hermes-simple] login error={type(exc).__name__}",flush=True); return self.sendb(502,'{"error":"auth_unavailable"}')
        if path=="/api/logout":
            token=_cookie_token(self.headers)
            if token:
                try: _auth_call("logout",{"token":token})
                except Exception: pass
            body=b'{"ok":true}'; self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Set-Cookie","hermes_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        if not self.require_auth(): return
        if path in ("/api/admin/create","/api/admin/toggle","/api/admin/delete"):
            if self.current_user.get("role")!="owner": return self.sendb(403,'{"error":"owner_required"}')
            try:
                n=int(self.headers.get("Content-Length","0")); msg=json.loads(self.rfile.read(n) or b"{}")
                action={"/api/admin/create":"create_user","/api/admin/toggle":"set_active","/api/admin/delete":"delete_user"}[path]
                msg["token"]=_cookie_token(self.headers)
                data,status=_auth_call(action,msg)
                return self.sendb(status,json.dumps(data,ensure_ascii=False))
            except Exception as exc:
                print(f"[hermes-simple] admin auth error={type(exc).__name__}",flush=True); return self.sendb(502,'{"error":"auth_unavailable"}')
        if path not in ("/api/chat","/api/upload"):
            return self.sendb(404,'{"error":"not_found"}')
        try:
'''
if old_post not in s:
    raise SystemExit('do_POST anchor not found')
s=s.replace(old_post,new_post,1)

# Owner controls in the existing sidebar; normal users get a harmless link that server-side authorization still protects.
s=s.replace('<div class="sidebottom"><a class="advanced" href="__ADVANCED_URL__" target="_blank">⚙ Avançado</a></div>', '<div class="sidebottom"><a class="advanced" href="/admin">👤 Usuários</a><a class="advanced" href="__ADVANCED_URL__" target="_blank">⚙ Avançado</a><a class="advanced" href="#" onclick="fetch(\'/api/logout\',{method:\'POST\'}).then(()=>location.href=\'/login\');return false">↪ Sair</a></div>')

old_main='''if __name__=="__main__":
    if not PASSWORD:
        raise SystemExit("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD missing")
    print(f"[hermes-simple] listening on 0.0.0.0:{PORT}",flush=True)
    threading.Thread(target=bridge_smoke, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
'''
new_main='''if __name__=="__main__":
    if not PASSWORD:
        raise SystemExit("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD missing")
    if not (AUTH_EDGE_URL and AUTH_EDGE_SECRET and AUTH_BOOTSTRAP_SECRET):
        raise SystemExit("Hermes private authentication is not configured")
    bootstrap_owner()
    print(f"[hermes-simple] listening on 0.0.0.0:{PORT}",flush=True)
    threading.Thread(target=bridge_smoke, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
'''
if old_main not in s:
    raise SystemExit('main anchor not found')
s=s.replace(old_main,new_main,1)

p.write_text(s)
