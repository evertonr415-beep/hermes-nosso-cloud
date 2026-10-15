FROM node:24-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install Chromium runtime dependencies directly. agent-browser's --with-deps
# helper invokes sudo, which is intentionally absent in slim containers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 ca-certificates \
       libxcb-shm0 libx11-xcb1 libx11-6 libxcb1 libxext6 libxrandr2 \
       libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 \
       libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 libatk1.0-0 \
       libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libxrender1 \
       libasound2 libfreetype6 libfontconfig1 libdbus-1-3 libnss3 \
       libnss3-tools libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
       libatspi2.0-0 libcups2 libxshmfence1 libgbm1 \
       fonts-noto-color-emoji fonts-noto-cjk fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global agent-browser@0.39.0 \
    && agent-browser install

COPY server.py /app/server.py
ENV PORT=8080
EXPOSE 8080
CMD ["python3", "/app/server.py"]
