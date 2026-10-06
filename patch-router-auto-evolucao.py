from pathlib import Path

path = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = path.read_text(encoding='utf-8')
marker = 'auto-evolucao-recursiva'
if marker not in text:
    block = '''\n## RECURSIVE SELF-IMPROVEMENT / ARCHITECTURE SEARCH / HYPERPARAMETER EVOLUTION\n\nUse when the user asks for recursive self-improvement, neural architecture search, evolutionary model experiments, hyperparameter optimization, automated benchmark loops, self-refinement of local skills/code, or safe sandboxed model/code evolution.\n\n- Primary skill -> `auto-evolucao-recursiva`.\n- For local-model quality work, optionally pair with `knowledge-distillation-proprietary-model-mimicry`.\n- For evolving skills/context pipelines, optionally pair with `evolutionary-metaprogramming-context-optimization`.\n- For distributed authorized compute placement, optionally pair with `decentralized-serverless-compute-orchestration`.\n- Keep autonomous mutation inside sandbox/checkpointed experiments. Production promotion requires tests, evidence, diff and rollback.\n- Do not reinterpret a user optimization target into an independent permanent goal.\n\n'''
    anchor = '## HERMES MAINTENANCE / INTERNAL TESTING'
    if anchor in text:
        text = text.replace(anchor, block + anchor, 1)
    else:
        text += block
    path.write_text(text, encoding='utf-8')
