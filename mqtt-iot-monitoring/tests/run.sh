#!/usr/bin/env bash
# Run a failure scenario against the running stack and show what the broker published.
#   ./tests/run.sh hung | reboot | site | willdelay
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
scenario=${1:?usage: tests/run.sh hung|reboot|site|willdelay}

# Test devices sim01..sim04 (added to the broker's password file, then reloaded)
docker compose exec -T -e P="$MQTT_DEVICE_PASSWORD" mosquitto sh -c '
  for d in sim01 sim02 sim03 sim04; do mosquitto_passwd -b /mosquitto/config/passwd $d "$P"; done
  kill -HUP 1'

# Record status and alert messages with timestamps while the scenario runs
docker compose exec -T -d mosquitto sh -c "mosquitto_sub -u watchdog -P '$MQTT_WATCHDOG_PASSWORD' \
  -t 'fleet/site9/#' -t 'fleet/+/+/alerts' -t 'fleet/+/alerts' -F '%I %t %p' > /tmp/$scenario.log"

docker compose run --rm --no-deps -v "$PWD/tests:/tests" -e MQTT_HOST=mosquitto \
  -e MQTT_PASSWORD="$MQTT_DEVICE_PASSWORD" device01 python -u /tests/scenarios.py "$scenario"

echo "--- broker messages (status, alerts) ---"
docker compose exec -T mosquitto sh -c "pkill mosquitto_sub; grep -v '/telemetry ' /tmp/$scenario.log"
