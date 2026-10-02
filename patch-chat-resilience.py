from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Keep long Hermes work off the browser request. Mobile Safari can close an
# otherwise healthy request after ~25s and surface only "Load failed". Jobs run
# server-side and the browser polls short status requests instead.
anchor='MEDIA_TTL=60*60\n'
insert='''MEDIA_TTL=60*60\nCHAT_JOBS={}\nCHAT_JOBS_LOCK=threading.Lock()\nCHAT_JOB_TTL=60*60\n'''
if anchor in s and 'CHAT_JOBS={}' not in s:
    s=s.replace(anchor,insert,1)

# Local owner fallback sessions are valid inside hermes-web, but are not rows in
# hermes_sessions. Tell the private profile service which authenticated owner is
# requesting the profile; the edge service still requires the server secret.
old_profile="""    body['action']=action\n    body['token']=token\n    req=urllib.request.Request(PROFILE_EDGE_URL,data=json.dumps(body).encode('utf-8'),method='POST',headers={\n"""
new_profile="""    body['action']=action\n    body['token']=token\n    if token.startswith('local.'):\n        body['username']=USER\n    req=urllib.request.Request(PROFILE_EDGE_URL,data=json.dumps(body).encode('utf-8'),method='POST',headers={\n"""
if old_profile in s:
    s=s.replace(old_profile,new_profile,1)

helper_anchor='class Handler(BaseHTTPRequestHandler):\n'
helpers=r'''def _cleanup_chat_jobs():
    now=time.time()
    with CHAT_JOBS_LOCK:
        for jid,item in list(CHAT_JOBS.items()):
            if now-float(item.get('created') or now)>CHAT_JOB_TTL:
                CHAT_JOBS.pop(jid,None)


def _run_chat_job(jid, cookie, payload):
    try:
        req=urllib.request.Request(
            f'http://127.0.0.1:{PORT}/api/chat',
            data=json.dumps(payload).encode('utf-8'),
            method='POST',
            headers={
                'Content-Type':'application/json',
                'Accept':'application/json',
                'Cookie':cookie or '',
            },
        )
        try:
            with urllib.request.urlopen(req,timeout=900) as res:
                raw=res.read(40*1024*1024)
                status=res.status
        except urllib.error.HTTPError as exc:
            raw=exc.read(1024*1024)
            status=exc.code
        try:
            response=json.loads(raw.decode('utf-8','ignore') or '{}')
        except Exception:
            response={'error':'O Hermes concluiu a tarefa, mas a resposta não pôde ser interpretada.'}
            status=502
        with CHAT_JOBS_LOCK:
            item=CHAT_JOBS.get(jid)
            if item is not None:
                item.update({'status':'done','httpStatus':status,'response':response,'finished':time.time()})
    except Exception as exc:
        print(f'[hermes-simple] async chat job failed type={type(exc).__name__}',flush=True)
        with CHAT_JOBS_LOCK:
            item=CHAT_JOBS.get(jid)
            if item is not None:
                item.update({
                    'status':'done','httpStatus':502,
                    'response':{'error':'Falha temporária de conexão com o Hermes. Tente novamente.','type':type(exc).__name__},
                    'finished':time.time(),
                })


'''
if helper_anchor in s and 'def _run_chat_job(' not in s:
    s=s.replace(helper_anchor,helpers+helper_anchor,1)

# Short polling endpoint. Each job is scoped to the authenticated username.
get_anchor='''        if path=="/api/session":\n'''
get_insert='''        if path=="/api/chat/status":\n            jid=(self.path.split("id=",1)[1].split("&",1)[0] if "id=" in self.path else "").strip()\n            with CHAT_JOBS_LOCK:\n                item=CHAT_JOBS.get(jid)\n            if not item:\n                return self.sendb(404,json.dumps({"error":"job_not_found"},ensure_ascii=False))\n            if item.get("owner") != str(self.current_user.get("username") or ""):\n                return self.sendb(403,json.dumps({"error":"forbidden"},ensure_ascii=False))\n            if item.get("status") != "done":\n                return self.sendb(200,json.dumps({"ok":True,"status":"pending","jobId":jid},ensure_ascii=False))\n            return self.sendb(200,json.dumps({"ok":True,"status":"done","jobId":jid,"httpStatus":item.get("httpStatus",200),"response":item.get("response") or {}},ensure_ascii=False))\n        if path=="/api/session":\n'''
if get_anchor in s and 'path=="/api/chat/status"' not in s:
    s=s.replace(get_anchor,get_insert,1)

