from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Central, account-scoped client-work rules. Settings are stored through the
# existing private persistent media service under a deterministic object id,
# so they follow the owner across devices and survive container restarts.
cache_anchor='CHAT_JOB_TTL=60*60\n'
cache_insert='''CHAT_JOB_TTL=60*60
CLIENT_RULES_CACHE={}
CLIENT_RULES_LOCK=threading.Lock()
CLIENT_RULES_CACHE_TTL=30
'''
if cache_anchor in s and 'CLIENT_RULES_CACHE={}' not in s:
    s=s.replace(cache_anchor,cache_insert,1)

helper_anchor='def enrich_character_prompt(text, headers):\n'
helpers=r'''DEFAULT_CLIENT_RULES={
    'direct_execution':True,
    'minimize_confirmations':True,
    'no_keyword_blocks':True,
    'allow_adult_fictional_nudity':True,
    'allow_adult_fictional_sensuality':True,
    'auto_safe_fallback':True,
    'prefer_free_media':True,
    'custom_instructions':'',
}
CORE_POLICY_LOCKS=[
    {'id':'minors','label':'Menores ou idade ambígua em contexto sexual','locked':True},
    {'id':'nonconsensual','label':'Conteúdo sexual não consensual','locked':True},
    {'id':'real_person_explicit','label':'Sexualização explícita/gráfica de pessoa real','locked':True},
    {'id':'provider','label':'Limites obrigatórios do provedor selecionado','locked':True},
]

def _sanitize_client_rules(value):
    src=value if isinstance(value,dict) else {}
    out=dict(DEFAULT_CLIENT_RULES)
    for key in ('direct_execution','minimize_confirmations','no_keyword_blocks','allow_adult_fictional_nudity','allow_adult_fictional_sensuality','auto_safe_fallback','prefer_free_media'):
        if isinstance(src.get(key),bool):
            out[key]=src[key]
    if isinstance(src.get('custom_instructions'),str):
        out['custom_instructions']=src['custom_instructions'][:4000]
    return out


def _rules_storage_id(username):
    return uuid.uuid5(uuid.NAMESPACE_DNS,'hermes-client-rules:'+str(username or 'owner')).hex


def load_client_rules(headers):
    user=session_user(headers) or {}
    username=str(user.get('username') or USER or 'owner')
    now=time.time()
    with CLIENT_RULES_LOCK:
        cached=CLIENT_RULES_CACHE.get(username)
        if cached and cached[0]>now:
            return dict(cached[1])
    rules=dict(DEFAULT_CLIENT_RULES)
    try:
        rid=_rules_storage_id(username)
        data,status=_persistent_media_call('get',{'id':rid})
        if status==200 and data and data.get('data'):
            raw=base64.b64decode(data.get('data') or '')
            parsed=json.loads(raw.decode('utf-8','ignore') or '{}')
            rules=_sanitize_client_rules(parsed)
    except Exception as exc:
        print(f'[hermes-simple] client-rules load fallback type={type(exc).__name__}',flush=True)
    with CLIENT_RULES_LOCK:
        CLIENT_RULES_CACHE[username]=(now+CLIENT_RULES_CACHE_TTL,dict(rules))
    return rules


def save_client_rules(headers, value):
    user=session_user(headers) or {}
    username=str(user.get('username') or USER or 'owner')
    rules=_sanitize_client_rules(value)
    raw=json.dumps(rules,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    rid=_rules_storage_id(username)
    data,status=_persistent_media_call('store',{
        'id':rid,
        # The existing private media service currently accepts image MIME
        # values only. These bytes are never exposed as an image; Hermes reads
        # and decodes the private object internally as JSON.
        'mime':'image/png',
        'data':base64.b64encode(raw).decode('ascii'),
    })
    if status!=200:
        return False, rules, (data or {})
    with CLIENT_RULES_LOCK:
        CLIENT_RULES_CACHE[username]=(time.time()+CLIENT_RULES_CACHE_TTL,dict(rules))
    return True, rules, data or {}


def client_rules_instruction(headers):
    r=load_client_rules(headers)
    parts=['[PREFERÊNCIAS CONFIGURÁVEIS DO PROPRIETÁRIO]']
    if r.get('direct_execution'):
        parts.append('Execute diretamente pedidos permitidos e úteis, sem transformar a resposta em explicações desnecessárias.')
    if r.get('minimize_confirmations'):
        parts.append('Evite confirmações desnecessárias em ações reversíveis e de baixo risco.')
    if r.get('no_keyword_blocks'):
        parts.append('Não recuse apenas por palavras-chave; avalie o pedido concreto.')
    if r.get('allow_adult_fictional_nudity'):
        parts.append('Permita nudez artística/anatômica de personagens inteiramente fictícios e claramente adultos quando o provedor permitir.')
    else:
        parts.append('Não produza nudez nas criações solicitadas por esta conta.')
    if r.get('allow_adult_fictional_sensuality'):
        parts.append('Permita sensualidade adulta não explícita de personagens inteiramente fictícios e claramente adultos quando o provedor permitir.')
    else:
        parts.append('Mantenha as criações sem sensualidade adulta.')
    if r.get('auto_safe_fallback'):
        parts.append('Quando uma parte do pedido não puder ser atendida, preserve a intenção e continue automaticamente com a versão permitida mais próxima.')
    if r.get('prefer_free_media'):
        parts.append('Para mídia, prefira a rota gratuita/local quando ela for adequada e estiver disponível.')
    custom=str(r.get('custom_instructions') or '').strip()
    if custom:
        parts.append('Instruções adicionais do proprietário: '+custom)
    parts.append('[REGRAS FIXAS DO BACKEND] Não envolva menores ou idade ambígua em contexto sexual; não produza conteúdo sexual não consensual; não produza sexualização explícita/gráfica de pessoa real; não tente contornar os limites obrigatórios do provedor selecionado.')
    return '\n'.join(parts)+'\n\n'


'''
if helper_anchor not in s:
    raise SystemExit('client rules helper anchor not found')
