from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Remove indentation-sensitive lines injected by the first rules patch.
# The account rules are applied centrally in enrich_character_prompt below.
kept=[]
for line in s.splitlines(True):
    if 'effective_image_prompt=client_rules_instruction(self.headers)+effective_image_prompt' in line:
        continue
    if 'paid_text=client_rules_instruction(self.headers)+paid_text' in line:
        continue
    kept.append(line)
s=''.join(kept)

# Apply the same account rules to every character-aware image request without
# touching Handler indentation. This covers free generation, edits and paid
# character images because they all call enrich_character_prompt.
old='''    if not matched:\n        return raw\n'''
new='''    if not matched:\n        return client_rules_instruction(headers)+raw\n'''
if old in s:
    s=s.replace(old,new,1)

old2="""    return ' '.join(notes)+'\\n'+raw\n"""
new2="""    return client_rules_instruction(headers)+' '.join(notes)+'\\n'+raw\n"""
if old2 in s:
    s=s.replace(old2,new2,1)

p.write_text(s)
print('owner admin rules indentation fix applied')
