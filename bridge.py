import os, json, urllib.request, urllib.error, hmac, base64, uuid, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM=os.getenv("HERMES_UPSTREAM","http://127.0.0.1:8642").rstrip("/")
PORT=int(os.getenv("PORT",os.getenv("BRIDGE_PORT","9120")))
HERMES_KEY=os.getenv("API_SERVER_KEY","")
BRIDGE_KEY=os.getenv("HERMES_BRIDGE_KEY","")
SIMPLE_BRIDGE_KEY=os.getenv("HERMES_SIMPLE_BRIDGE_KEY","")
OPENAI_KEY=os.getenv("OPENAI_API_KEY","")
OPENAI_BASE=os.getenv("OPENAI_BASE_URL","https://api.openai.com").rstrip("/")
DIRECT_OPENAI_TEXT=os.getenv("HERMES_DIRECT_OPENAI_TEXT","1").strip().lower() not in ("0","false","no","off")
IMAGE_STORE={}
IMAGE_LOCK=threading.Lock()
IMAGE_TTL=60*60
GET_PATHS={"/health/detailed","/v1/models","/v1/skills","/v1/toolsets"}
POST_PATHS={"/v1/chat/completions","/v1/responses","/v1/runs"}


def generate_image(prompt, model="gpt-image-2", size="1024x1024"):
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")

    candidates=[]
    for name in (model, "gpt-image-2.5-flare", "gpt-image-2.5-sunburst"):
        if name and name not in candidates:
            candidates.append(name)

    last_http_error=None
    for candidate in candidates:
        print(f"[image] generation start model={candidate} size={size}",flush=True)
        payload=json.dumps({"model":candidate,"prompt":prompt,"size":size}).encode()
        req=urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=payload,
            method="POST",
            headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json","Accept":"application/json"}
        )
        try:
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
            print(f"[image] generation success model={candidate}",flush=True)
            return iid, candidate
        except urllib.error.HTTPError as exc:
            last_http_error=exc
            print(f"[image] generation http={exc.code} model={candidate}",flush=True)
            if exc.code==429:
                continue
            raise

    if last_http_error:
        raise last_http_error
    raise RuntimeError("image generation unavailable")

def rewrite_model(body, model):
    try:
        payload=json.loads(body or b"{}")
        payload["model"]=model
        return json.dumps(payload,separators=(",",":")).encode()
    except Exception:
        return body

def routed_models(body):
    try:
        requested=(json.loads(body or b"{}").get("model") or "").strip()
    except Exception:
        requested=""
    # Keep the local Hermes UI/config compatible while routing legacy Sol
    # requests to the current general-purpose Sol model.
    if requested in ("gpt-5.6-sol","gpt-6.1-sol"):
        return [("gpt-6-sol",rewrite_model(body,"gpt-6-sol")),("gpt-6-luna",rewrite_model(body,"gpt-6-luna"))]
    if requested=="gpt-6-sol":
        return [("gpt-6-sol",body),("gpt-6-luna",rewrite_model(body,"gpt-6-luna"))]
    if requested=="gpt-6-luna":
        return [("gpt-6-luna",body)]
    return [(requested or "as-requested",body)]

def direct_openai(path, body, timeout=240):
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    req=urllib.request.Request(
        OPENAI_BASE+path,
        data=body,
        method="POST",
        headers={
            "Authorization":"Bearer "+OPENAI_KEY,
            "Content-Type":"application/json",
            "Accept":"application/json",
        },
    )
    with urllib.request.urlopen(req,timeout=timeout) as res:
        return res.status, res.read(), res.headers.get("Content-Type","application/json")