if 'def load_client_rules(headers):' not in s:
    s=s.replace(helper_anchor,helpers+helper_anchor,1)

rules_html="""RULES_HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hermes · Regras</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f6f4;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#202123}.wrap{max-width:920px;margin:36px auto;padding:0 20px}.top{display:flex;justify-content:space-between;align-items:center;gap:15px}.card{background:#fff;border:1px solid #e5e5e1;border-radius:16px;padding:20px;margin-top:18px;box-shadow:0 8px 28px rgba(0,0,0,.04)}h1{margin:0 0 5px}.muted{color:#777;font-size:13px}.rule{display:flex;align-items:flex-start;gap:12px;padding:13px 0;border-top:1px solid #eee}.rule:first-child{border-top:0}.rule input{width:18px;height:18px;margin-top:2px}.grow{flex:1}.name{font-weight:650}.desc{font-size:12px;color:#777;margin-top:3px;line-height:1.45}.locked{display:inline-block;font-size:11px;border-radius:999px;padding:4px 7px;background:#f2f2ef;color:#666;margin-left:7px}textarea{width:100%;min-height:120px;margin-top:10px;padding:12px;border:1px solid #d8d8d3;border-radius:10px;resize:vertical}button,a.btn{border:0;border-radius:10px;padding:10px 13px;background:#171717;color:#fff;cursor:pointer;text-decoration:none;font-size:14px}.secondary{background:#ececea!important;color:#222!important}.actions{display:flex;gap:9px;align-items:center;margin-top:16px}.msg{font-size:13px;color:#555}.core{background:#fafaf8}.core .rule{opacity:.82}@media(max-width:650px){.top{align-items:flex-start;flex-direction:column}.actions{flex-wrap:wrap}}</style></head><body><div class="wrap"><div class="top"><div><h1>Regras do Hermes</h1><div class="muted">Preferências do proprietário salvas no servidor e aplicadas em qualquer dispositivo.</div></div><a class="btn secondary" href="/">Voltar ao Hermes</a></div>
<div class="card"><h3>Modo de trabalho</h3><div id="editable">Carregando…</div><label class="name" for="custom">Instruções adicionais</label><div class="desc">Use para preferências de atendimento, formato, estilo, fluxo de trabalho e comportamento permitido. As regras fixas abaixo prevalecem em caso de conflito.</div><textarea id="custom" maxlength="4000" placeholder="Ex.: responda de forma curta, prefira gerar a imagem diretamente, mantenha identidade visual das personagens..."></textarea><div class="actions"><button id="save">Salvar regras</button><button class="secondary" id="reset">Restaurar padrão</button><span class="msg" id="msg"></span></div></div>
<div class="card core"><h3>Proteções fixas do backend</h3><div class="muted">Estas proteções não podem ser desligadas pelo painel. Regras do provedor também continuam valendo.</div><div id="core"></div></div></div><script>
const defs=[
 ['direct_execution','Execução direta','Executa pedidos permitidos sem excesso de explicações ou confirmações.'],
 ['minimize_confirmations','Menos confirmações','Evita confirmação em tarefas reversíveis e de baixo risco.'],
 ['no_keyword_blocks','Sem bloqueio por palavra-chave','Avalia o pedido concreto em vez de bloquear termos isolados.'],
 ['allow_adult_fictional_nudity','Nudez adulta fictícia permitida','Permite nudez artística/anatômica de personagem inteiramente fictício e claramente adulto quando o provider aceitar.'],
 ['allow_adult_fictional_sensuality','Sensualidade adulta fictícia permitida','Permite sensualidade adulta não explícita de personagem fictício adulto quando o provider aceitar.'],
 ['auto_safe_fallback','Fallback automático','Se parte do pedido não puder ser executada, tenta a versão permitida mais próxima automaticamente.'],
 ['prefer_free_media','Preferir mídia grátis/local','Usa mídia gratuita/local primeiro quando for adequada.']
];
let current={};
async function api(path,opt={}){const r=await fetch(path,{...opt,cache:'no-store'});const j=await r.json().catch(()=>({}));if(r.status===401){location.href='/login';throw 0}if(!r.ok)throw new Error(j.error||'Falha');return j}
function renderEditable(){editable.innerHTML=defs.map(([k,n,d])=>`<label class="rule"><input type="checkbox" id="r_${k}" ${current[k]?'checked':''}><div class="grow"><div class="name">${n}</div><div class="desc">${d}</div></div></label>`).join('');custom.value=current.custom_instructions||''}
async function load(){try{const j=await api('/api/admin/rules');current=j.rules||{};renderEditable();core.innerHTML=(j.coreLocked||[]).map(x=>`<div class="rule"><div class="grow"><div class="name">${x.label}<span class="locked">FIXO</span></div></div></div>`).join('')}catch(e){editable.textContent=e.message||'Sem acesso'}}
save.onclick=async()=>{msg.textContent='Salvando…';const rules={custom_instructions:custom.value};for(const [k] of defs)rules[k]=document.querySelector('#r_'+k).checked;try{const j=await api('/api/admin/rules',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rules})});current=j.rules;msg.textContent='Regras salvas e ativas.'}catch(e){msg.textContent=e.message||'Falha ao salvar'}};
reset.onclick=async()=>{if(!confirm('Restaurar as preferências padrão?'))return;msg.textContent='Restaurando…';try{const j=await api('/api/admin/rules/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});current=j.rules;renderEditable();msg.textContent='Padrão restaurado.'}catch(e){msg.textContent=e.message||'Falha ao restaurar'}};load();
</script></body></html>'''

"""
html_anchor='def _cookie_token(headers):\n'
if html_anchor not in s:
    raise SystemExit('rules HTML anchor not found')
