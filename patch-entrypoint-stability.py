from pathlib import Path

entrypoint = Path('/usr/local/bin/hermes-railway-entrypoint')
text = entrypoint.read_text(encoding='utf-8')

old_provider = 'model["provider"] = "openai-api"'
new_provider = 'model["provider"] = "openai-codex"'
if old_provider in text:
    text = text.replace(old_provider, new_provider, 1)

old_fallbacks = '''data["fallback_providers"] = [
    {"provider": "openai-codex", "model": "gpt-6-sol"},
    {"provider": "openai-codex", "model": "gpt-5.6-sol"},
]
'''
new_fallbacks = '''data["fallback_providers"] = [
    {"provider": "openai-codex", "model": "gpt-5.6-sol"},
]
'''
if old_fallbacks in text:
    text = text.replace(old_fallbacks, new_fallbacks, 1)

# Belt-and-suspenders: the supervised plugin service owns plugin lifecycle.
text = text.replace('${HERMES_CURATED_PLUGINS_BOOTSTRAP:-1}', '${HERMES_CURATED_PLUGINS_BOOTSTRAP:-0}')

entrypoint.write_text(text, encoding='utf-8')
