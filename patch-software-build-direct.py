from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Detect long-running software construction tasks. These should bypass the
# public bridge because Railway's HTTP edge can terminate a still-running
# request around 300s, while Hermes keeps the session locked in the background.
helper_anchor='def call_upstream(payload):\n'
helper='''def is_software_build_request(text):\n    t=(text or "").lower()\n    software=(\n        "sistema", "software", "aplicativo", "web app", "site", "website",\n        "portal", "plataforma", "frontend", "backend", "api", "banco de dados",\n        "database", "supabase", "postgres", "crud", "deploy", "vercel",\n        "github", "repositório", "repositorio", "pwa", "saas"\n    )\n    action=(\n        "crie", "criar", "desenvolva", "desenvolver", "construa", "construir",\n        "implemente", "implementar", "monte", "montar", "execute", "executar"\n    )\n    return any(x in t for x in software) and any(x in t for x in action)\n\n\n'''
if helper_anchor in s and 'def is_software_build_request(' not in s:
    s=s.replace(helper_anchor,helper+helper_anchor,1)

old='''def call_upstream(payload):\n    \"\"\"Use the isolated bridge as the single stable chat path.\"\"\"\n    if not BRIDGE_KEY:\n        raise RuntimeError(\"Bridge Hermes não configurado\")\n    body = json.dumps(payload).encode(\"utf-8\")\n    req = urllib.request.Request(BRIDGE_UPSTREAM + \"/v1/responses\", data=body, method=\"POST\", headers={\n        \"Authorization\": \"Bearer \" + BRIDGE_KEY,\n        \"Content-Type\": \"application/json\",\n        \"Accept\": \"application/json\",\n    })\n    try:\n        with urllib.request.urlopen(req, timeout=900) as res:\n            return json.load(res), \"bridge\"\n    except urllib.error.HTTPError as e:\n        raw = e.read(8192)\n        raise RuntimeError(f\"bridge HTTP {e.code}: \" + raw.decode(\"utf-8\",\"ignore\")[:400]) from e\n'''
new='''def call_upstream(payload):\n    \"\"\"Use direct private networking for long software builds; bridge otherwise.\"\"\"\n    direct=bool(payload.pop(\"_software_direct\",False))\n    body=json.dumps(payload).encode(\"utf-8\")\n    if direct:\n        if not DIRECT_KEY:\n            raise RuntimeError(\"Hermes direct API não configurada\")\n        req=urllib.request.Request(DIRECT_UPSTREAM+\"/v1/responses\",data=body,method=\"POST\",headers={\n            \"Authorization\":\"Bearer \"+DIRECT_KEY,\n            \"Content-Type\":\"application/json\",\n            \"Accept\":\"application/json\",\n        })\n        try:\n            with urllib.request.urlopen(req,timeout=900) as res:\n                return json.load(res),\"direct-private\"\n        except urllib.error.HTTPError as e:\n            raw=e.read(8192)\n            raise RuntimeError(f\"direct HTTP {e.code}: \"+raw.decode(\"utf-8\",\"ignore\")[:400]) from e\n    if not BRIDGE_KEY:\n        raise RuntimeError(\"Bridge Hermes não configurado\")\n    req=urllib.request.Request(BRIDGE_UPSTREAM+\"/v1/responses\",data=body,method=\"POST\",headers={\n        \"Authorization\":\"Bearer \"+BRIDGE_KEY,\n        \"Content-Type\":\"application/json\",\n        \"Accept\":\"application/json\",\n    })\n    try:\n        with urllib.request.urlopen(req,timeout=900) as res:\n            return json.load(res),\"bridge\"\n    except urllib.error.HTTPError as e:\n        raw=e.read(8192)\n        raise RuntimeError(f\"bridge HTTP {e.code}: \"+raw.decode(\"utf-8\",\"ignore\")[:400]) from e\n'''
if old not in s:
    raise SystemExit('call_upstream anchor not found')
s=s.replace(old,new,1)

# The exact route block is changed by later patches (paid/Antigravity), so only
# anchor on the stable payload assignment line and inject immediately after it.
payload_line='            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}\n'
inject='''            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}\n            if is_software_build_request(text):\n                # Isolate each build attempt so a cancelled/expired previous turn\n                # cannot hold the conversation session lock.\n                payload["conversation"]=(conv or "web")+"-build-"+uuid.uuid4().hex[:10]\n                payload["_software_direct"]=True\n                print("[hermes-simple] software-build routing=direct-private isolated_session=true",flush=True)\n'''
if 'software-build routing=direct-private isolated_session=true' not in s:
    if payload_line not in s:
        raise SystemExit('payload assignment anchor not found')
    s=s.replace(payload_line,inject,1)

p.write_text(s)
print('software build direct-routing patch applied')
