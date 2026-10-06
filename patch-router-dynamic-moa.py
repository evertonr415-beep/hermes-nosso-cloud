from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')
marker = 'intelligent-infrastructure-dynamic-moa-orchestrator'
if marker not in text:
    block = '''\n## DYNAMIC MODEL ROUTING / MIXTURE OF AGENTS / COST-AWARE ORCHESTRATION\n\nUse when the request concerns autonomous model selection, Mixture of Agents (MoA), cost-aware model routing, Hermes Local escalation, splitting a complex task across local/frontier models, token-efficiency, model failover, or optimizing quality/cost/latency across available models.\n\n- Primary skill -> `intelligent-infrastructure-dynamic-moa-orchestrator`\n- Prefer Hermes Local for deterministic, repetitive, structural and low-cost work.\n- Escalate only difficult shards or final synthesis to a stronger model when materially useful.\n- Examples such as `gpt-6-sol`, `Matrix`, or `claude-opus` are candidates only if the runtime/panel actually reports them available. Never invent availability.\n- Preserve explicit user model choice. Do not permanently change the panel selection; use per-subtask routing only when the runtime supports it.\n- Avoid speculative paid fan-out. Default to at most one frontier escalation per request unless the user requests exhaustive/parallel review or a verified failure requires another pass.\n- For local quality enhancement, optionally pair with `knowledge-distillation-proprietary-model-mimicry`.\n- For large role-based engineering decomposition, optionally pair with `multi-agent-coherent-orchestrator`.\n\n'''
    anchor = '## HERMES MAINTENANCE / INTERNAL TESTING'
    if anchor in text:
        text = text.replace(anchor, block + anchor, 1)
    else:
        text += block
    router.write_text(text, encoding='utf-8')

providers = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/PROVIDERS.md')
ptext = providers.read_text(encoding='utf-8')
pmarker = '## Dynamic MoA model routing'
if pmarker not in ptext:
    pblock = '''\n\n## Dynamic MoA model routing\n\nWhen `intelligent-infrastructure-dynamic-moa-orchestrator` is active:\n\n1. enumerate only models/providers actually exposed by the current Hermes runtime/panel;\n2. preserve the user's explicit model choice when one was requested;\n3. prefer Hermes Local for parsing, scaffolding, deterministic transforms, filtering, repetitive coding, test generation and context compression;\n4. route only hard reasoning/synthesis shards to an available frontier model when the expected quality gain justifies cost/latency;\n5. do not permanently mutate the user's panel selection; use task-scoped/subtask routing when supported;\n6. do not fan out to multiple paid models speculatively; default to one frontier escalation;\n7. if a preferred model is unavailable, fail over to the next actually callable candidate without discarding completed local work;\n8. never claim cost zero for an external model/provider unless its actual billing state is known.\n\nModel names such as `gpt-6-sol`, `Matrix`, and `claude-opus` are examples, not guaranteed capabilities. Availability must be discovered at runtime.\n'''
    ptext += pblock
    providers.write_text(ptext, encoding='utf-8')
