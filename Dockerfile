FROM nousresearch/hermes-agent:latest

USER root

ENV NPM_CONFIG_CACHE=/tmp/npm-cache
ENV PATH="/opt/hermes/.venv/bin:/usr/local/bin:/usr/bin:/bin"
# The old entrypoint bootstrap targets six plugins and calls a dashboard helper
# signature that is no longer valid on Hermes 0.21.x. Curated plugins are
# persisted on /opt/data; production no longer keeps a bootstrap supervisor
# resident after startup.
ENV HERMES_CURATED_PLUGINS_BOOTSTRAP=0

# Add only Hermes Nosso skills that are not already bundled upstream.
COPY custom-skills.tar.gz.b64 /tmp/custom-skills.tar.gz.b64
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

# Lightweight S3 client for private Railway bucket backups plus the distro
# cryptography library used only to derive the private executor SSH identity.
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends python3-boto3 python3-cryptography git curl jq \
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

ENTRYPOINT ["/usr/local/bin/hermes-railway-entrypoint"]
CMD ["sleep", "infinity"]
