from pathlib import Path

path = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = path.read_text(encoding='utf-8')
marker = 'multi-agent-coherent-orchestrator'
if marker not in text:
    block = '''\n## MULTI-AGENT / COMPLEX PROJECT ORCHESTRATION\n\nUse when the user asks for a large multi-stage software/system project, coordinated review by several engineering disciplines, explicit sub-agents/sub-processes, cross-review before delivery, or a workflow that materially benefits from architecture + implementation + QA/security roles.\n\n- Primary skill -> `multi-agent-coherent-orchestrator`\n- Use only when task complexity justifies multiple specialist roles; do not add orchestration overhead to simple requests.\n- Pair with at most 1-2 narrow specialist skills when actual implementation or domain expertise is required.\n- For full-stack system construction, prefer `multi-agent-coherent-orchestrator` + `hermes-fullstack-builder`.\n- For authorized security-heavy work, add the narrowest relevant installed security skill rather than loading every security skill.\n- Cross-review must converge on one coherent implementation; do not return incompatible alternatives as a final result.\n- Validate with real tests/tools when available and distinguish verified results from inference.\n\n'''
    anchor = '## METAPROGRAMMING / SELF-REFLECTION / CONTEXT OPTIMIZATION'
    if anchor in text:
        text = text.replace(anchor, block + anchor, 1)
    else:
        text += block
    path.write_text(text, encoding='utf-8')
