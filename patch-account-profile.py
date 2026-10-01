from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Server-side account profile service. Uses the same private auth secret and
# session token as Hermes auth, so behavior follows the logged-in account,
# never the browser/device.
anchor='AUTH_CACHE_TTL = 60\n'
insert='''AUTH_CACHE_TTL = 60\nPROFILE_EDGE_URL = os.getenv("HERMES_PROFILE_EDGE_URL", "").rstrip("/")\nPROFILE_CACHE = {}\nPROFILE_CACHE_LOCK = threading.Lock()\nPROFILE_CACHE_TTL = 60\n'''
if anchor in s and 'PROFILE_EDGE_URL =' not in s:
    s=s.replace(anchor,insert,1)

helper_anchor='def session_user(headers):\n'
helper=r'''def _profile_call(action, headers, payload=None):
    if not PROFILE_EDGE_URL or not AUTH_EDGE_SECRET:
        return None
    token=_cookie_token(headers)
    if not token:
        return None
    body=dict(payload or {})
    body['action']=action
    body['token']=token
    req=urllib.request.Request(PROFILE_EDGE_URL,data=json.dumps(body).encode('utf-8'),method='POST',headers={
        'Content-Type':'application/json','Accept':'application/json','X-Hermes-Auth':AUTH_EDGE_SECRET,
    })
    try:
        with urllib.request.urlopen(req,timeout=15) as res:
            return json.load(res)
    except Exception as exc:
        print(f'[hermes-simple] profile service unavailable type={type(exc).__name__}',flush=True)
        return None


def account_profile(headers):
    token=_cookie_token(headers)
    if not token:
        return {'preferences':{'default_route':'auto','settings':{}},'characters':[]}
    now=time.time()
    with PROFILE_CACHE_LOCK:
        cached=PROFILE_CACHE.get(token)
        if cached and cached[0]>now:
            return cached[1]
    data=_profile_call('get_profile',headers) or {'preferences':{'default_route':'auto','settings':{}},'characters':[]}
    with PROFILE_CACHE_LOCK:
        PROFILE_CACHE[token]=(now+PROFILE_CACHE_TTL,data)
    return data


def enrich_character_prompt(text, headers):
    raw=(text or '').strip()
    profile=account_profile(headers)
    chars=profile.get('characters') or []
    low=raw.lower()
    matched=[]
    for ch in chars:
        names=[str(ch.get('name') or '')]+[str(x) for x in (ch.get('aliases') or [])]
        if any(n and n.lower() in low for n in names):
            matched.append(ch)
    if not matched:
        return raw
    notes=[]
    for ch in matched:
        meta=ch.get('metadata') or {}
        desc=str(ch.get('description') or '').strip()
        note=f"PERSONAGEM DA CONTA: {ch.get('name')}."
        if meta.get('fictional'): note+=' É inteiramente fictícia.'
        if meta.get('adult'): note+=f" É claramente adulta ({int(meta.get('min_age') or 25)}+)."
        if desc: note+=' '+desc
        if ch.get('reference_media'):
            note+=' Existem referências visuais persistentes cadastradas; preserve a identidade dessas referências.'
        else:
            note+=' Não invente que existe uma referência visual persistente quando nenhuma estiver cadastrada.'
        notes.append(note)
    return ' '.join(notes)+'\n'+raw


'''
if helper_anchor in s and 'def account_profile(headers):' not in s:
    s=s.replace(helper_anchor,helper+helper_anchor,1)

# Use account character memory after the owner normalization layer.
s=s.replace(
    'effective_image_prompt=normalize_owner_image_prompt(text, getattr(self, "current_user", None))\n                    mid, used_space=generate_zero_cost_image(effective_image_prompt)',
    'effective_image_prompt=normalize_owner_image_prompt(text, getattr(self, "current_user", None))\n                    effective_image_prompt=enrich_character_prompt(effective_image_prompt,self.headers)\n                    mid, used_space=generate_zero_cost_image(effective_image_prompt)'
)
s=s.replace(
    'effective_image_prompt=normalize_owner_image_prompt(text, getattr(self, "current_user", None))\n                        mid, used_space=generate_zero_cost_edit(item["bytes"], item["mime"], effective_image_prompt)',
    'effective_image_prompt=normalize_owner_image_prompt(text, getattr(self, "current_user", None))\n                        effective_image_prompt=enrich_character_prompt(effective_image_prompt,self.headers)\n                        mid, used_space=generate_zero_cost_edit(item["bytes"], item["mime"], effective_image_prompt)'
)

# Read-only profile endpoint for every logged-in browser.
get_anchor='''        if path=="/api/session":\n            return self.sendb(200,json.dumps({"ok":True,"user":self.current_user,"accountMode":"owner" if self.current_user.get("role")=="owner" else "user","defaultRoute":"auto","serverConfig":"cross-device-v1"},ensure_ascii=False))\n'''
get_new='''        if path=="/api/session":\n            prof=account_profile(self.headers)\n            pref=prof.get("preferences") or {}\n            return self.sendb(200,json.dumps({"ok":True,"user":self.current_user,"accountMode":"owner" if self.current_user.get("role")=="owner" else "user","defaultRoute":pref.get("default_route") or "auto","serverConfig":"cross-device-v2","characters":[{"name":c.get("name"),"aliases":c.get("aliases") or [],"metadata":c.get("metadata") or {},"referenceCount":len(c.get("reference_media") or [])} for c in (prof.get("characters") or [])]},ensure_ascii=False))\n        if path=="/api/profile":\n            prof=account_profile(self.headers)\n            return self.sendb(200,json.dumps({"ok":True,"profile":prof},ensure_ascii=False))\n'''
if get_anchor in s:
    s=s.replace(get_anchor,get_new,1)

p.write_text(s)
print('account profile + character memory patch applied')
