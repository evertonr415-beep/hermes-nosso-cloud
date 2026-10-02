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
        (('na cama','em uma cama','sobre a cama','cama'), 'The requested scene must clearly show the subject on or in a visible bed. Keep the bed as the actual setting; do not replace it with a sofa, chair, armchair or plain studio background.'),
        (('no sofá','no sofa','em um sofá','em um sofa'), 'The requested scene must clearly show the subject on a visible sofa. Do not replace it with a bed, chair or armchair.'),
        (('na cadeira','em uma cadeira'), 'The requested scene must clearly show the subject using a visible chair. Do not replace it with a bed, sofa or armchair.'),
        (('na poltrona','em uma poltrona'), 'The requested scene must clearly show the subject using a visible armchair. Do not replace it with a bed, sofa or chair.'),
        (('no escritório','no escritorio','em um escritório','em um escritorio'), 'Keep the requested office setting clearly recognizable, with visible workplace elements.'),
        (('na cozinha','em uma cozinha'), 'Keep the requested kitchen setting clearly recognizable and visible in the frame.'),
        (('no banheiro','em um banheiro'), 'Keep the requested bathroom setting clearly recognizable and visible in the frame.'),
        (('na varanda','em uma varanda'), 'Keep the requested balcony setting clearly recognizable and visible in the frame.'),
    ]
    for terms,instruction in locations:
        if any(t in low for t in terms):
            req.append(instruction)
            break

    poses=[
        (('sentada','sentado'), 'Keep the subject seated as requested; do not change the main pose to standing or lying down.'),
        (('deitada','deitado'), 'Keep the subject lying down as requested; do not change the main pose to seated or standing.'),
        (('em pé','em pe'), 'Keep the subject standing as requested; do not change the main pose to seated or lying down.'),
        (('ajoelhada','ajoelhado'), 'Keep the subject kneeling as requested.'),
        (('pernas abertas','joelhos afastados'), 'Preserve the requested leg position without changing it to crossed or closed legs.'),
    ]
    for terms,instruction in poses:
        if any(t in low for t in terms):
            req.append(instruction)

    if any(t in low for t in ('corpo inteiro','de corpo inteiro','full body')):
        req.append('Use a full-body composition with the head and feet visible unless the user explicitly requested otherwise.')
    if any(t in low for t in ('close-up','close up','primeiro plano')):
        req.append('Use the requested close-up framing.')

    # Keep the user's actual scene description first. The following sentences are
    # silent generation constraints, not content to render inside the picture.
    constraints=[
        'Follow the requested character, setting, pose, framing, style and lighting exactly.',
        'Preserve the character identity when a stored memory or visual reference exists.',
        'Do not add any written words, captions, labels, signs, banners, subtitles, watermarks or typography to the generated image unless the user explicitly asks for text in the image.',
    ]
    constraints.extend(req)
    constraints.append('The final picture itself must contain no instructional text or prompt wording.')
    return raw+'\n\n'+' '.join(constraints)


'''
if 'def apply_image_fidelity_prompt(prompt):' not in s:
    if anchor not in s:
        raise SystemExit('image fidelity helper anchor not found')
    s=s.replace(anchor,helper+anchor,1)

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

paid='paid_text=enrich_character_prompt(paid_text,self.headers)\n'
if paid in s and 'paid_text=apply_image_fidelity_prompt(paid_text)' not in s:
    s=s.replace(paid,paid+'                paid_text=apply_image_fidelity_prompt(paid_text)\n',1)

s=s.replace(
    'Preferências do proprietário salvas no servidor e aplicadas em qualquer dispositivo.',
    'Preferências do proprietário salvas no servidor e aplicadas em qualquer dispositivo. Cenário, pose e enquadramento pedidos são tratados como requisitos rígidos na geração de imagens.'
)

p.write_text(s)
print(f'image fidelity patch applied generation={n_gen} edit={n_edit}')
