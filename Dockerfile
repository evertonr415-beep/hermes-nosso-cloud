FROM nousresearch/hermes-agent:latest

USER root

ENV NPM_CONFIG_CACHE=/tmp/npm-cache
ENV PATH="/opt/hermes/.venv/bin:/usr/local/bin:/usr/bin:/bin"

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

# Lightweight S3 client for private Railway bucket backups.
# git/curl/jq are explicit full-stack execution dependencies; node/npm are provided by the Hermes image.
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends python3-boto3 git curl jq \
    && rm -rf /var/lib/apt/lists/*

# Make the Hermes CLI available from every runtime shell/exec context.
RUN test -x /opt/hermes/.venv/bin/hermes \
    && ln -sf /opt/hermes/.venv/bin/hermes /usr/local/bin/hermes

# Defensive compatibility layer for the current upstream dashboard.
# It normalizes session metadata at the HTTP boundary and clears only stale
# browser-side chat/session state once; it never mutates state.db.
COPY patch-hermes-web-runtime.py /tmp/patch-hermes-web-runtime.py
COPY patch-hermes-video-runtime.py /tmp/patch-hermes-video-runtime.py
RUN python3 /tmp/patch-hermes-web-runtime.py \
    && python3 /tmp/patch-hermes-video-runtime.py \
    && rm -f /tmp/patch-hermes-web-runtime.py /tmp/patch-hermes-video-runtime.py

COPY railway-entrypoint.sh /usr/local/bin/hermes-railway-entrypoint
COPY smoke-tests.sh /usr/local/bin/hermes-smoke-tests
COPY runtime-smoke-run.sh /etc/services.d/hermes-runtime-smoke/run
COPY cron-validation-run.sh /etc/services.d/hermes-cron-validation/run
COPY bucket-backup.py /usr/local/bin/hermes-bucket-backup
COPY bucket-backup-run.sh /etc/services.d/hermes-bucket-backup/run
COPY plugin-bootstrap-run.sh /etc/services.d/hermes-plugin-bootstrap/run

RUN chmod +x /usr/local/bin/hermes-railway-entrypoint \
    /usr/local/bin/hermes-smoke-tests \
    /usr/local/bin/hermes-bucket-backup \
    /etc/services.d/hermes-runtime-smoke/run \
    /etc/services.d/hermes-cron-validation/run \
    /etc/services.d/hermes-bucket-backup/run \
    /etc/services.d/hermes-plugin-bootstrap/run

ENTRYPOINT ["/usr/local/bin/hermes-railway-entrypoint"]
CMD ["sleep", "infinity"]
