"""Offline watchdog for MQTT IoT devices.

Signals:
  * Last Will "offline" on fleet/{site}/{device}/status  -> connection lost
  * no heartbeat/telemetry for MISSED_BEATS intervals    -> device hung or gone
  * uptime lower than the previous value                 -> device rebooted
Alerts wait GRACE seconds, and are grouped into one site-outage alert when most
devices at a site go down together. Alerts go to fleet/.../alerts and WEBHOOK_URL.
"""
import json
import os
import threading
import time
import urllib.request
from collections import defaultdict

import paho.mqtt.client as mqtt

GRACE = int(os.getenv("GRACE", "60"))   # seconds a problem must last before we alert
MISSED_BEATS = 3                         # heartbeats missed before a device counts as stale
SITE_OUTAGE = 0.5                        # share of a site's devices down at once = site outage
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # optional: Slack, Teams or any HTTP endpoint

devices = {}          # "fleet/site/dev" -> state dict
lock = threading.Lock()


def alert(client, topic, state, reason):
    event = {"target": topic, "state": state, "reason": reason, "ts": int(time.time())}
    client.publish(f"{topic}/alerts", json.dumps(event), qos=1)
    print("ALERT", event, flush=True)
    if WEBHOOK_URL:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps({"text": f"{topic} is {state}: {reason}"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except OSError as err:
            print("webhook failed:", err, flush=True)


def device(base):
    return devices.setdefault(base, {
        "last_beat": time.time(), "interval": 30, "uptime": None,
        "down_since": None, "alerted": False,
    })


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe([
        ("fleet/+/+/heartbeat", 0),
        ("fleet/+/+/telemetry", 0),   # telemetry on a fixed schedule doubles as the heartbeat
        ("fleet/+/+/status", 1),
    ])


def on_message(client, userdata, msg):
    base, kind = msg.topic.rsplit("/", 1)
    now = time.time()
    with lock:
        d = device(base)
        if kind in ("heartbeat", "telemetry"):
            try:
                beat = json.loads(msg.payload)
            except ValueError:
                return
            uptime = beat.get("uptime")
            if uptime is not None and d["uptime"] is not None and uptime + 5 < d["uptime"]:
                alert(client, base, "rebooted", f"uptime reset to {uptime}s")
            d.update(last_beat=now, uptime=uptime, interval=beat.get("interval", 30))
            if d["alerted"]:
                alert(client, base, "recovered", "heartbeat resumed")
            d.update(down_since=None, alerted=False)
        elif kind == "status" and msg.payload == b"offline" and d["down_since"] is None:
            d["down_since"] = now   # pending; confirmed by the check loop after GRACE


def check(client):
    now = time.time()
    by_site = defaultdict(list)
    with lock:
        for base, d in devices.items():
            stale = now - d["last_beat"] > MISSED_BEATS * d["interval"]
            if stale and d["down_since"] is None:
                d["down_since"] = now
            down = d["down_since"] is not None and now - d["down_since"] >= GRACE
            by_site[base.rsplit("/", 1)[0]].append((base, d, down))

        for site, members in by_site.items():
            new = [(b, d) for b, d, down in members if down and not d["alerted"]]
            if not new:
                continue
            down_count = sum(1 for _, _, down in members if down)
            if len(members) >= 4 and down_count / len(members) >= SITE_OUTAGE:
                alert(client, site, "site-outage", f"{down_count}/{len(members)} devices down")
            else:
                for base, _ in new:
                    alert(client, base, "offline", "no heartbeat or Last Will received")
            for _, d in new:
                d["alerted"] = True


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="offline-watchdog")
client.username_pw_set("watchdog", os.environ["MQTT_PASSWORD"])
client.on_connect = on_connect
client.on_message = on_message
client.connect(os.getenv("MQTT_HOST", "127.0.0.1"), 1883, keepalive=60)
client.loop_start()

while True:
    check(client)
    time.sleep(10)
