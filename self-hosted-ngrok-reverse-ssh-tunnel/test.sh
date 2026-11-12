#!/usr/bin/env bash
# Runs every check from the article against the Docker lab and prints PASS/FAIL.
# Usage: docker compose up -d --build && ./test.sh
cd "$(dirname "$0")"

PASS=0; FAIL=0; ROWS=()
x() { docker compose exec -T "$@" 2>&1; }
check() {  # id, description, output, expected (extended regex)
  if grep -qE -- "$4" <<<"$3"; then r=PASS; PASS=$((PASS+1)); else r=FAIL; FAIL=$((FAIL+1)); fi
  ROWS+=("$(printf '%-4s %-4s %s' "$1" "$r" "$2")")
  [ "$r" = FAIL ] && printf '     got: %s\n' "$(head -c 300 <<<"$3" | tr '\n' ' ')" >&2
}
code() { x client curl -sk -o /dev/null -w '%{http_code}' "$@"; }
ws() {  # url, user:pass
  x client python3 - "$1" "$2" <<'PY'
import asyncio, base64, ssl, sys, websockets
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
h = {"Authorization": "Basic " + base64.b64encode(sys.argv[2].encode()).decode()}
async def go():
    async with websockets.connect(sys.argv[1], ssl=ctx, extra_headers=h) as s:
        await s.send("hello"); print(await s.recv())
asyncio.run(go())
PY
}
admin_ssh() { x client ssh -i /root/admin_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes "$@"; }
dev_ssh() { x "$1" timeout 10 ssh -o BatchMode=yes "${@:2}"; }

echo "Waiting for tunnels..."
for i in $(seq 1 30); do
  [ "$(x vps ss -tln | grep -cE '127.0.0.1:808[012]')" = 3 ] && break; sleep 2
done
VPS_IP=$(x vps hostname -i | awk '{print $1}')
x client install -m 600 /keys/admin /root/admin_key >/dev/null  # ssh rejects keys readable by others

# --- VPS and sshd hardening ---
check T01 "sshd config is valid (sshd -t)"                    "$(x vps sshd -t && echo ok)" '^ok$'
check T02 "Nginx config is valid (nginx -t)"                  "$(x vps nginx -t)" 'test is successful'
check T03 "Tunnel ports bound to 127.0.0.1 only"              "$(x vps ss -tln | grep -E ':808[0-9]' | awk '{print $4}' | sort | tr '\n' ' ')" '^127.0.0.1:8080 127.0.0.1:8081 127.0.0.1:8082 $'
check T04 "Tunnel port not reachable from the internet"       "$(x client nc -zv -w 3 tunnel.example.com 8080)" 'refused|timed out'
check T05 "Password logins refused"                           "$(x client ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PubkeyAuthentication=no -o PreferredAuthentications=password -o NumberOfPasswordPrompts=0 admin@tunnel.example.com true)" 'Permission denied \(publickey\)'
check T06 "Root login refused, even with a valid key"         "$(admin_ssh root@tunnel.example.com true; x vps grep -c 'ROOT LOGIN REFUSED' /var/log/sshd.log)" '^[1-9][0-9]*$'
check T07 "Admin can still log in with a key"                 "$(admin_ssh admin@tunnel.example.com echo admin-ok)" 'admin-ok'
check T08 "Tunnel user gets no shell"                         "$(dev_ssh device1 tunnel@tunnel.example.com id)" 'This account is currently not available'
check T09 "Tunnel user can't use -L to reach VPS services"    "$(x device1 bash -c 'timeout 6 ssh -NT -o BatchMode=yes -L 127.0.0.1:9999:127.0.0.1:22 tunnel@tunnel.example.com & sleep 3; timeout 2 bash -c "exec 3<>/dev/tcp/127.0.0.1/9999; head -c 20 <&3" || true; wait')" 'administratively prohibited'
check T10 "Port not in PermitListen is refused"               "$(dev_ssh device2 -NT -o ExitOnForwardFailure=yes -R 9000:localhost:3001 tunnel@tunnel.example.com)" 'remote port forwarding failed for listen port 9000'
check T11 "Device pins the VPS host key (unknown key refused)" "$(dev_ssh device1 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/dev/null tunnel@tunnel.example.com)" 'Host key verification failed'

# --- Public URLs through Nginx ---
check T12 "https://app.example.com reaches device-01 app"     "$(x client curl -sk https://app.example.com/)" 'Hello from device-01 app'
check T13 "HTTP redirects to HTTPS"                           "$(x client curl -s -o /dev/null -w '%{http_code} %{redirect_url}' http://app.example.com/x)" '^301 https://app.example.com/x$'
check T14 "Paths and query strings pass through"              "$(x client curl -sk 'https://app.example.com/sub/page.txt?a=1&b=2')" 'deep path ok'
check T15 "One key, two ports: shop.example.com on device-01" "$(x client curl -sk https://shop.example.com/)" 'Hello from device-01 shop'
check T16 "app.example.com has no password prompt"            "$(code https://app.example.com/)" '^200$'
check T17 "grafana.example.com without password: 401"         "$(code https://grafana.example.com/)" '^401$'
check T18 "grafana.example.com with password: 200"            "$(x client curl -sk -u demo:s3cret https://grafana.example.com/)" 'Hello from device-02 dashboard'
check T19 "WebSocket through Nginx and the tunnel"            "$(ws wss://grafana.example.com/ demo:s3cret)" 'device-02 echo: hello'
check T20 "WebSocket without password: 401"                   "$(ws wss://grafana.example.com/ demo:wrong)" '401'
check T21 "Unknown subdomain: 404"                            "$(code https://unknown.example.com/)" '^404$'
check T22 "Bare IP address: 404"                              "$(code https://$VPS_IP/)" '^404$'
check T23 "Forged Host header (localhost): 404"               "$(code -H 'Host: localhost' https://$VPS_IP/)" '^404$'

# --- Failures and recovery ---
docker compose stop -t 2 device1 >/dev/null 2>&1; sleep 2
check T24 "device-01 offline: app.example.com returns 502"    "$(code https://app.example.com/)" '^502$'
check T25 "device-01 offline: device-02 still works"          "$(x client curl -sk -u demo:s3cret https://grafana.example.com/)" 'Hello from device-02 dashboard'
check T26 "device-02 key can't take device-01's free port"    "$(dev_ssh device2 -NT -o ExitOnForwardFailure=yes -R 8080:localhost:3001 tunnel@tunnel.example.com)" 'remote port forwarding failed for listen port 8080'
docker compose start device1 >/dev/null 2>&1
out=""; for i in $(seq 1 30); do out=$(code https://app.example.com/); [ "$out" = 200 ] && break; sleep 2; done
check T27 "device-01 back: tunnel reconnects by itself"       "$out" '^200$'

echo
printf '%s\n' "${ROWS[@]}"
echo
echo "$PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
