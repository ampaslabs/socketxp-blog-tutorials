FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      curl openssh-client netcat-openbsd python3 python3-websockets ca-certificates \
    && rm -rf /var/lib/apt/lists/*
