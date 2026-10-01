from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

anchor='AUTH_CACHE_TTL = 60\n'
insert='''AUTH_CACHE_TTL = 60
MEDIA_PERSIST_URL = os.getenv("HERMES_MEDIA_PERSIST_URL", "").rstrip("/")
MEDIA_PERSIST_JWT = os.getenv("HERMES_MEDIA_PERSIST_JWT", "")
'''
if anchor not in s:
    raise SystemExit('persistent media config anchor not found')
s=s.replace(anchor,insert,1)

helper='''def _persistent_media_call(action, payload):
    if not MEDIA_PERSIST_URL or not MEDIA_PERSIST_JWT:
        return None, 0
    body=dict(payload or {})
    body["action"]=action
    req=urllib.request.Request(
        MEDIA_PERSIST_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization":"Bearer "+MEDIA_PERSIST_JWT,
            "apikey":MEDIA_PERSIST_JWT,
            "Content-Type":"application/json",
            "Accept":"application/json",
        },
    )
    try:
        with urllib.request.urlopen(req,timeout=45) as res:
            return json.load(res),res.status
    except urllib.error.HTTPError as e:
        try: data=json.loads(e.read(4096).decode("utf-8","ignore") or "{}")
        except Exception: data={"error":"media_http_%s"%e.code}
        return data,e.code
    except Exception as exc:
        print(f"[hermes-simple] persistent-media error={type(exc).__name__}",flush=True)
        return None,0

'''
anchor2='def store_media(raw, mime):\n'
if anchor2 not in s:
    raise SystemExit('store_media anchor not found')
s=s.replace(anchor2,helper+anchor2,1)

old='''def store_media(raw, mime):
    mid=uuid.uuid4().hex
    now=time.time()
    with MEDIA_LOCK:
        for key,val in list(MEDIA_STORE.items()):
            if now-val["created"]>MEDIA_TTL:
                MEDIA_STORE.pop(key,None)
        MEDIA_STORE[mid]={"bytes":raw,"mime":mime,"created":now}
    return mid
'''
new='''def store_media(raw, mime):
    mid=uuid.uuid4().hex
    now=time.time()
    with MEDIA_LOCK:
        for key,val in list(MEDIA_STORE.items()):
            if now-val["created"]>MEDIA_TTL:
                MEDIA_STORE.pop(key,None)
        MEDIA_STORE[mid]={"bytes":raw,"mime":mime,"created":now}
    try:
        data,status=_persistent_media_call("store",{"id":mid,"mime":mime,"data":base64.b64encode(raw).decode("ascii")})
        print(f"[hermes-simple] persistent-media store status={status} id={mid[:8]}",flush=True)
    except Exception as exc:
        print(f"[hermes-simple] persistent-media store skipped={type(exc).__name__}",flush=True)
    return mid
'''
if old not in s:
    raise SystemExit('store_media function not found')
s=s.replace(old,new,1)

old_get='''        if path.startswith("/api/media/"):
            mid=path.rsplit("/",1)[-1]
            with MEDIA_LOCK:
                item=MEDIA_STORE.get(mid)
            if not item:
                return self.sendb(404,'{"error":"media_not_found"}')
            return self.sendb(200,item["bytes"],item["mime"])
'''
new_get='''        if path.startswith("/api/media/"):
            mid=path.rsplit("/",1)[-1]
            with MEDIA_LOCK:
                item=MEDIA_STORE.get(mid)
            if not item:
                data,status=_persistent_media_call("get",{"id":mid})
                if status==200 and data and data.get("data"):
                    try:
                        raw=base64.b64decode(data["data"])
                        mime=str(data.get("mime") or "application/octet-stream")
                        item={"bytes":raw,"mime":mime,"created":time.time()}
                        with MEDIA_LOCK: MEDIA_STORE[mid]=item
                        print(f"[hermes-simple] persistent-media restored id={mid[:8]} bytes={len(raw)}",flush=True)
                    except Exception:
                        item=None
            if not item:
                return self.sendb(404,'{"error":"media_not_found"}')
            return self.sendb(200,item["bytes"],item["mime"])
'''
if old_get not in s:
    raise SystemExit('media GET anchor not found')
s=s.replace(old_get,new_get,1)

# Ensure inline remote images use the persistent media path too.
old_inline='''            mid=uuid.uuid4().hex
            now=time.time()
            with MEDIA_LOCK:
                for key,val in list(MEDIA_STORE.items()):
                    if now-val["created"]>MEDIA_TTL:
                        MEDIA_STORE.pop(key,None)
                MEDIA_STORE[mid]={"bytes":raw,"mime":ctype or "image/png","created":now}
            print(f"[hermes-simple] cached inline image bytes={len(raw)}",flush=True)
            return mid
'''
new_inline='''            mid=store_media(raw,ctype or "image/png")
            print(f"[hermes-simple] cached inline image bytes={len(raw)}",flush=True)
            return mid
'''
if old_inline in s:
    s=s.replace(old_inline,new_inline,1)

p.write_text(s)
