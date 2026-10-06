from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')

section = '''\n## SECURITY / REVERSE ENGINEERING / SANDBOXED AUDIT\n\nUse for authorized code auditing, reverse engineering, defensive vulnerability analysis, advanced automation, protocol/interface reconstruction, local sandbox simulation, and security diagnostics.\n\n- Authorized security audit / reverse engineering / sandbox simulation -> `sandbox-security-reverse-engineering`\n- Defensive vulnerability reproduction and remediation -> `sandbox-security-reverse-engineering`, optionally with `systematic-debugging` when a concrete software bug must be fixed\n- Advanced automation in an authorized environment -> `sandbox-security-reverse-engineering`\n- Interface reconstruction from user-provided or authorized references -> `sandbox-security-reverse-engineering`; add a web implementation skill only when a real web artifact is requested\n\nPrefer the sandbox executor for untrusted code and experiments. Do not route unauthorized intrusion, credential theft, persistence, destructive exploitation, stealth/evasion, or malware deployment to this skill.\n\n'''

if '## SECURITY / REVERSE ENGINEERING / SANDBOXED AUDIT' not in text:
    marker = '## SOFTWARE DEVELOPMENT / BUGS / TESTING\n'
    if marker not in text:
        raise SystemExit('router marker not found')
    text = text.replace(marker, section + marker, 1)
    router.write_text(text, encoding='utf-8')
