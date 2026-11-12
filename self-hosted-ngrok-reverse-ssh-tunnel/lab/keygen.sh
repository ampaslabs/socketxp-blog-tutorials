#!/bin/bash
# Creates lab-only SSH keys and the tunnel user's authorized_keys. Never reuse these keys.
set -e
cd /keys
[ -f device01 ] && { echo "keys already exist"; exit 0; }
for k in device01 device02 admin; do ssh-keygen -q -t ed25519 -N '' -C "$k" -f "$k"; done
{
  echo "restrict,port-forwarding,permitlisten=\"8080\",permitlisten=\"8082\" $(cat device01.pub)"
  echo "restrict,port-forwarding,permitlisten=\"8081\" $(cat device02.pub)"
} > tunnel.authorized_keys
chmod 644 /keys/*
echo "keys created"
