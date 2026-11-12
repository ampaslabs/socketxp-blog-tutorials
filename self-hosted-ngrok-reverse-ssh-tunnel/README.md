# Self-Hosted ngrok With a Reverse SSH Tunnel and Nginx

Config files and a Docker test lab for exposing a web app on a home or IoT device at a public HTTPS URL on your own domain. You'll get something like `https://app.example.com`, like ngrok but with your own VPS, a reverse SSH tunnel, Nginx and Let's Encrypt.

📖 **Full tutorial:** [Build a Self-Hosted ngrok With a Reverse SSH Tunnel and Nginx](https://www.socketxp.com/iot/self-hosted-ngrok-reverse-ssh-tunnel-nginx/)

```
Browser ──HTTPS──▶ Nginx on VPS :443 ──▶ 127.0.0.1:8080 on VPS ──reverse SSH tunnel──▶ device ──▶ localhost:3000
```

- The tunnel port listens on the VPS loopback address only (`GatewayPorts no`). Nginx is the only public entry point.
- The tunnel account has no shell, can only open remote forwards, and each device key can only open its own ports.
- A single wildcard Nginx server block routes `*.example.com` to tunnel ports through a `map`, with optional per-subdomain basic auth.

## What's in here

| Path | What it is |
|---|---|
| `configs/sshd/10-tunnel.conf` | Hardened sshd drop-in for the VPS |
| `configs/ssh/authorized_keys.example` | Per-device key restrictions for the `tunnel` user |
| `configs/nginx/app.example.com.conf` | One server block per app (run certbot on it) |
| `configs/nginx/tunnels.example.com.conf` | One wildcard server block for every app, with a port `map` |
| `configs/systemd/reverse-tunnel.service` | Keeps the tunnel running on the device |
| `docker-compose.yml`, `lab/` | A test lab: VPS, two devices and an outside client |
| `test.sh` | Runs 27 checks against the lab and prints PASS/FAIL |

The lab mounts the files in `configs/` directly, so the tests run against exactly what you copy to your servers.

## Run the test lab

You need Docker with Compose v2.

```bash
git clone --depth 1 https://github.com/ampaslabs/socketxp-blog-tutorials.git
cd socketxp-blog-tutorials/self-hosted-ngrok-reverse-ssh-tunnel
docker compose up -d --build
./test.sh
docker compose down -v      # remove the lab and its keys
```

The lab runs Ubuntu 24.04 (OpenSSH 9.6, Nginx 1.24) and contains:

| Container | Role |
|---|---|
| `vps` | sshd and Nginx, playing `tunnel.example.com` and `*.example.com` |
| `device1` | device-01: web app on `:3000` and a second app on `:8000`, published as `app.example.com` and `shop.example.com` through one key |
| `device2` | device-02: a dashboard with WebSockets on `:3001`, published as `grafana.example.com` behind basic auth (`demo` / `s3cret`) |
| `client` | An outside machine on the internet, used by `test.sh` |

Expected output ends with:

```
27 passed, 0 failed
```

To see a test fail, set `GatewayPorts yes` in `configs/sshd/10-tunnel.conf` and run `docker compose restart vps device1 device2 && ./test.sh`. T03 and T04 fail, because the tunnel ports are now open to the internet.

### Lab-only shortcuts

These exist only to make the lab self-contained. Don't copy them to a real server.

- SSH keys are generated fresh into a Docker volume on first start.
- A self-signed `*.example.com` certificate stands in for Let's Encrypt.
- Devices trust the VPS host key on first contact. On a real device, compare the fingerprint with `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on the VPS.
- `root` gets the admin key so the test can prove root logins are refused.
- Devices use `autossh` with `ServerAliveInterval=10` so recovery tests run faster. The article's systemd unit uses 30.

### Not covered by the lab

- Real Let's Encrypt certificates (`certbot --nginx`, or DNS-01 for wildcards), which need a real public domain
- `ufw` and `fail2ban` on the VPS
- The systemd unit, which was tested separately in a systemd container

## Use it on real servers

Follow the [tutorial](https://www.socketxp.com/iot/self-hosted-ngrok-reverse-ssh-tunnel-nginx/) step by step. In short:

1. Point `tunnel.example.com` and `*.example.com` at your VPS.
2. Copy `configs/sshd/10-tunnel.conf` to `/etc/ssh/sshd_config.d/`, then run `sudo sshd -t && sudo systemctl reload ssh` while keeping an existing session open.
3. Create the `tunnel` user and add device keys as in `configs/ssh/authorized_keys.example`.
4. Copy an Nginx config, get certificates with certbot, and reload Nginx.
5. Install `configs/systemd/reverse-tunnel.service` on each device.

## Need this for a whole device fleet?

Every new app here means a new port, a new key entry and a new `map` line, edited by hand on the VPS. [SocketXP](https://www.socketxp.com/iot-remote-access/) gives each device a public HTTPS URL, or private SSH/VNC access with no public port, through one command (`socketxp connect http://localhost:3000`), plus a device dashboard and OTA updates. It can also be self-hosted, including a free Community edition for non-commercial use (up to 100 devices).

## License

MIT. See [LICENSE](../LICENSE).