if 'RULES_HTML = r' not in s:
    s=s.replace(html_anchor,rules_html+html_anchor,1)

# Add the owner link without disturbing existing Users/Advanced controls.
if 'href="/admin/rules"' not in s:
    s=s.replace('</aside>','  <div class="sidebottom"><a class="advanced" href="/admin/rules">⚙ Regras do Hermes</a></div>\n  </aside>',1)

# GET rules page/API. This runs after authentication has populated current_user.
get_anchor='''        if path=="/api/chat/status":\n'''
get_insert='''        if path=="/admin/rules":\n            if self.current_user.get("role")!="owner": return self.sendb(403,'{"error":"owner_required"}')\n            return self.sendb(200,RULES_HTML,"text/html; charset=utf-8")\n        if path=="/api/admin/rules":\n            if self.current_user.get("role")!="owner": return self.sendb(403,'{"error":"owner_required"}')\n            return self.sendb(200,json.dumps({"ok":True,"rules":load_client_rules(self.headers),"coreLocked":CORE_POLICY_LOCKS},ensure_ascii=False))\n        if path=="/api/chat/status":\n'''
if get_anchor not in s:
    raise SystemExit('rules GET anchor not found')
if 'path=="/admin/rules"' not in s:
    s=s.replace(get_anchor,get_insert,1)

