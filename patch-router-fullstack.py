from pathlib import Path

p = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
s = p.read_text(encoding='utf-8')

s = s.replace('version: 3.0.0', 'version: 3.1.0', 1)
old = '''## WEBSITE / WEB APP / LANDING PAGE / UI

Use for sites, landing pages, frontend, responsive UI, HTML/CSS/JS, interactive web pages, or visual redesign.

- Web design patterns and layout direction -> `popular-web-designs`
- High-end design direction -> `claude-design`
- Design specification / system documentation -> `design-md`
- Creative interactive web experiences -> `p5js`
- Large implementation task -> `codex`, `claude-code`, or `opencode` according to user preference/availability
- Debug broken website/app -> `systematic-debugging`
- Inspect unfamiliar codebase first -> `codebase-inspection`

A request to "create a website" must result in functioning implementation, not just visual suggestions.
'''
new = '''## WEBSITE / WEB APP / LANDING PAGE / UI

Use for sites, systems, dashboards, SaaS, landing pages, frontend, backend, responsive UI, HTML/CSS/JS, interactive web pages, full-stack applications, or visual redesign.

- Create a new site/system/app end-to-end -> `hermes-fullstack-builder` (primary)
- Extend or finish an existing full-stack project -> `hermes-fullstack-builder` (primary)
- Web design patterns and layout direction -> `popular-web-designs` only as supporting skill when visual direction is material
- High-end design direction -> `claude-design` only as supporting skill
- Design specification / system documentation -> `design-md`
- Creative interactive web experiences -> `p5js`
- Large delegated coding subtask -> `codex`, `claude-code`, or `opencode` only when actually available and useful
- Debug broken website/app -> `systematic-debugging`
- Inspect unfamiliar codebase first -> `codebase-inspection`

A request to "create a website", "crie um sistema" or "faça um app" must route to `hermes-fullstack-builder` and result in functioning implementation, not just visual suggestions or snippets.
'''
if old not in s:
    raise SystemExit('website route anchor not found')
s = s.replace(old, new, 1)
s = s.replace('Route: `popular-web-designs` + one implementation skill only if needed.', 'Route: `hermes-fullstack-builder` (primary) + visual-design skill only if materially needed.', 1)
p.write_text(s, encoding='utf-8')
print('fullstack router patch applied')
