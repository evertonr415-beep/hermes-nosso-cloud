from pathlib import Path

p=Path('/app/bridge.py')
s=p.read_text()

# Upgrade the explicit paid Responses route so callers can opt into the
# official OpenAI image_generation tool. This remains manual-only.
old='''def paid_gpt_response(prompt, conversation=""):\n    \"\"\"Explicit paid GPT-5.6 Sol route. Never used as an automatic fallback.\"\"\"'''
new='''def paid_gpt_response(prompt, conversation="", image_generation=False):\n    \"\"\"Explicit paid GPT-5.6 Sol route. Never used as an automatic fallback.\n\n    When image_generation=True, expose the official Responses API\n    image_generation hosted tool and require a tool call.\n    \"\"\"'''
if old not in s:
    raise SystemExit('paid_gpt_response signature anchor not found')
s=s.replace(old,new,1)

old_payload='''    payload={\n        \"model\":\"gpt-5.6-sol\",\n        \"input\":prompt,\n        \"reasoning\":{\"effort\":\"medium\"},\n        \"store\":True,\n    }\n'''
new_payload='''    payload={\n        \"model\":\"gpt-5.6-sol\",\n        \"input\":prompt,\n        \"reasoning\":{\"effort\":\"medium\"},\n        \"store\":True,\n    }\n    if image_generation:\n        payload[\"tools\"]=[{\"type\":\"image_generation\",\"size\":\"1024x1536\",\"quality\":\"auto\"}]\n        payload[\"tool_choice\"]={\"type\":\"image_generation\"}\n'''
if old_payload not in s:
    raise SystemExit('paid payload anchor not found')
s=s.replace(old_payload,new_payload,1)

old_call='''                prompt=msg.get(\"input\") or \"\"\n                conversation=msg.get(\"conversation\") or \"\"\n                data=paid_gpt_response(prompt,conversation)\n'''
new_call='''                prompt=msg.get(\"input\") or \"\"\n                conversation=msg.get(\"conversation\") or \"\"\n                image_generation=bool(msg.get(\"image_generation\"))\n                data=paid_gpt_response(prompt,conversation,image_generation=image_generation)\n'''
if old_call not in s:
    raise SystemExit('paid route call anchor not found')
s=s.replace(old_call,new_call,1)

p.write_text(s)
print('paid image-generation bridge patch applied')
