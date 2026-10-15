FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global agent-browser@0.39.0 \
    && agent-browser install --with-deps

COPY server.py /app/server.py
ENV PORT=8080
EXPOSE 8080
CMD ["python3", "/app/server.py"]
