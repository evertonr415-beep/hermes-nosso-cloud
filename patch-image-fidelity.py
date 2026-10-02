from pathlib import Path
import re

p=Path('/app/hermes-simple.py')
s=p.read_text()

anchor='def enrich_character_prompt(text, headers):\n'
helper=r'''def apply_image_fidelity_prompt(prompt):
    raw=(prompt or '').strip()
    if not raw:
        return raw
    low=raw.lower()
    req=[]

    locations=[
        (('na cama','em uma cama','sobre a cama','cama'), 'CENÁRIO OBRIGATÓRIO: a personagem deve estar claramente em/sobre uma cama visível no enquadramento. Não substituir a cama por sofá, cadeira, poltrona ou fundo de estúdio.'),
        (('no sofá','no sofa','em um sofá','em um sofa'), 'CENÁRIO OBRIGATÓRIO: a personagem deve estar claramente em um sofá visível. Não substituir por cama, cadeira ou poltrona.'),
        (('na cadeira','em uma cadeira'), 'CENÁRIO OBRIGATÓRIO: a personagem deve estar claramente em uma cadeira visível. Não substituir por cama, sofá ou poltrona.'),
        (('na poltrona','em uma poltrona'), 'CENÁRIO OBRIGATÓRIO: a personagem deve estar claramente em uma poltrona visível. Não substituir por cama, sofá ou cadeira.'),
        (('no escritório','no escritorio','em um escritório','em um escritorio'), 'CENÁRIO OBRIGATÓRIO: usar um escritório claramente reconhecível, com elementos de ambiente de trabalho visíveis.'),
        (('na cozinha','em uma cozinha'), 'CENÁRIO OBRIGATÓRIO: usar uma cozinha claramente reconhecível e visível no enquadramento.'),
        (('no banheiro','em um banheiro'), 'CENÁRIO OBRIGATÓRIO: usar um banheiro claramente reconhecível e visível no enquadramento.'),
        (('na varanda','em uma varanda'), 'CENÁRIO OBRIGATÓRIO: usar uma varanda claramente reconhecível e visível no enquadramento.'),
    ]
    for terms,instruction in locations:
        if any(t in low for t in terms):
            req.append(instruction)
            break

    poses=[
        (('sentada','sentado'), 'POSE OBRIGATÓRIA: manter a personagem sentada; não trocar para em pé ou deitada.'),
        (('deitada','deitado'), 'POSE OBRIGATÓRIA: manter a personagem deitada; não trocar para sentada ou em pé.'),
        (('em pé','em pe'), 'POSE OBRIGATÓRIA: manter a personagem em pé; não trocar para sentada ou deitada.'),
        (('ajoelhada','ajoelhado'), 'POSE OBRIGATÓRIA: manter a personagem ajoelhada conforme solicitado.'),
        (('pernas abertas','joelhos afastados'), 'POSE OBRIGATÓRIA: preservar a posição das pernas descrita pelo usuário, sem substituir por pernas cruzadas ou fechadas.'),
    ]
    for terms,instruction in poses:
        if any(t in low for t in terms):
            req.append(instruction)

    framing=[]
    if any(t in low for t in ('corpo inteiro','de corpo inteiro','full body')):
        framing.append('ENQUADRAMENTO OBRIGATÓRIO: corpo inteiro visível, sem cortar cabeça ou pés.')
    if any(t in low for t in ('close-up','close up','primeiro plano')):
        framing.append('ENQUADRAMENTO OBRIGATÓRIO: primeiro plano/close-up conforme solicitado.')

    rules=[
        '[FIDELIDADE RÍGIDA AO PEDIDO DE IMAGEM]',
        'Trate personagem, cenário, pose, enquadramento, estilo e iluminação explicitamente pedidos como requisitos obrigatórios, não como sugestões.',
        'Não troque o cenário por outro semelhante e não altere a pose principal.',
        'Preserve a identidade visual da personagem quando houver memória ou referência cadastrada.',
    ]
    rules.extend(req)
    rules.extend(framing)
    rules.append('PEDIDO ORIGINAL DO USUÁRIO:')
    rules.append(raw)
    return '\n'.join(rules)


'''
if 'def apply_image_fidelity_prompt(prompt):' not in s:
    if anchor not in s:
        raise SystemExit('image fidelity helper anchor not found')
    s=s.replace(anchor,helper+anchor,1)

# Apply after all account/owner normalization to free generation and edits.
pat_gen=r'(?m)^(\s*)mid, used_space=generate_zero_cost_image\(effective_image_prompt\)$'
def repl_gen(m):
    ind=m.group(1)
    return ind+'effective_image_prompt=apply_image_fidelity_prompt(effective_image_prompt)\n'+ind+'mid, used_space=generate_zero_cost_image(effective_image_prompt)'
s,n_gen=re.subn(pat_gen,repl_gen,s)

pat_edit=r'(?m)^(\s*)mid, used_space=generate_zero_cost_edit\(item\["bytes"\], item\["mime"\], effective_image_prompt\)$'
def repl_edit(m):
    ind=m.group(1)
    return ind+'effective_image_prompt=apply_image_fidelity_prompt(effective_image_prompt)\n'+ind+'mid, used_space=generate_zero_cost_edit(item["bytes"], item["mime"], effective_image_prompt)'
s,n_edit=re.subn(pat_edit,repl_edit,s)

# Paid image route receives the same fidelity reinforcement.
paid='paid_text=enrich_character_prompt(paid_text,self.headers)\n'
if paid in s and 'paid_text=apply_image_fidelity_prompt(paid_text)' not in s:
    s=s.replace(paid,paid+'                paid_text=apply_image_fidelity_prompt(paid_text)\n',1)

# Surface the behavior in the owner rules page description without adding a new policy switch.
s=s.replace(
    'Preferências do proprietário salvas no servidor e aplicadas em qualquer dispositivo.',
    'Preferências do proprietário salvas no servidor e aplicadas em qualquer dispositivo. Cenário, pose e enquadramento pedidos são tratados como requisitos rígidos na geração de imagens.'
)

p.write_text(s)
print(f'image fidelity patch applied generation={n_gen} edit={n_edit}')
