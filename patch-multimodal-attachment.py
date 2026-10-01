from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

old = '''            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="paid":
'''
new = '''            payload_input=text
            if attachment_id:
                with MEDIA_LOCK:
                    attached=MEDIA_STORE.get(attachment_id)
                if not attached or not str(attached.get("mime","")).startswith("image/"):
                    return self.sendb(400,json.dumps({"error":"A imagem anexada não está mais disponível. Anexe novamente."},ensure_ascii=False))
                encoded=base64.b64encode(attached["bytes"]).decode("ascii")
                data_url="data:"+attached["mime"]+";base64,"+encoded
                payload_input=[{
                    "role":"user",
                    "content":[
                        {"type":"input_text","text":text},
                        {"type":"input_image","image_url":data_url}
                    ]
                }]
                print(f"[hermes-simple] multimodal attachment bytes={len(attached['bytes'])} route={route}",flush=True)
            payload={"input":payload_input,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="paid":
'''

if old not in s:
    raise SystemExit('multimodal payload anchor not found')
s=s.replace(old,new)
p.write_text(s)
