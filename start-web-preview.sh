#!/bin/sh
set -eu
echo "[hermes-web] validating nginx configuration"
nginx -t
echo "[hermes-web] starting nginx on port 9119"
exec nginx -g 'daemon off;'
