FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openssh-server nginx apache2-utils openssl iproute2 \
    && rm -rf /var/lib/apt/lists/* && rm -f /etc/nginx/sites-enabled/default
# "admin" logs in with a key. "tunnel" is the locked-down account devices use.
RUN useradd -m -s /bin/bash admin && useradd -m -s /usr/sbin/nologin tunnel
COPY entrypoint.sh /entrypoint.sh
CMD ["bash", "/entrypoint.sh"]
