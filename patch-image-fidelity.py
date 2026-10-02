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
    focus=[]
    req=[]

    is_bed=any(t in low for t in ('na cama','em uma cama','sobre a cama','cama'))
    is_sofa=any(t in low for t in ('no sofá','no sofa','em um sofá','em um sofa'))
    is_chair=any(t in low for t in ('na cadeira','em uma cadeira'))
    is_armchair=any(t in low for t in ('na poltrona','em uma poltrona'))
    is_lying=any(t in low for t in ('deitada','deitado','lying down','lying on'))
    is_seated=any(t in low for t in ('sentada','sentado','seated','sitting'))
    is_standing=any(t in low for t in ('em pé','em pe','standing'))
    is_kneeling=any(t in low for t in ('ajoelhada','ajoelhado','kneeling'))
    legs_apart=any(t in low for t in ('pernas abertas','joelhos afastados','legs apart','knees apart'))

    # Put a concise visual scene capsule FIRST. Diffusion models follow short,
    # concrete visual language better than long administrative instructions.
    if is_bed and is_lying:
        focus.append('Primary composition: the subject is lying relaxed on a clearly visible modern bed, with the bed visibly supporting the body and remaining the unmistakable setting.')
    elif is_bed and is_seated:
        focus.append('Primary composition: the subject is seated on a clearly visible modern bed; the bed must remain the unmistakable setting.')
    elif is_bed:
        focus.append('Primary composition: the subject is on a clearly visible modern bed; the bed must remain the unmistakable setting.')
    elif is_sofa:
        focus.append('Primary composition: the subject is on a clearly visible sofa; do not replace the sofa with another piece of furniture.')
    elif is_chair:
        focus.append('Primary composition: the subject is using a clearly visible chair; do not replace it with another setting.')
    elif is_armchair:
        focus.append('Primary composition: the subject is using a clearly visible armchair; do not replace it with another setting.')

    if is_lying and not (is_bed and focus):
        focus.append('Primary pose: the subject is lying down in a relaxed pose.')
    elif is_seated and not (is_bed and focus):
        focus.append('Primary pose: the subject is seated in a relaxed pose.')
    elif is_standing:
        focus.append('Primary pose: the subject is standing.')
    elif is_kneeling:
        focus.append('Primary pose: the subject is kneeling.')

    if legs_apart:
        focus.append('Leg position: keep the legs naturally apart in the relaxed non-explicit pose requested; do not cross or close them.')

    if any(t in low for t in ('corpo inteiro','de corpo inteiro','full body')):
        focus.append('Framing: show the full body from head to feet.')
        req.append('Use a full-body composition with the head and feet visible unless the user explicitly requested otherwise.')
    if any(t in low for t in ('close-up','close up','primeiro plano')):
        focus.append('Framing: use the requested close-up composition.')
        req.append('Use the requested close-up framing.')

    locations=[
        (is_bed, 'The requested scene must clearly show the subject on or in a visible bed. Keep the bed as the actual setting; do not replace it with a sofa, chair, armchair or plain studio background.'),
        (is_sofa, 'The requested scene must clearly show the subject on a visible sofa. Do not replace it with a bed, chair or armchair.'),
        (is_chair, 'The requested scene must clearly show the subject using a visible chair. Do not replace it with a bed, sofa or armchair.'),
        (is_armchair, 'The requested scene must clearly show the subject using a visible armchair. Do not replace it with a bed, sofa or chair.'),
        (any(t in low for t in ('no escritório','no escritorio','em um escritório','em um escritorio')), 'Keep the requested office setting clearly recognizable, with visible workplace elements.'),
        (any(t in low for t in ('na cozinha','em uma cozinha')), 'Keep the requested kitchen setting clearly recognizable and visible in the frame.'),
        (any(t in low for t in ('no banheiro','em um banheiro')), 'Keep the requested bathroom setting clearly recognizable and visible in the frame.'),
        (any(t in low for t in ('na varanda','em uma varanda')), 'Keep the requested balcony setting clearly recognizable and visible in the frame.'),
    ]
    for matched,instruction in locations:
        if matched:
            req.append(instruction)
            break

    if is_seated:
        req.append('Keep the subject seated as requested; do not change the main pose to standing or lying down.')
    if is_lying:
        req.append('Keep the subject lying down as requested; do not change the main pose to seated or standing.')
    if is_standing:
        req.append('Keep the subject standing as requested; do not change the main pose to seated or lying down.')
    if is_kneeling:
        req.append('Keep the subject kneeling as requested.')
    if legs_apart:
        req.append('Preserve the requested leg position without changing it to crossed or closed legs.')

    constraints=[
        'Follow the requested character, setting, pose, framing, style and lighting exactly.',
        'Preserve the character identity when a stored memory or visual reference exists.',
        'Do not add any written words, captions, labels, signs, banners, subtitles, watermarks or typography to the generated image unless the user explicitly asks for text in the image.',
    ]
    constraints.extend(req)
    constraints.append('The final picture itself must contain no instructional text or prompt wording.')

    # Scene capsule first, original request second, supporting constraints last.
    parts=[]
    if focus:
        parts.append(' '.join(focus))
    parts.append(raw)
    parts.append(' '.join(constraints))
    return '\n\n'.join(parts)


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
