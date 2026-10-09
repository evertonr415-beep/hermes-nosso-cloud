FROM nousresearch/hermes-agent:latest

# Build as root, but grant the Hermes gateway's unprivileged uid 10000
# access only to its own mutable state/log directories (never chmod 777 /opt).
USER root
ENV TMPDIR=/tmp
RUN install -d -o 10000 -g 10000 -m 0755 /opt/data \
    && install -d -o 10000 -g 10000 -m 0750 /opt/data/logs \
    && install -d -o 10000 -g 10000 -m 0750 /opt/data/logs/gateways \
    && install -d -o 10000 -g 10000 -m 0700 /tmp/hermes-runtime-logs \
    && install -d -o 10000 -g 10000 -m 0700 /tmp/hermes-runtime-cache

ENV NPM_CONFIG_CACHE=/tmp/npm-cache
ENV PATH="/opt/hermes/.venv/bin:/usr/local/bin:/usr/bin:/bin"
# The old entrypoint bootstrap targets six plugins and calls a dashboard helper
# signature that is no longer valid on Hermes 0.21.x. Curated plugins are
# persisted on /opt/data; production no longer keeps a bootstrap supervisor
# resident after startup.
ENV HERMES_CURATED_PLUGINS_BOOTSTRAP=0

# Add only Hermes Nosso skills that are not already bundled upstream.
COPY custom-skills.tar.gz.b64 /tmp/custom-skills.tar.gz.b64
RUN base64 -d /tmp/custom-skills.tar.gz.b64 | tar -tzf - | grep -c 'SKILL.md'
RUN base64 -d /tmp/custom-skills.tar.gz.b64 | tar -xz -C /opt/hermes/skills \
    && rm -f /tmp/custom-skills.tar.gz.b64

# Always-loaded routing skill: chooses the smallest relevant installed skill set.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router
COPY hermes-nosso-router/SKILL.md /opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md
COPY hermes-nosso-router/EXECUTORS.md /opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/EXECUTORS.md
COPY hermes-nosso-router/PROVIDERS.md /opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/PROVIDERS.md

# Hermes Nosso full-stack builder: creates and validates real sites/systems/apps.
RUN mkdir -p /opt/hermes/skills/software-development/hermes-fullstack-builder
COPY hermes-fullstack-builder/SKILL.md /opt/hermes/skills/software-development/hermes-fullstack-builder/SKILL.md
COPY patch-router-fullstack.py /tmp/patch-router-fullstack.py
RUN python3 /tmp/patch-router-fullstack.py \
    && rm -f /tmp/patch-router-fullstack.py

# Technical translator / prompt engineer for local latent-diffusion workflows.
RUN mkdir -p /opt/hermes/skills/machine-learning/stable-diffusion-prompt-engineer
COPY stable-diffusion-prompt-engineer/SKILL.md /opt/hermes/skills/machine-learning/stable-diffusion-prompt-engineer/SKILL.md
COPY patch-router-diffusion.py /tmp/patch-router-diffusion.py
RUN python3 /tmp/patch-router-diffusion.py \
    && rm -f /tmp/patch-router-diffusion.py

# Sandboxed engineering skill for authorized reverse engineering, code audit,
# defensive security diagnostics, automation and interface reconstruction.
RUN mkdir -p /opt/hermes/skills/security/sandbox-security-reverse-engineering
COPY sandbox-security-reverse-engineering/SKILL.md /opt/hermes/skills/security/sandbox-security-reverse-engineering/SKILL.md
COPY patch-router-security.py /tmp/patch-router-security.py
RUN python3 /tmp/patch-router-security.py \
    && rm -f /tmp/patch-router-security.py

# Defensive security specialist: OWASP, applied cryptography, threat modeling,
# secure coding, server/API hardening and authorized defensive verification.
RUN mkdir -p /opt/hermes/skills/security/defensive-security-crypto-hardening
COPY defensive-security-crypto-hardening/SKILL.md /opt/hermes/skills/security/defensive-security-crypto-hardening/SKILL.md
COPY patch-router-defensive-security.py /tmp/patch-router-defensive-security.py
RUN python3 /tmp/patch-router-defensive-security.py \
    && rm -f /tmp/patch-router-defensive-security.py

