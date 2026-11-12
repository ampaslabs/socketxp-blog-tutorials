#!/bin/bash
set -e
install_keys() {  # user, source file
  install -d -m 700 -o "$1" -g "$1" "/home/$1/.ssh"
  install -m 600 -o "$1" -g "$1" "$2" "/home/$1/.ssh/authorized_keys"
}
install_keys tunnel /keys/tunnel.authorized_keys
install_keys admin  /keys/admin.pub
# Lab only: give root the admin key, so test.sh can prove root logins are refused.
install -d -m 700 /root/.ssh && install -m 600 /keys/admin.pub /root/.ssh/authorized_keys

# Lab only: a self-signed wildcard cert stands in for Let's Encrypt.
C=/etc/letsencrypt/live/example.com
if [ ! -f $C/fullchain.pem ]; then
  mkdir -p $C
  openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=*.example.com" \
    -addext "subjectAltName=DNS:*.example.com,DNS:example.com" \
    -keyout $C/privkey.pem -out $C/fullchain.pem 2>/dev/null
fi
htpasswd -bc /etc/nginx/.htpasswd demo s3cret 2>/dev/null

mkdir -p /run/sshd
sshd -t
/usr/sbin/sshd -E /var/log/sshd.log -o LogLevel=VERBOSE
nginx -t
exec nginx -g 'daemon off;'