# Start endpoint returns immediately; the original /api/chat remains the worker
# execution endpoint, minimizing regression risk in the established routing.
post_anchor='''        if path in ("/api/admin/create","/api/admin/toggle","/api/admin/delete"):\n'''
post_insert='''        if path=="/api/chat/start":\n            try:\n                n=int(self.headers.get("Content-Length","0"))\n                if n>18*1024*1024:\n                    return self.sendb(413,json.dumps({"error":"Arquivo muito grande"},ensure_ascii=False))\n                payload=json.loads(self.rfile.read(n) or b"{}")\n                jid=uuid.uuid4().hex\n                _cleanup_chat_jobs()\n                with CHAT_JOBS_LOCK:\n                    CHAT_JOBS[jid]={"status":"pending","created":time.time(),"owner":str(self.current_user.get("username") or "")}\n                cookie=self.headers.get("Cookie","") or ""\n                threading.Thread(target=_run_chat_job,args=(jid,cookie,payload),daemon=True).start()\n                return self.sendb(202,json.dumps({"ok":True,"jobId":jid,"status":"pending"},ensure_ascii=False))\n            except Exception as exc:\n                print(f"[hermes-simple] chat start error type={type(exc).__name__}",flush=True)\n                return self.sendb(400,json.dumps({"error":"Não foi possível iniciar a tarefa."},ensure_ascii=False))\n        if path in ("/api/admin/create","/api/admin/toggle","/api/admin/delete"):\n'''
if post_anchor in s and 'path=="/api/chat/start"' not in s:
    s=s.replace(post_anchor,post_insert,1)

# Replace the browser's single long request with start + short polling. A job
# continues on the server even if an iPhone briefly suspends Safari.
old_js="""  const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation:'web-'+c.id,input:text,route:$('#model').value,attachmentId:pendingAttachment?pendingAttachment.id:null})});\n  const data=await res.json().catch(()=>({}));\n  holder.remove();\n  if(!res.ok)throw new Error(data.error||'Falha ao conversar com o Hermes');\n  c.messages.push({role:'assistant',text:data.text||'(sem resposta)',routeMeta:data.routeMeta||null,imageUrl:data.imageUrl||null,videoUrl:data.videoUrl||null});\n"""
new_js="""  const requestBody={conversation:'web-'+c.id,input:text,route:$('#model').value,attachmentId:pendingAttachment?pendingAttachment.id:null};\n  const startRes=await fetch('/api/chat/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(requestBody),cache:'no-store'});\n  const startData=await startRes.json().catch(()=>({}));\n  if(!startRes.ok||!startData.jobId)throw new Error(startData.error||'Não foi possível iniciar a tarefa no Hermes');\n  const jobId=startData.jobId;\n  let data=null, finalStatus=200;\n  for(let attempt=0;attempt<450;attempt++){\n    await new Promise(r=>setTimeout(r,2000));\n    try{\n      const poll=await fetch('/api/chat/status?id='+encodeURIComponent(jobId),{cache:'no-store'});\n      const pj=await poll.json().catch(()=>({}));\n      if(!poll.ok)throw new Error(pj.error||'Falha ao consultar a tarefa');\n      if(pj.status==='done'){data=pj.response||{};finalStatus=pj.httpStatus||200;break}\n      statusEl.textContent='Hermes trabalhando… '+Math.max(2,(attempt+1)*2)+'s';\n    }catch(netErr){\n      statusEl.textContent='Reconectando ao Hermes…';\n    }\n  }\n  holder.remove();\n  if(!data)throw new Error('A tarefa continua demorando. Tente abrir a conversa novamente em alguns instantes.');\n  if(finalStatus>=400)throw new Error(data.error||'Falha ao conversar com o Hermes');\n  c.messages.push({role:'assistant',text:data.text||'(sem resposta)',routeMeta:data.routeMeta||null,imageUrl:data.imageUrl||null,videoUrl:data.videoUrl||null});\n"""
if old_js in s:
    s=s.replace(old_js,new_js,1)
else:
    raise SystemExit('async frontend chat anchor not found')

# Make API quota exhaustion explicit instead of returning an opaque 502.
old_err='''        except Exception as e:\n            print("[hermes-simple] chat error "+type(e).__name__+": "+str(e)[:500],flush=True)\n            return self.sendb(502,json.dumps({"error":"Não consegui falar com o Hermes agora. Tente novamente.","type":type(e).__name__},ensure_ascii=False))\n'''
new_err='''        except Exception as e:\n            detail=str(e)\n            print("[hermes-simple] chat error "+type(e).__name__+": "+detail[:500],flush=True)\n            if "credit_balance_exhausted" in detail or "no credits remaining" in detail.lower() or "insufficient_quota" in detail:\n                message="A rota GPT-5.6 Sol · Pago está sem créditos de API no momento. Adicione créditos na conta da API OpenAI para usar esta rota."\n            else:\n                message="Não consegui falar com o Hermes agora. Tente novamente."\n            return self.sendb(502,json.dumps({"error":message,"type":type(e).__name__},ensure_ascii=False))\n'''
if old_err in s:
    s=s.replace(old_err,new_err,1)

p.write_text(s)
print('chat resilience + async jobs patch applied')
