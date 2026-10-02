from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

old="""    body=dict(payload or {})\n    body['action']=action\n    body['token']=token\n    if token.startswith('local.'):\n        body['username']=USER\n    req=urllib.request.Request(PROFILE_EDGE_URL,data=json.dumps(body).encode('utf-8'),method='POST',headers={\n"""
new="""    body=dict(payload or {})\n    body['action']=action\n    body['token']=token\n    if token.startswith('local.') and action=='get_profile':\n        return {\n            'ok':True,\n            'user':{'id':'local-owner','username':USER,'role':'owner','local':True},\n            'preferences':{'default_route':'auto','settings':{'account_mode':'owner','cross_device':True}},\n            'characters':[\n                {'name':'Angel','aliases':['angel'],'description':'','metadata':{'fictional':True,'adult':True,'min_age':25},'reference_media':[]},\n                {'name':'Aurora','aliases':['aurora'],'description':'','metadata':{'fictional':True,'adult':True,'min_age':25},'reference_media':[]}\n            ]\n        }\n    req=urllib.request.Request(PROFILE_EDGE_URL,data=json.dumps(body).encode('utf-8'),method='POST',headers={\n"""
if old not in s:
    raise SystemExit('local profile fallback anchor not found')
s=s.replace(old,new,1)

p.write_text(s)
print('local owner profile fallback patch applied')
