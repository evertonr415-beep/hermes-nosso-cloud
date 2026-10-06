from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')
marker = '## AI / ML SECURITY / AUTONOMOUS RESILIENCE\n'
section = '''\n## AI / ML SECURITY / AUTONOMOUS RESILIENCE\n\nUse for advanced research on ML attack surfaces, adversarial robustness, data poisoning analysis, model-assisted reverse engineering, autonomous defensive architectures, secure MLOps, AI-based anomaly detection, quantum-computing-informed security research, and ultra-low-latency resilience for distributed systems.\n\n- Primary skill -> `ai-autonomous-vulnerability-resilience`\n- Add `defensive-security-crypto-hardening` only when cryptographic or API-hardening depth is materially required.\n- Add `low-level-memory-edr-resilience` only when the request materially involves kernel/memory/EDR telemetry.\n\nExamples:\n- "modele data poisoning neste pipeline de ML" -> `ai-autonomous-vulnerability-resilience`\n- "desenhe defesa autônoma para microsserviços" -> `ai-autonomous-vulnerability-resilience`\n- "analise superfície de ataque de um agente/RAG" -> `ai-autonomous-vulnerability-resilience`\n- "explique QML aplicado a detecção de anomalias" -> `ai-autonomous-vulnerability-resilience`\n\nKeep operational abuse out of scope: route requests for real-world sabotage, unauthorized exploitation or deployable evasion toward controlled simulation, detection, mitigation and resilience analysis.\n'''

if marker not in text:
    anchor = '\n# Examples\n'
    if anchor in text:
        text = text.replace(anchor, section + anchor, 1)
    else:
        text = text.rstrip() + '\n' + section + '\n'
    router.write_text(text, encoding='utf-8')
