import os, json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
UPSTREAM=os.getenv("HERMES_UPSTREAM","http://127.0.0.1:8642").rstrip("/")
PORT=int(os.getenv("PORT",os.getenv("BRIDGE_PORT","9120")))
HERMES_KEY=os.getenv("API_SERVER_KEY","")
BRIDGE_KEY=os.getenv("HERMES_BRIDGE_KEY","")
GET_PATHS={"/health/detailed","/v1/models","/v1/skills","/v1/toolsets"}
POST_PATHS={"/v1/chat/completions","/v1/responses","/v1/runs"}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): print("[hermes-bridge] "+(fmt%args),flush=True)
    def reply(self,status,body,ctype="application/json"):
        self.send_response(status); self.send_header("Content-Type",ctype); self.end_headers(); self.wfile.write(body)
    def authorized(self):
        return bool(BRIDGE_KEY) and self.headers.get("Authorization","")=="Bearer "+BRIDGE_KEY
    def proxy(self):
        path=self.path.split("?",1)[0]
        if path=="/health": return self.reply(200,b'{"status":"ok"}')
        if not self.authorized(): return self.reply(401,b'{"error":"unauthorized"}')
        if path not in (GET_PATHS if self.command=="GET" else POST_PATHS): return self.reply(404,b'{"error":"not_found"}')
        body=None
        if self.command=="POST": body=self.rfile.read(int(self.headers.get("Content-Length","0")))
        req=urllib.request.Request(UPSTREAM+self.path,data=body,method=self.command,headers={"Authorization":"Bearer "+HERMES_KEY,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=900) as res: self.reply(res.status,res.read(),res.headers.get("Content-Type","application/json"))
        except urllib.error.HTTPError as exc: self.reply(exc.code,exc.read())
        except Exception as exc: self.reply(502,json.dumps({"error":"upstream_unavailable","type":type(exc).__name__}).encode())
    do_GET=proxy
    do_POST=proxy
if __name__=="__main__":
    if not HERMES_KEY or not BRIDGE_KEY: raise SystemExit("bridge credentials missing")
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
