FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server ca-certificates git curl wget jq rsync zip unzip procps lsof \
    build-essential python3 python3-pip python3-venv nodejs npm sudo \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash -u 10001 hermes \
    && mkdir -p /run/sshd /workspace /home/hermes/.ssh \
    && chown -R hermes:hermes /workspace /home/hermes/.ssh \
    && chmod 700 /home/hermes/.ssh \
    && printf 'hermes ALL=(ALL) NOPASSWD:ALL\n' >/etc/sudoers.d/hermes \
    && chmod 440 /etc/sudoers.d/hermes

COPY entrypoint.sh /usr/local/bin/hermes-executor-entrypoint
RUN chmod +x /usr/local/bin/hermes-executor-entrypoint

EXPOSE 2222
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/hermes-executor-entrypoint"]
