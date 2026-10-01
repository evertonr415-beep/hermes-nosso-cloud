from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

anchor = '''def session_user(headers):
    token=_cookie_token(headers)
    if not token: return None
'''
replacement = '''def _local_owner_token():
    exp = int(time.time()) + 7*24*60*60
    secret = (os.getenv("HERMES_DASHBOARD_BASIC_AUTH_SECRET", "") or PASSWORD or "hermes-owner").encode("utf-8")
    msg = f"{USER}|{exp}".encode("utf-8")
    sig = hmac.new(secret, msg, "sha256").hexdigest()
    return f"local.{exp}.{sig}"

def _local_owner_user(token):
    try:
        if not token.startswith("local."):
            return None
        _, exp_s, sig = token.split(".", 2)
        exp = int(exp_s)
        if exp <= int(time.time()):
            return None
        secret = (os.getenv("HERMES_DASHBOARD_BASIC_AUTH_SECRET", "") or PASSWORD or "hermes-owner").encode("utf-8")
        msg = f"{USER}|{exp}".encode("utf-8")
        expected = hmac.new(secret, msg, "sha256").hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return {"id":"local-owner","username":USER,"role":"owner","local":True}
    except Exception:
        return None

def session_user(headers):
    token=_cookie_token(headers)
    if not token: return None
    local_user = _local_owner_user(token)
    if local_user:
        return local_user
'''
if anchor not in s:
    raise SystemExit('session_user anchor not found')
s = s.replace(anchor, replacement, 1)

old = '''                data,status=_auth_call("login",{"username":str(msg.get("username") or ""),"password":str(msg.get("password") or "")})
                if status==200 and data.get("token"):
'''
new = '''                login_user=str(msg.get("username") or "")
                login_pass=str(msg.get("password") or "")
                data,status=_auth_call("login",{"username":login_user,"password":login_pass})
                if not (status==200 and data.get("token")):
                    if USER and PASSWORD and hmac.compare_digest(login_user, USER) and hmac.compare_digest(login_pass, PASSWORD):
                        data={"ok":True,"token":_local_owner_token(),"user":{"id":"local-owner","username":USER,"role":"owner","local":True}}
                        status=200
                        print("[hermes-simple] owner login via cross-device fallback", flush=True)
                if status==200 and data.get("token"):
'''
if old not in s:
    raise SystemExit('login fallback anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)
