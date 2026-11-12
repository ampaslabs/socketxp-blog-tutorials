#!/usr/bin/env bash
# Creates the Mosquitto password files and the gateway bridge config from .env.
# Safe to re-run after changing passwords; then `docker compose restart mosquitto gateway`.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found. Run: cp .env.example .env  (and change the passwords)" >&2
  exit 1
fi
set -a; . ./.env; set +a

IMAGE=eclipse-mosquitto:2

# Central broker: one entry per client. Demo devices share MQTT_DEVICE_PASSWORD.
docker run --rm \
  -e TELEGRAF="$MQTT_TELEGRAF_PASSWORD" -e WATCHDOG="$MQTT_WATCHDOG_PASSWORD" \
  -e DEVICE="$MQTT_DEVICE_PASSWORD" -e GATEWAY="$MQTT_GATEWAY_PASSWORD" \
  -v "$PWD/mosquitto/config:/mosquitto/config" "$IMAGE" sh -c '
    f=/mosquitto/config/passwd
    rm -f $f
    mosquitto_passwd -c -b $f telegraf "$TELEGRAF"
    mosquitto_passwd -b $f watchdog "$WATCHDOG"
    for d in device01 device02 device03; do mosquitto_passwd -b $f $d "$DEVICE"; done
    mosquitto_passwd -b $f site3-gateway "$GATEWAY"
    chmod 0700 $f /mosquitto/config/acl'

# Gateway broker (Raspberry Pi demo): local ESP32 credentials
docker run --rm -e DEVICE="$MQTT_DEVICE_PASSWORD" \
  -v "$PWD/gateway:/mosquitto/config" "$IMAGE" sh -c '
    f=/mosquitto/config/passwd
    rm -f $f
    mosquitto_passwd -c -b $f esp32-node-01 "$DEVICE"
    chmod 0700 $f'

# Gateway bridge config with the bridge password filled in
sed "s|__GATEWAY_PASSWORD__|$MQTT_GATEWAY_PASSWORD|" gateway/mosquitto.conf.template > gateway/mosquitto.conf

echo "Done. Start the stack with: docker compose up -d"