# Academic red-team / CTF instructor for controlled adversary simulation,
# authorized pentest methodology and lab-safe vulnerability exploitation.
RUN mkdir -p /opt/hermes/skills/security/red-team-ctf-academic
COPY red-team-ctf-academic/SKILL.md /opt/hermes/skills/security/red-team-ctf-academic/SKILL.md
COPY patch-router-redteam.py /tmp/patch-router-redteam.py
RUN python3 /tmp/patch-router-redteam.py \
    && rm -f /tmp/patch-router-redteam.py

# Academic security-tool engineering for isolated labs and authorized testing.
RUN mkdir -p /opt/hermes/skills/security/academic-security-tooling
COPY academic-security-tooling/SKILL.md /opt/hermes/skills/security/academic-security-tooling/SKILL.md
COPY patch-router-academic-security-tooling.py /tmp/patch-router-academic-security-tooling.py
RUN python3 /tmp/patch-router-academic-security-tooling.py \
    && rm -f /tmp/patch-router-academic-security-tooling.py

# Low-level systems security, memory-failure analysis, kernel architecture and
# EDR/XDR telemetry resilience for defensive research and secure development.
RUN mkdir -p /opt/hermes/skills/security/low-level-memory-edr-resilience
COPY low-level-memory-edr-resilience/SKILL.md /opt/hermes/skills/security/low-level-memory-edr-resilience/SKILL.md
COPY patch-router-lowlevel-memory.py /tmp/patch-router-lowlevel-memory.py
RUN python3 /tmp/patch-router-lowlevel-memory.py \
    && rm -f /tmp/patch-router-lowlevel-memory.py

# Advanced AI/ML security research, adversarial robustness, autonomous defense,
# model-assisted reverse engineering and quantum-computing-informed resilience.
RUN mkdir -p /opt/hermes/skills/security/ai-autonomous-vulnerability-resilience
COPY ai-autonomous-vulnerability-resilience/SKILL.md /opt/hermes/skills/security/ai-autonomous-vulnerability-resilience/SKILL.md
COPY patch-router-ai-resilience.py /tmp/patch-router-ai-resilience.py
RUN python3 /tmp/patch-router-ai-resilience.py \
    && rm -f /tmp/patch-router-ai-resilience.py

# Self-reflective metaprogramming, recursive feedback, dynamic context
# optimization, knowledge graphs and safe sandboxed evolution of local skills.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/evolutionary-metaprogramming-context-optimization
COPY evolutionary-metaprogramming-context-optimization/SKILL.md /opt/hermes/skills/autonomous-ai-agents/evolutionary-metaprogramming-context-optimization/SKILL.md
COPY patch-router-metaprogramming.py /tmp/patch-router-metaprogramming.py
RUN python3 /tmp/patch-router-metaprogramming.py \
    && rm -f /tmp/patch-router-metaprogramming.py

# Coherent multi-agent orchestrator for complex engineering projects: decomposes
# work into specialist roles, cross-reviews results, validates, and synthesizes.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/multi-agent-coherent-orchestrator
COPY multi-agent-coherent-orchestrator/SKILL.md /opt/hermes/skills/autonomous-ai-agents/multi-agent-coherent-orchestrator/SKILL.md
COPY patch-router-multiagent.py /tmp/patch-router-multiagent.py
RUN python3 /tmp/patch-router-multiagent.py \
    && rm -f /tmp/patch-router-multiagent.py

# Decentralized/P2P/edge compute orchestration, container portability,
# model sharding, quantization and tensor compression with zero-cost-first design.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/decentralized-serverless-compute-orchestration
COPY decentralized-serverless-compute-orchestration/SKILL.md /opt/hermes/skills/autonomous-ai-agents/decentralized-serverless-compute-orchestration/SKILL.md
COPY patch-router-decentralized-compute.py /tmp/patch-router-decentralized-compute.py
RUN python3 /tmp/patch-router-decentralized-compute.py \
    && rm -f /tmp/patch-router-decentralized-compute.py

# Local/open-model quality optimizer: behavioral knowledge distillation,
# prompt compilation, decomposition, critique and verification without paid APIs.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/knowledge-distillation-proprietary-model-mimicry
COPY knowledge-distillation-proprietary-model-mimicry/SKILL.md /opt/hermes/skills/autonomous-ai-agents/knowledge-distillation-proprietary-model-mimicry/SKILL.md
COPY patch-router-local-distillation.py /tmp/patch-router-local-distillation.py
RUN python3 /tmp/patch-router-local-distillation.py \
    && rm -f /tmp/patch-router-local-distillation.py

