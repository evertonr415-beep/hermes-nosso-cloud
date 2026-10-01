from pathlib import Path
p=Path('/tmp/patch-private-auth.py')
s=p.read_text()
s=s.replace("new=r'''LOGIN_HTML", 'new=r"""LOGIN_HTML', 1)
needle="\n'''\nif old not in s:\n    raise SystemExit('auth function anchor not found')"
repl='\n"""\nif old not in s:\n    raise SystemExit(\'auth function anchor not found\')'
if needle not in s:
    raise SystemExit('private auth closing quote anchor not found')
s=s.replace(needle,repl,1)
p.write_text(s)
