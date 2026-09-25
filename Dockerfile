FROM nousresearch/hermes-agent:latest

USER root

# Add only Hermes Nosso skills that are not already bundled upstream.
COPY custom-skills.tar.gz.b64 /tmp/custom-skills.tar.gz.b64
RUN base64 -d /tmp/custom-skills.tar.gz.b64 | tar -xz -C /opt/hermes/skills \
    && rm -f /tmp/custom-skills.tar.gz.b64

COPY railway-entrypoint.sh /usr/local/bin/hermes-railway-entrypoint
RUN chmod +x /usr/local/bin/hermes-railway-entrypoint

ENTRYPOINT ["/usr/local/bin/hermes-railway-entrypoint"]
CMD ["sleep", "infinity"]
