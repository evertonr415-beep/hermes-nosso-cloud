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
