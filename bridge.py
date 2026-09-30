import os, json, urllib.request, urllib.error, hmac, base64, uuid, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM=os.getenv("HERMES_UPSTREAM","http://127.0.0.1:8642").rstrip("/")
PORT=int(os.getenv("PORT",os.getenv("BRIDGE_PORT","9120")))
HERMES_KEY=os.getenv("API_SERVER_KEY","")
BRIDGE_KEY=os.getenv("HERMES_BRIDGE_KEY","")
SIMPLE_BRIDGE_KEY=os.getenv("HERMES_SIMPLE_BRIDGE_KEY","")
OPENAI_KEY=os.getenv("OPENAI_API_KEY","")
IMAGE_STORE={}
IMAGE_LOCK=threading.Lock()
IMAGE_TTL=60*60
GET_PATHS={"/health/detailed","/v1/models","/v1/skills","/v1/toolsets"}
POST_PATHS={"/v1/chat/completions","/v1/responses","/v1/runs"}


def generate_image(prompt, model="gpt-image-2", size="1024x1024"):
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    print(f"[image] generation start model={model} size={size}",flush=True)\n    payload=json.dumps({"model":model,"prompt":prompt,"size":size}).encode()
    req=urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        method="POST",
        headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json","Accept":"application/json"}
    )
    with urllib.request.urlopen(req,timeout=75) as res:
        data=json.load(res)
    item=(data.get("data") or [{}])[0]
    b64=item.get("b64_json")
    if not b64:
        raise RuntimeError("image response missing b64_json")
    raw=base64.b64decode(b64)
    iid=uuid.uuid4().hex
    now=time.time()
    with IMAGE_LOCK:
        for key,val in list(IMAGE_STORE.items()):
            if now-val["created"] > IMAGE_TTL:
                IMAGE_STORE.pop(key,None)
        IMAGE_STORE[iid]={"bytes":raw,"mime":"image/png","created":now}
    return iid, model

def hermes_chat(prompt):
    payload=json.dumps({"model":"gpt-5.6-sol","messages":[{"role":"user","content":prompt}],"stream":False}).encode()
    req=urllib.request.Request(UPSTREAM+"/v1/chat/completions",data=payload,method="POST",headers={"Authorization":"Bearer "+HERMES_KEY,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=75) as res:
        data=json.load(res)
    return data["choices"][0]["message"]["content"]

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,fmt,*args): print("[hermes-bridge] "+(fmt%args),flush=True)
    def reply(self,status,body,ctype="application/json"):
        if isinstance(body,str): body=body.encode()
        self.send_response(status); self.send_header("Content-Type",ctype); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def authorized(self):
        presented=self.headers.get("Authorization","")
        allowed=[]
        if BRIDGE_KEY: allowed.append("Bearer "+BRIDGE_KEY)
        if SIMPLE_BRIDGE_KEY: allowed.append("Bearer "+SIMPLE_BRIDGE_KEY)
        return any(hmac.compare_digest(presented, expected) for expected in allowed)
    def mcp(self):
        if not self.authorized(): return self.reply(401,b'{"error":"unauthorized"}')
        try:
            body=self.rfile.read(int(self.headers.get("Content-Length","0")))
            msg=json.loads(body or b"{}")
            mid=msg.get("id")
            method=msg.get("method")
            if method=="initialize":
                result={"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"hermes-chatgpt-bridge","version":"1.0.0"}}
            elif method=="notifications/initialized":
                return self.reply(202,b"")
            elif method=="tools/list":
                result={"tools":[{"name":"hermes","description":"Send a task to the user's private Hermes Agent and return its response.","inputSchema":{"type":"object","properties":{"prompt":{"type":"string","description":"Task or message for Hermes"}},"required":["prompt"]}}]}
            elif method=="tools/call":
                p=msg.get("params",{})
                if p.get("name")!="hermes": raise ValueError("unknown tool")
                answer=hermes_chat(p.get("arguments",{}).get("prompt",""))
                result={"content":[{"type":"text","text":answer}],"isError":False}
            elif method=="ping":
                result={}
            else:
                return self.reply(200,json.dumps({"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":"Method not found"}}))
            return self.reply(200,json.dumps({"jsonrpc":"2.0","id":mid,"result":result}))
        except urllib.error.HTTPError as exc:
            return self.reply(200,json.dumps({"jsonrpc":"2.0","id":msg.get("id") if 'msg' in locals() else None,"error":{"code":-32000,"message":"Hermes upstream HTTP "+str(exc.code)}}))
        except Exception as exc:
            return self.reply(200,json.dumps({"jsonrpc":"2.0","id":msg.get("id") if 'msg' in locals() else None,"error":{"code":-32000,"message":type(exc).__name__}}))
    def proxy(self):
        path=self.path.split("?",1)[0]
        if path=="/health": return self.reply(200,b'{"status":"ok","mcp":true}')
        if path.startswith("/v1/images/") and self.command=="GET":
            if not self.authorized(): return self.reply(401,b'{"error":"unauthorized"}')
            iid=path.rsplit("/",1)[-1]
            with IMAGE_LOCK:
                item=IMAGE_STORE.get(iid)
            if not item: return self.reply(404,b'{"error":"image_not_found"}')
            return self.reply(200,item["bytes"],item["mime"])
        if path=="/v1/images/generations" and self.command=="POST":
            if not self.authorized(): return self.reply(401,b'{"error":"unauthorized"}')
            try:
                body=self.rfile.read(int(self.headers.get("Content-Length","0")))
                msg=json.loads(body or b"{}")
                prompt=(msg.get("prompt") or "").strip()
                if not prompt: return self.reply(400,b'{"error":"prompt_required"}')
                model=(msg.get("model") or "gpt-image-2").strip()
                size=(msg.get("size") or "1024x1024").strip()
                iid,used_model=generate_image(prompt,model,size)
                return self.reply(200,json.dumps({"id":iid,"url":"/v1/images/"+iid,"model":used_model}).encode())
            except urllib.error.HTTPError as exc:
                raw=exc.read(8192)
                return self.reply(exc.code,raw or json.dumps({"error":"image_upstream_http"}))
            except Exception as exc:
                return self.reply(502,json.dumps({"error":"image_generation_failed","type":type(exc).__name__}).encode())
        if path=="/mcp" and self.command=="POST": return self.mcp()
        if not self.authorized(): return self.reply(401,b'{"error":"unauthorized"}')
        if path not in (GET_PATHS if self.command=="GET" else POST_PATHS): return self.reply(404,b'{"error":"not_found"}')
        body=None
        if self.command=="POST": body=self.rfile.read(int(self.headers.get("Content-Length","0")))
        req=urllib.request.Request(UPSTREAM+self.path,data=body,method=self.command,headers={"Authorization":"Bearer "+HERMES_KEY,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=900) as res: self.reply(res.status,res.read(),res.headers.get("Content-Type","application/json"))
        except urllib.error.HTTPError as exc: self.reply(exc.code,exc.read())
        except Exception as exc: self.reply(502,json.dumps({"error":"upstream_unavailable","type":type(exc).__name__}))
    do_GET=proxy
    do_POST=proxy

if __name__=="__main__":
    if not HERMES_KEY or not (BRIDGE_KEY or SIMPLE_BRIDGE_KEY): raise SystemExit("bridge credentials missing")
    print("[hermes-bridge] MCP endpoint enabled at /mcp",flush=True)
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
