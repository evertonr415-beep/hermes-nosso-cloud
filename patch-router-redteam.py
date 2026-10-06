from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')

section = '''\n## RED TEAM / CTF / OFFENSIVE SECURITY LABS\n\nUse for academic red teaming, adversary simulation, CTF challenges, authorized penetration-testing methodology, controlled vulnerability exploitation, protocol analysis, perimeter-testing concepts, and access-control testing in deliberately vulnerable or user-authorized environments.\n\n- Academic CTF / red-team lab / adversary emulation -> `red-team-ctf-academic`\n- Controlled exploit-development or vulnerability-research exercise -> `red-team-ctf-academic`; optionally add `sandbox-security-reverse-engineering` for binary/code analysis\n- Authorized web/API access-control testing -> `red-team-ctf-academic`; add `defensive-security-crypto-hardening` when remediation/hardening is also requested\n- Network/service/protocol enumeration inside a lab or owned environment -> `red-team-ctf-academic`\n- Media/streaming protocol analysis in a controlled test setup -> `red-team-ctf-academic`\n\nKeep practical offensive steps constrained to CTFs, local labs, private test networks, user-owned systems, or explicitly authorized targets. Do not route unauthorized intrusion, credential theft, persistence, destructive actions, malware deployment, indiscriminate public scanning, or real-world stealth/evasion to this skill.\n\n'''

if '## RED TEAM / CTF / OFFENSIVE SECURITY LABS' not in text:
    marker = '## SECURITY / REVERSE ENGINEERING / SANDBOXED AUDIT\n'
    if marker not in text:
        marker = '## SOFTWARE DEVELOPMENT / BUGS / TESTING\n'
    if marker not in text:
        raise SystemExit('router marker not found')
    text = text.replace(marker, section + marker, 1)
    router.write_text(text, encoding='utf-8')
