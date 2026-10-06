from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')

section = '''\n## ACADEMIC SECURITY TOOLING / CONTROLLED LAB AUTOMATION\n\nUse for engineering security-testing tools in CTFs, isolated labs, deliberately vulnerable apps, private test networks, and explicitly authorized environments.\n\n- Security tooling architecture, lab scanners, fuzzers, harnesses, CLI automation -> `academic-security-tooling`\n- Controlled validation workflows and reproducible lab exercises -> `academic-security-tooling`\n- Academic attack-chain modeling with detection/remediation -> `academic-security-tooling`; optionally add `red-team-ctf-academic` for CTF methodology\n- Defensive fixes, OWASP or hardening -> add `defensive-security-crypto-hardening`\n\nDo not route unauthorized intrusion, malware deployment, credential theft, operational persistence, destructive actions, indiscriminate public scanning, or stealth/evasion against real defenders to this skill. Convert ambiguous requests into a safe lab simulation or defensive analysis.\n\n'''

if '## ACADEMIC SECURITY TOOLING / CONTROLLED LAB AUTOMATION' not in text:
    marker = '## RED TEAM / CTF / OFFENSIVE SECURITY LABS\n'
    if marker not in text:
        marker = '## SECURITY / REVERSE ENGINEERING / SANDBOXED AUDIT\n'
    if marker not in text:
        raise SystemExit('router marker not found')
    text = text.replace(marker, section + marker, 1)
    router.write_text(text, encoding='utf-8')
