FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openssh-client autossh python3 python3-websockets iproute2 \
    && rm -rf /var/lib/apt/lists/*
COPY apps.py /apps.py
COPY entrypoint.sh /entrypoint.sh
CMD ["bash", "/entrypoint.sh"]
