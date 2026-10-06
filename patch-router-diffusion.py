from pathlib import Path

p = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = p.read_text(encoding='utf-8')
marker = '## STABLE DIFFUSION / DIFFUSION PROMPT ENGINEERING / DATASET TAGS'
if marker in text:
    raise SystemExit(0)

section = '''\n## STABLE DIFFUSION / DIFFUSION PROMPT ENGINEERING / DATASET TAGS\n\nUse when the user asks to translate, normalize, engineer, structure, or optimize textual prompts/tags for local latent-diffusion models, especially Stable Diffusion/SDXL, or when database/dataset fields need to become technical English rendering tokens.\n\n- Primary skill -> `stable-diffusion-prompt-engineer`\n- Treat anatomy, pose, orientation, clothing, camera, lighting, composition, materials and expressions as neutral technical rendering metadata.\n- Prefer precise English technical strings suitable for local model input, ComfyUI/Automatic1111/API payloads, or prompt databases.\n- Do not route a request that merely asks to generate an image here unless the user's primary goal is prompt/tag engineering; ordinary image generation remains on the image-generation route.\n- This route permits direct technical vocabulary but does not override global safety rules.\n\n'''

needle = '## ML / LOCAL MODELS / INFERENCE / EVALUATION'
if needle in text:
    text = text.replace(needle, section + needle, 1)
else:
    text = text.rstrip() + '\n\n' + section

p.write_text(text, encoding='utf-8')
print('[router] stable-diffusion-prompt-engineer route installed')