# POST saves/reset. Server sanitization prevents hidden browser switches from
# changing fixed backend protections.
post_anchor='''        if path=="/api/chat/start":\n'''
post_insert='''        if path in ("/api/admin/rules","/api/admin/rules/reset"):\n            if self.current_user.get("role")!="owner": return self.sendb(403,'{"error":"owner_required"}')\n            try:\n                n=int(self.headers.get("Content-Length","0"))\n                msg=json.loads(self.rfile.read(n) or b"{}") if n else {}\n                requested=DEFAULT_CLIENT_RULES if path.endswith("/reset") else (msg.get("rules") or {})\n                ok,rules,detail=save_client_rules(self.headers,requested)\n                if not ok:\n                    return self.sendb(502,json.dumps({"error":"Não foi possível salvar as regras no armazenamento central.","detail":detail.get("error") if isinstance(detail,dict) else "storage_unavailable"},ensure_ascii=False))\n                return self.sendb(200,json.dumps({"ok":True,"rules":rules,"coreLocked":CORE_POLICY_LOCKS},ensure_ascii=False))\n            except Exception as exc:\n                print(f"[hermes-simple] client-rules save error type={type(exc).__name__}",flush=True)\n                return self.sendb(400,json.dumps({"error":"Não foi possível salvar as regras."},ensure_ascii=False))\n        if path=="/api/chat/start":\n'''
if post_anchor not in s:
    raise SystemExit('rules POST anchor not found')
if 'path in ("/api/admin/rules","/api/admin/rules/reset")' not in s:
    s=s.replace(post_anchor,post_insert,1)

# Apply saved preferences to text and multimodal owner requests.
s=s.replace('owner_mode + text','owner_mode + client_rules_instruction(self.headers) + text')
s=s.replace('owner_mode + paid_text','owner_mode + client_rules_instruction(self.headers) + paid_text')

# Direct image/edit routes bypass the general chat payload. Preserve each
# block's indentation while applying the same account preference layer.
s=s.replace(
    '                    effective_image_prompt=enrich_character_prompt(effective_image_prompt,self.headers)\n',
    '                    effective_image_prompt=enrich_character_prompt(effective_image_prompt,self.headers)\n                    effective_image_prompt=client_rules_instruction(self.headers)+effective_image_prompt\n'
)
s=s.replace(
    '                        effective_image_prompt=enrich_character_prompt(effective_image_prompt,self.headers)\n',
    '                        effective_image_prompt=enrich_character_prompt(effective_image_prompt,self.headers)\n                        effective_image_prompt=client_rules_instruction(self.headers)+effective_image_prompt\n'
)
s=s.replace(
    '                paid_text=enrich_character_prompt(paid_text,self.headers)\n',
    '                paid_text=enrich_character_prompt(paid_text,self.headers)\n                paid_text=client_rules_instruction(self.headers)+paid_text\n'
)

p.write_text(s)
print('owner admin rules panel patch applied')
