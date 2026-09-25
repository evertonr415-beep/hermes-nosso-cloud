#!/bin/sh
set -eu

mkdir -p /opt/data

# Keep the default Hermes gateway enabled across Railway restarts.
# The official s6 reconciler reads this before registering services.
printf '%s\n' '{"gateway_state":"running"}' > /opt/data/gateway_state.json

exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
