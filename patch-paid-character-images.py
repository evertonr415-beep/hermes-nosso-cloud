from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Paid image requests must reach the paid Responses API instead of being
# intercepted by the free image route. Free/auto behavior is unchanged.
s=s.replace(
    '            if is_real_person_reference_request(text) and not attachment_id:\n',
    '            if route != "paid" and is_real_person_reference_request(text) and not attachment_id:\n',
    1,
)
s=s.replace(
    '            if is_image_generation_request(text):\n                try:\n',
    '            if route != "paid" and is_image_generation_request(text):\n                try:\n',
    1,
)

# Extract the official Responses API image_generation output.
anchor='def response_text(data):\n'
helper=r'''def response_image_bytes(data):
    for item in (data.get('output') or []):
        if isinstance(item, dict) and item.get('type') == 'image_generation_call' and item.get('result'):
            try:
                raw=base64.b64decode(item.get('result'), validate=False)
                if raw and len(raw) <= 30*1024*1024:
                    return raw
            except Exception:
                pass
    return None


'''
if 'def response_image_bytes(data):' not in s:
    if anchor not in s:
        raise SystemExit('response helper anchor not found')
    s=s.replace(anchor,helper+anchor,1)

# Multimodal/owner patches run before this patch, so payload_input is the final
# authoritative request body. Enrich Aurora/Angel there for the paid route.
payload_anchor='''            payload={"input":payload_input,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}\n            if route=="paid":\n                data, via=call_paid_upstream(payload)\n'''
payload_new='''            paid_image_request = route=="paid" and is_image_generation_request(text)\n            if route=="paid":\n                paid_text=normalize_owner_image_prompt(text, getattr(self, "current_user", None))\n                paid_text=enrich_character_prompt(paid_text,self.headers)\n                if isinstance(payload_input, str):\n                    payload_input=owner_mode + paid_text\n                elif isinstance(payload_input, list):\n                    try:\n                        for _msg in payload_input:\n                            for _part in (_msg.get("content") or []):\n                                if _part.get("type")=="input_text":\n                                    _part["text"]=owner_mode + paid_text\n                    except Exception:\n                        pass\n            payload={"input":payload_input,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}\n            if paid_image_request:\n                payload["image_generation"]=True\n            if route=="paid":\n                data, via=call_paid_upstream(payload)\n'''
if payload_anchor not in s:
    raise SystemExit('paid payload_input anchor not found')
s=s.replace(payload_anchor,payload_new,1)

out_anchor='''            out=response_text(data)\n            if not out:\n                out="O Hermes concluiu a execução, mas não retornou texto."\n'''
out_new='''            if route=="paid" and paid_image_request:\n                paid_raw=response_image_bytes(data)\n                if paid_raw:\n                    mid=store_media(paid_raw,"image/png")\n                    meta={"category":"Imagem","skill":"image-generation","provider":"GPT-5.6 Sol · OpenAI image generation"}\n                    return self.sendb(200,json.dumps({"text":"Imagem criada pela rota GPT paga usando a memória compartilhada da personagem.","via":via,"routeMeta":meta,"imageUrl":"/api/media/"+mid},ensure_ascii=False))\n            out=response_text(data)\n            if not out:\n                out="O Hermes concluiu a execução, mas não retornou texto."\n'''
if out_anchor not in s:
    raise SystemExit('paid output anchor not found')
s=s.replace(out_anchor,out_new,1)

p.write_text(s)
print('paid character image route patch applied')
