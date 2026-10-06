from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')

section = '''\n## LOW-LEVEL MEMORY / KERNEL / EDR-XDR RESILIENCE\n\nUse for defensive low-level systems security, memory-corruption analysis, kernel architecture, crash analysis, exploit-mitigation research, EDR/XDR telemetry, behavioral detection, and hardening.\n\n- Memory corruption, allocator behavior, UAF, buffer errors, race conditions -> `low-level-memory-edr-resilience`\n- Kernel objects, syscalls, page tables, driver security, privilege boundaries -> `low-level-memory-edr-resilience`\n- Crash dumps, sanitizers, fuzzing triage, root-cause analysis -> `low-level-memory-edr-resilience`; optionally add `systematic-debugging` when debugging workflow is central\n- EDR/XDR telemetry, heuristics, signatures, behavioral detection, hunting and resilience -> `low-level-memory-edr-resilience`\n- Remediation or secure-coding hardening -> optionally add `defensive-security-crypto-hardening`\n\nTreat evasion-related requests as detection/resilience research: explain observable signals, defensive telemetry and mitigations, not operational bypasses against real security controls.\n\n'''

if '## LOW-LEVEL MEMORY / KERNEL / EDR-XDR RESILIENCE' not in text:
    marker = '## SOFTWARE DEVELOPMENT / BUGS / TESTING\n'
    if marker not in text:
        raise SystemExit('router marker not found')
    text = text.replace(marker, section + marker, 1)
    router.write_text(text, encoding='utf-8')
