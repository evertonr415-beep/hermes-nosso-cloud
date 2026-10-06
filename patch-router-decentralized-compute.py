from pathlib import Path

path = Path('/opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md')
text = path.read_text(encoding='utf-8')
marker = 'decentralized-serverless-compute-orchestration'
if marker not in text:
    block = '''\n## DECENTRALIZED / P2P / EDGE / SERVERLESS COMPUTE ORCHESTRATION\n\nUse when the user asks for distributed or decentralized inference, P2P model execution, local/edge compute pooling, model sharding, zero-cost-first compute, Docker/Kubernetes migration, autonomous workload placement, tensor compression, quantization for constrained hardware, or reducing dependence on centralized AI APIs.\n\n- Primary skill -> `decentralized-serverless-compute-orchestration`\n- For large multi-component systems, optionally pair with `multi-agent-coherent-orchestrator`.\n- For local LLM runtime specifics, optionally pair with `llama-cpp` or `serving-llms-vllm` when installed and relevant.\n- Prefer local/open-source/zero-cost-first designs, but never claim physical infrastructure is literally free; account for hardware, power, bandwidth, storage, and node availability.\n- Benchmark real hardware before promising latency, throughput, or model capacity.\n\n'''
    anchor = '## HERMES MAINTENANCE / INTERNAL TESTING'
    if anchor in text:
        text = text.replace(anchor, block + anchor, 1)
    else:
        text += block
    path.write_text(text, encoding='utf-8')
