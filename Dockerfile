FROM nousresearch/hermes-agent:latest

USER root

# Add only Hermes Nosso skills that are not already bundled upstream.
COPY custom-skills.tar.gz.b64 /tmp/custom-skills.tar.gz.b64
RUN base64 -d /tmp/custom-skills.tar.gz.b64 | tar -xz -C /opt/hermes/skills \
    && rm -f /tmp/custom-skills.tar.gz.b64

COPY railway-entrypoint.sh /usr/local/bin/hermes-railway-entrypoint
COPY smoke-tests.sh /usr/local/bin/hermes-smoke-tests
COPY runtime-smoke-run.sh /etc/services.d/hermes-runtime-smoke/run \
    /etc/services.d/hermes-cron-validation/run
COPY cron-validation-run.sh /etc/services.d/hermes-cron-validation/run
RUN chmod +x /usr/local/bin/hermes-railway-entrypoint \
    /usr/local/bin/hermes-smoke-tests \
    /etc/services.d/hermes-runtime-smoke/run

ENTRYPOINT ["/usr/local/bin/hermes-railway-entrypoint"]
CMD ["sleep", "infinity"]
