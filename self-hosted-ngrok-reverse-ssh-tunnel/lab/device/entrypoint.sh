#!/bin/bash
python3 /apps.py &

mkdir -p ~/.ssh && chmod 700 ~/.ssh
install -m 600 "/keys/$KEY_NAME" ~/.ssh/id_ed25519

# Lab only: trust the VPS host key on first contact. On a real device, compare
# this fingerprint with "ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub" on the VPS.
until ssh-keyscan -t ed25519 tunnel.example.com > ~/.ssh/known_hosts 2>/dev/null && [ -s ~/.ssh/known_hosts ]; do sleep 1; done

# Same options as the article's systemd unit, with a shorter ServerAliveInterval
# so the lab recovers faster. AUTOSSH_GATETIME=0 keeps
# retrying even if the very first connection fails.
export AUTOSSH_GATETIME=0
exec autossh -M 0 -NT \
  -o ServerAliveInterval=10 -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes \
  $TUNNELS tunnel@tunnel.example.com
