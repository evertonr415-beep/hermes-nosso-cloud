from pathlib import Path

path = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = path.read_text(encoding='utf-8')
marker = 'evolutionary-metaprogramming-context-optimization'
if marker not in text:
    block = '''\n## METAPROGRAMMING / SELF-REFLECTION / CONTEXT OPTIMIZATION\n\nUse when the user asks for self-evaluation of agent/tool performance, recursive feedback loops, automatic skill refinement in sandbox, knowledge-graph-based concept linking, dynamic context compression/ranking, self-healing syntax pipelines, or local capability evolution without retraining neural weights.\n\n- Primary skill -> `evolutionary-metaprogramming-context-optimization`\n- For actual codebase changes, optionally pair with `codebase-inspection` or `systematic-debugging` when needed.\n- For Hermes skill authoring specifically, this skill may support `hermes-agent-skill-authoring`, but do not load both unless the task actually modifies skills.\n- Keep autonomous code mutation sandboxed by default; validate with tests, benchmarks, diff and rollback before production promotion.\n\n'''
    anchor = '## HERMES MAINTENANCE / INTERNAL TESTING'
    if anchor in text:
        text = text.replace(anchor, block + anchor, 1)
    else:
        text += block
    path.write_text(text, encoding='utf-8')