# Cost-aware Mixture-of-Agents controller: local-first task decomposition,
# dynamic per-subtask model routing, frontier escalation and failover.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/intelligent-infrastructure-dynamic-moa-orchestrator
COPY intelligent-infrastructure-dynamic-moa-orchestrator/SKILL.md /opt/hermes/skills/autonomous-ai-agents/intelligent-infrastructure-dynamic-moa-orchestrator/SKILL.md
COPY patch-router-dynamic-moa.py /tmp/patch-router-dynamic-moa.py
RUN python3 /tmp/patch-router-dynamic-moa.py \
    && rm -f /tmp/patch-router-dynamic-moa.py

# Safe recursive self-improvement laboratory: benchmarks, sandboxed variants,
# architecture/hyperparameter search, explicit promotion gates and rollback.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/auto-evolucao-recursiva
COPY auto-evolucao-recursiva/SKILL.md /opt/hermes/skills/autonomous-ai-agents/auto-evolucao-recursiva/SKILL.md

RUN mkdir -p /opt/hermes/skills/cloud/global-distributed-ai-cloud-architecture
COPY global-distributed-ai-cloud-architecture/SKILL.md /opt/hermes/skills/cloud/global-distributed-ai-cloud-architecture/SKILL.md

RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/global-decentralized-inference-orchestrator
COPY global-decentralized-inference-orchestrator/SKILL.md /opt/hermes/skills/autonomous-ai-agents/global-decentralized-inference-orchestrator/SKILL.md

# Encrypted memory sync: client-side AES-256-GCM before Supabase, no public memory port.
RUN mkdir -p /opt/hermes/skills/data-management/hermes-encrypted-cloud-memory-sync
COPY hermes-encrypted-cloud-memory-sync/SKILL.md /opt/hermes/skills/data-management/hermes-encrypted-cloud-memory-sync/SKILL.md
COPY hermes-memory-sync.py /usr/local/bin/hermes-memory-sync
COPY hermes-memory-sync-run.sh /etc/services.d/hermes-memory-sync/run
RUN chmod 0755 /usr/local/bin/hermes-memory-sync /etc/services.d/hermes-memory-sync/run \
    && /usr/bin/python3 -m py_compile /usr/local/bin/hermes-memory-sync


# Optional, bounded HTTPS inference router; fails closed until its owner explicitly enables providers.
RUN mkdir -p /opt/hermes/skills/autonomous-ai-agents/hermes-worldwide-model-router
COPY hermes-global-model-router.py /usr/local/bin/hermes-global-model-router
COPY hermes-worldwide-model-router/SKILL.md /opt/hermes/skills/autonomous-ai-agents/hermes-worldwide-model-router/SKILL.md
RUN /usr/bin/python3 -m py_compile /usr/local/bin/hermes-global-model-router
RUN chmod 0755 /usr/local/bin/hermes-global-model-router


# Re-copy the original custom bundle only for an exact build-time count.
COPY custom-skills.tar.gz.b64 /tmp/custom-skills-audit.b64
RUN base64 -d /tmp/custom-skills-audit.b64 | tar -tzf - | grep -c 'SKILL.md' > /opt/hermes/hermes-nosso-bundle-count.txt \
    && rm -f /tmp/custom-skills-audit.b64

# Verify every repository-defined Hermes Nosso skill is present in the image.
RUN test -f /opt/hermes/skills/autonomous-ai-agents/hermes-nosso-router/SKILL.md \
    && test -f /opt/hermes/skills/software-development/hermes-fullstack-builder/SKILL.md \
    && test -f /opt/hermes/skills/machine-learning/stable-diffusion-prompt-engineer/SKILL.md \
    && test -f /opt/hermes/skills/security/sandbox-security-reverse-engineering/SKILL.md \
    && test -f /opt/hermes/skills/security/defensive-security-crypto-hardening/SKILL.md \
    && test -f /opt/hermes/skills/security/red-team-ctf-academic/SKILL.md \
    && test -f /opt/hermes/skills/security/academic-security-tooling/SKILL.md \
    && test -f /opt/hermes/skills/security/low-level-memory-edr-resilience/SKILL.md \
    && test -f /opt/hermes/skills/security/ai-autonomous-vulnerability-resilience/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/evolutionary-metaprogramming-context-optimization/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/multi-agent-coherent-orchestrator/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/decentralized-serverless-compute-orchestration/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/knowledge-distillation-proprietary-model-mimicry/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/intelligent-infrastructure-dynamic-moa-orchestrator/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/auto-evolucao-recursiva/SKILL.md \
    && test -f /opt/hermes/skills/cloud/global-distributed-ai-cloud-architecture/SKILL.md \
    && test -f /opt/hermes/skills/autonomous-ai-agents/global-decentralized-inference-orchestrator/SKILL.md \
    && find /opt/hermes/skills -type f -name SKILL.md | wc -l

