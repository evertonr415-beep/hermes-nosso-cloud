from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

old = '''def is_image_generation_request(text):
    t = (text or '').lower()
    verbs = ('crie ', 'criar ', 'gere ', 'gerar ', 'faça ', 'faca ', 'desenhe ', 'produza ', 'edite ', 'editar ', 'modifique ', 'mude ', 'troque ', 'coloque ', 'remova ')
    nouns = ('imagem', 'foto', 'ilustração', 'ilustracao', 'arte', 'rosto', 'fundo', 'óculos', 'oculos')
    return any(v in t for v in verbs) and any(n in t for n in nouns)
'''

new = '''def is_image_generation_request(text):
    t = (text or '').lower()

    # Software/product-building intent always wins over incidental mentions of
    # photos/images inside a specification. Example: a pet-management system
    # may need photo uploads, but that must be routed to the coding agent, not
    # to an image generator.
    software_terms = (
        'sistema', 'software', 'aplicativo', 'app ', 'web app', 'site', 'website',
        'portal', 'plataforma', 'painel', 'dashboard', 'frontend', 'backend',
        'api', 'banco de dados', 'database', 'supabase', 'postgres', 'sql',
        'login', 'cadastro', 'autenticação', 'autenticacao', 'crud', 'deploy',
        'vercel', 'github', 'repositório', 'repositorio', 'responsivo',
        'mobile', 'desktop', 'pwa', 'saas', 'módulo', 'modulo'
    )
    build_terms = (
        'criar um sistema', 'crie um sistema', 'desenvolver um sistema',
        'desenvolva um sistema', 'construir um sistema', 'monte um sistema',
        'criar um app', 'crie um app', 'criar um site', 'crie um site',
        'desenvolver um app', 'desenvolver um site', 'implementar', 'desenvolva'
    )
    if any(term in t for term in software_terms) or any(term in t for term in build_terms):
        return False

    verbs = ('crie ', 'criar ', 'gere ', 'gerar ', 'faça ', 'faca ', 'desenhe ', 'produza ', 'edite ', 'editar ', 'modifique ', 'mude ', 'troque ', 'coloque ', 'remova ', 'transforme ', 'recrie ')
    nouns = (
        'imagem', 'foto', 'ilustração', 'ilustracao', 'arte', 'rosto', 'fundo', 'óculos', 'oculos',
        'personagem', 'mulher virtual', 'homem virtual', 'pessoa virtual', 'modelo virtual', 'retrato',
        'corpo', 'anatomia', 'nudez', 'nu artístico', 'nu artistico', 'nua', 'nu ', 'figurino', 'biquíni', 'biquini', 'lingerie'
    )
    return any(v in t for v in verbs) and any(n in t for n in nouns)
'''

if old not in s:
    raise SystemExit('image intent detector anchor not found')

s = s.replace(old, new, 1)
p.write_text(s)
