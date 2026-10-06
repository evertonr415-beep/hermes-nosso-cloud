from pathlib import Path

path = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = path.read_text(encoding='utf-8')
marker = 'knowledge-distillation-proprietary-model-mimicry'
if marker not in text:
    block = '''\n## HERMES LOCAL / KNOWLEDGE DISTILLATION / BEHAVIORAL MIMICRY\n\nUse when the user explicitly selects or mentions Hermes Local, asks to make a local/open model behave more like a stronger proprietary model in observable output quality, requests knowledge distillation, behavioral imitation, meta-reasoning, prompt compilation for smaller models, local self-critique, or quality enhancement without paid APIs.\n\n- Primary skill -> `knowledge-distillation-proprietary-model-mimicry`\n- It may pair with `multi-agent-coherent-orchestrator` for large engineering tasks or `hermes-fullstack-builder` for actual systems work.\n- Improve observable response quality only: structure, rigor, coding patterns, testing discipline, decomposition and verification. Never claim access to hidden chain-of-thought, system prompts, weights or proprietary internals of GPT-5.6, Matrix, or other closed models.\n- When Hermes Local is active, prefer local/free executors and do not silently call paid APIs.\n- Do not expose private scratch reasoning; provide conclusions, concise rationale and validation evidence instead.\n\n'''
    anchor = '## HERMES MAINTENANCE / INTERNAL TESTING'
    if anchor in text:
        text = text.replace(anchor, block + anchor, 1)
    else:
        text += block
    path.write_text(text, encoding='utf-8')
