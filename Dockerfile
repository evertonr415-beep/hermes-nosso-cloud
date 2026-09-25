FROM nousresearch/hermes-agent:latest

USER root

ENV NPM_CONFIG_CACHE=/tmp/npm-cache

# Add only Hermes Nosso skills that are not already bundled upstream.
COPY custom-skills.tar.gz.b64 /tmp/custom-skills.tar.gz.b64
RUN base64 -d /tmp/custom-skills.tar.gz.b64 | tar -xz -C /opt/hermes/skills \
    && rm -f /tmp/custom-skills.tar.gz.b64

# Lightweight S3 client for private Railway bucket backups.
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends python3-boto3 && rm -rf /var/lib/apt/lists/*

COPY railway-entrypoint.sh /usr/local/bin/hermes-railway-entrypoint
COPY smoke-tests.sh /usr/local/bin/hermes-smoke-tests
COPY runtime-smoke-run.sh /etc/services.d/hermes-runtime-smoke/run
COPY cron-validation-run.sh /etc/services.d/hermes-cron-validation/run
COPY bucket-backup.py /usr/local/bin/hermes-bucket-backup
COPY bucket-backup-run.sh /etc/services.d/hermes-bucket-backup/run

RUN chmod +x /usr/local/bin/hermes-railway-entrypoint \
    /usr/local/bin/hermes-smoke-tests \
    /usr/local/bin/hermes-bucket-backup \
    /etc/services.d/hermes-runtime-smoke/run \
    /etc/services.d/hermes-cron-validation/run \
    /etc/services.d/hermes-bucket-backup/run

ENTRYPOINT ["/usr/local/bin/hermes-railway-entrypoint"]
CMD ["sleep", "infinity"]
