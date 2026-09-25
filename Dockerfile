FROM nousresearch/hermes-agent:latest

USER root
COPY railway-entrypoint.sh /usr/local/bin/hermes-railway-entrypoint
RUN chmod +x /usr/local/bin/hermes-railway-entrypoint

ENTRYPOINT ["/usr/local/bin/hermes-railway-entrypoint"]
CMD ["sleep", "infinity"]
