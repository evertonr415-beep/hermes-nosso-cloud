import os, json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM=os.getenv("HERMES_UPSTREAM","http://127.0.0.1:8642").rstrip("/")
PORT=int(os.getenv("PORT",os.getenv("BRIDGE_PORT","9120")))
HERMES_KEY=os.getenv("API_SERVER_KEY","")
BRIDGE_KEY=os.getenv("HERMES_BRIDGE_KEY","")
GET_PATHS={"/health/detailed","/v1/models","/v1/skills","/v1/toolsets"}
POST_PATHS={"/v1/chat/completions","/v1/responses","/v1/runs"}

def hermes_chat(prompt):
    payload=json.dumps({"model":"gpt-5.6-sol","messages":[{"role":"user","content":prompt}],"stream":False}).encode()
    req=urllib.request.Request(UPSTREAM+"/v1/chat/completions",data=payload,method="POST",headers={"Authorization":"Bearer "+HERMES_KEY,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=900) as res:
        data=json.load(res)
    return data["choices"][0]["message"]["content"]

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,fmt,*args): print("[hermes-bridge] "+(fmt%args),flush=True)
    def reply(self,status,body,ctype="application/json"):
        if isinstance(body,str): body=body.encode()
        self.send_response(status); self.send_header("Content-Type",ctype); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def authorized(self):
        return bool(BRIDGE_KEY) and self.headers.get("Authorization","")=="Bearer "+BRIDGE_KEY
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
    if not HERMES_KEY or not BRIDGE_KEY: raise SystemExit("bridge credentials missing")
    print("[hermes-bridge] MCP endpoint enabled at /mcp",flush=True)
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
