from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Remove indentation-sensitive lines injected by the first rules patch.
# Image requests get a compact image-specific preference layer instead of the
# full chat-policy block, which was diluting scene and pose instructions.
kept=[]
for line in s.splitlines(True):
    if 'effective_image_prompt=client_rules_instruction(self.headers)+effective_image_prompt' in line:
        continue
    if 'paid_text=client_rules_instruction(self.headers)+paid_text' in line:
        continue
    kept.append(line)
s=''.join(kept)

anchor='def enrich_character_prompt(text, headers):\n'
helper=r'''def image_client_rules_instruction(headers):
    r=load_client_rules(headers)
    parts=[]
    if r.get('allow_adult_fictional_nudity'):
        parts.append('For clearly adult fully fictional characters, artistic/anatomical nudity may be handled when the selected provider supports it.')
    if r.get('allow_adult_fictional_sensuality'):
        parts.append('For clearly adult fully fictional characters, non-explicit adult sensuality may be handled when the selected provider supports it.')
    custom=str(r.get('custom_instructions') or '').strip()
    if custom:
        # Keep account customization active, but do not let a long admin text
        # overwhelm the visual scene specification sent to diffusion models.
        parts.append('Owner image preferences: '+custom[:1200])
    parts.append('Do not depict minors or age-ambiguous subjects in sexual contexts. Keep provider-required limits in force.')
    return ' '.join(parts)


'''
if 'def image_client_rules_instruction(headers):' not in s:
    if anchor not in s:
        raise SystemExit('image rules helper anchor not found')
    s=s.replace(anchor,helper+anchor,1)

# Character-aware image prompts keep the actual scene first. Character memory
# and compact owner preferences come afterwards so pose/location remain the
# strongest visual instructions.
old='''    if not matched:\n        return client_rules_instruction(headers)+raw\n'''
new='''    if not matched:\n        extra=image_client_rules_instruction(headers)\n        return raw+('\\n'+extra if extra else '')\n'''
if old in s:
    s=s.replace(old,new,1)

old2="""    return client_rules_instruction(headers)+' '.join(notes)+'\\n'+raw\n"""
new2="""    extra=image_client_rules_instruction(headers)\n    tail=' '.join(notes)\n    if extra:\n        tail=(tail+' '+extra).strip()\n    return raw+('\\n'+tail if tail else '')\n"""
if old2 in s:
    s=s.replace(old2,new2,1)

p.write_text(s)
print('owner admin rules image-specific prompt layer applied')