def hermes_chat(prompt):
    payload=json.dumps({"model":"gpt-5.6-sol","messages":[{"role":"user","content":prompt}],"stream":False}).encode()
    if DIRECT_OPENAI_TEXT and OPENAI_KEY:
        status, raw, _ = direct_openai("/v1/chat/completions", payload, timeout=180)
        data=json.loads(raw)
    else:
        req=urllib.request.Request(UPSTREAM+"/v1/chat/completions",data=payload,method="POST",headers={"Authorization":"Bearer "+HERMES_KEY,"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=180) as res:
            data=json.load(res)
    return data["choices"][0]["message"]["content"]

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,fmt,*args): print("[hermes-bridge] "+(fmt%args),flush=True)
    def reply(self,status,body,ctype="application/json"):
        if isinstance(body,str): body=body.encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # If the client disconnected, do not attempt another 502 reply.
            self.close_connection = True
            print("[hermes-bridge] client disconnected before response delivery", flush=True)
    def direct_openai_stream(self,path,body,timeout=300):
        req=urllib.request.Request(
            OPENAI_BASE+path,
            data=body,
            method="POST",
            headers={
                "Authorization":"Bearer "+OPENAI_KEY,
                "Content-Type":"application/json",
                "Accept":"text/event-stream",
            },
        )
        started=time.time()
        with urllib.request.urlopen(req,timeout=timeout) as res:
            ctype=res.headers.get("Content-Type","text/event-stream")
            self.send_response(res.status)
            self.send_header("Content-Type",ctype)
            self.send_header("Cache-Control","no-cache")
            self.send_header("Connection","close")
            self.end_headers()
            self.close_connection=True
            first=True
            try:
                for chunk in res:
                    if not chunk:
                        continue
                    if first:
                        print(f"[text] direct-openai-stream path={path} ttfb={time.time()-started:.2f}s",flush=True)
                        first=False
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError):
                print("[text] streaming client disconnected",flush=True)
            print(f"[text] direct-openai-stream path={path} duration={time.time()-started:.2f}s",flush=True)

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
        try:
            if self.command=="POST" and path in ("/v1/chat/completions","/v1/responses") and DIRECT_OPENAI_TEXT and OPENAI_KEY:
                stream_requested=False
                try:
                    stream_requested=bool(json.loads(body or b"{}").get("stream"))
                except Exception:
                    stream_requested=False
                candidates=routed_models(body or b"{}")
                last_error=None
                for idx,(candidate,candidate_body) in enumerate(candidates):
                    try:
                        if idx:
                            print(f"[text] fast-fallback model={candidate} path={path}",flush=True)
                        if stream_requested:
                            return self.direct_openai_stream(path,candidate_body,timeout=300)
                        started=time.time()
                        status, raw, ctype = direct_openai(path,candidate_body,timeout=300)
                        print(f"[text] direct-openai path={path} model={candidate} status={status} duration={time.time()-started:.2f}s",flush=True)
                        return self.reply(status,raw,ctype)
                    except urllib.error.HTTPError as exc:
                        last_error=exc
                        raw=exc.read(8192)
                        detail=raw.decode("utf-8","ignore").replace("\n"," ")[:280]
                        print(f"[text] direct-openai-http model={candidate} status={exc.code} detail={detail}",flush=True)
                        if exc.code in (400,401,403,404,429) and idx+1<len(candidates):
                            continue
                        return self.reply(exc.code,raw or json.dumps({"error":"direct_openai_http"}))
                if last_error:
                    return self.reply(last_error.code,b'{"error":"direct_openai_failed"}')
            req=urllib.request.Request(UPSTREAM+self.path,data=body,method=self.command,headers={"Authorization":"Bearer "+HERMES_KEY,"Content-Type":"application/json"})
            with urllib.request.urlopen(req,timeout=900) as res:
                return self.reply(res.status,res.read(),res.headers.get("Content-Type","application/json"))
        except urllib.error.HTTPError as exc:
            raw=exc.read()
            print(f"[text] upstream-http path={path} status={exc.code}",flush=True)
            return self.reply(exc.code,raw)
        except Exception as exc:
            print(f"[text] upstream-error path={path} type={type(exc).__name__}",flush=True)
            return self.reply(502,json.dumps({"error":"upstream_unavailable","type":type(exc).__name__}))
    do_GET=proxy
    do_POST=proxy

if __name__=="__main__":
    if not HERMES_KEY or not (BRIDGE_KEY or SIMPLE_BRIDGE_KEY): raise SystemExit("bridge credentials missing")
    print("[hermes-bridge] MCP endpoint enabled at /mcp",flush=True)
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