# Lightweight S3 client for private Railway bucket backups plus the distro
# cryptography library used only to derive the private executor SSH identity.
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends python3-boto3 python3-cryptography python3-yaml git curl jq socat \
    && rm -rf /var/lib/apt/lists/*

# Vercel Sandbox SDK is lazy-installed by Hermes itself through its managed
# package manager when the vercel_sandbox backend is first used.

# Make the Hermes CLI available from every runtime shell/exec context.
RUN test -x /opt/hermes/.venv/bin/hermes \
    && ln -sf /opt/hermes/.venv/bin/hermes /usr/local/bin/hermes

# Defensive compatibility layer for the current upstream dashboard.
COPY patch-hermes-web-runtime.py /tmp/patch-hermes-web-runtime.py
COPY patch-hermes-video-runtime.py /tmp/patch-hermes-video-runtime.py
COPY patch-dashboard-stability.py /tmp/patch-dashboard-stability.py
RUN python3 /tmp/patch-hermes-web-runtime.py \
    && python3 /tmp/patch-hermes-video-runtime.py \
    && python3 /tmp/patch-dashboard-stability.py \
    && rm -f /tmp/patch-hermes-web-runtime.py /tmp/patch-hermes-video-runtime.py /tmp/patch-dashboard-stability.py

COPY railway-entrypoint.sh /usr/local/bin/hermes-railway-entrypoint
COPY patch-entrypoint-stability.py /tmp/patch-entrypoint-stability.py
RUN python3 /tmp/patch-entrypoint-stability.py \
    && rm -f /tmp/patch-entrypoint-stability.py

# Repair private config/backup ownership. Prefer Vercel Sandbox when its
# credentials exist; otherwise use the dedicated private Railway executor.
COPY hermes-storage-permissions.sh /etc/cont-init.d/00-hermes-storage-permissions
COPY hermes-vercel-sandbox.sh /etc/cont-init.d/01-hermes-vercel-sandbox
COPY hermes-private-executor.sh /etc/cont-init.d/02-hermes-private-executor

# Keep only the periodic bucket backup as a resident helper. Development-only
# smoke, synthetic cron validation/cleanup, and plugin doctor supervisors are
# intentionally omitted in production to keep the 1 GB Railway memory budget
# available to the gateway and active agent request.
COPY bucket-backup.py /usr/local/bin/hermes-bucket-backup
COPY bucket-backup-run.sh /etc/services.d/hermes-bucket-backup/run

RUN chmod +x /usr/local/bin/hermes-railway-entrypoint \
    /usr/local/bin/hermes-bucket-backup \
    /etc/cont-init.d/00-hermes-storage-permissions \
    /etc/cont-init.d/01-hermes-vercel-sandbox \
    /etc/cont-init.d/02-hermes-private-executor \
    /etc/services.d/hermes-bucket-backup/run

# Render / Hugging Face Spaces: start the lightweight HTTP server directly.
# It uses the existing Hermes Web chat UI and official global inference router.
# The full Hermes/s6 image is preserved but is not started in lightweight mode.
USER root
COPY hermes-simple.py /opt/hermes-render/hermes-simple.py
COPY hermes-render-light-web.py /usr/local/bin/hermes-render-light-web
COPY hermes-light-agent.py /usr/local/bin/hermes-light-agent
COPY hermes-spaces-port-run.sh /hermes-spaces-port-run.sh
RUN chmod 0755 /hermes-spaces-port-run.sh /usr/local/bin/hermes-render-light-web \
    && /bin/bash -n /hermes-spaces-port-run.sh \
    && /usr/bin/python3 -m py_compile /usr/local/bin/hermes-render-light-web /usr/local/bin/hermes-light-agent /opt/hermes-render/hermes-simple.py
ENV PORT=8080
EXPOSE 8080
ENTRYPOINT []
CMD ["/bin/bash", "/hermes-spaces-port-run.sh"]
