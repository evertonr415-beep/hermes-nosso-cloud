from pathlib import Path

router = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = router.read_text(encoding='utf-8')

section = '''\n## DEFENSIVE SECURITY / OWASP / CRYPTOGRAPHY / HARDENING\n\nUse for secure-code review, OWASP remediation, defensive vulnerability analysis, threat modeling, applied cryptography, authentication/authorization design, secret handling, TLS, server/API hardening and authorized security verification.\n\n- Secure-code review / OWASP remediation -> `defensive-security-crypto-hardening`\n- Threat modeling / abuse-case analysis -> `defensive-security-crypto-hardening`\n- AES, RSA, signatures, hashes, KDFs, TLS, certificate or key-management explanation -> `defensive-security-crypto-hardening`\n- Linux/server/API/container hardening -> `defensive-security-crypto-hardening`\n- Authorized defensive verification of a concrete finding -> `defensive-security-crypto-hardening`, optionally with `systematic-debugging` when a software fix must be implemented\n- Reverse engineering, interface reconstruction or broad sandbox simulation -> keep using `sandbox-security-reverse-engineering`\n\nPrefer established cryptographic libraries, least privilege and safe verification tests. Do not route credential theft, malware deployment, persistence, destructive exploitation, stealth/evasion or unauthorized compromise to this skill.\n\n'''

if '## DEFENSIVE SECURITY / OWASP / CRYPTOGRAPHY / HARDENING' not in text:
    marker = '## SECURITY / REVERSE ENGINEERING / SANDBOXED AUDIT\n'
    if marker not in text:
        marker = '## SOFTWARE DEVELOPMENT / BUGS / TESTING\n'
    if marker not in text:
        raise SystemExit('router marker not found')
    text = text.replace(marker, section + marker, 1)
    router.write_text(text, encoding='utf-8')
