"""Simulates the ESP32 sketch from the blog so the gateway demo runs without hardware.

Same topics and JSON as the real firmware: a retained Last Will, one boot event with
the reset reason, then heap / heap_min / rssi / uptime every INTERVAL seconds.
heap_min drifts down slowly to imitate a memory leak on the Grafana dashboard.
"""
import json
import os
import random
import time

import paho.mqtt.client as mqtt

SITE = os.getenv("SITE", "site3")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32-node-01")
INTERVAL = int(os.getenv("INTERVAL", "30"))
FW_VERSION = "1.0.3"
BASE = f"fleet/{SITE}/{DEVICE_ID}"
STATUS = f"{BASE}/status"
started = time.time()
boot_reported = False


def on_connect(client, userdata, flags, reason_code, properties):
    global boot_reported
    if reason_code.is_failure:
        return
    client.publish(STATUS, "online", qos=1, retain=True)
    if not boot_reported:  # once per boot, after the first successful connect
        client.publish(f"{BASE}/event", json.dumps(
            {"event": "boot", "count": 1,
             "reset_reason": random.choice(["power_on", "brownout"]), "fw": FW_VERSION}),
            qos=1)  # QoS 1: the gateway queues it if its bridge isn't connected yet
        boot_reported = True


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
client.username_pw_set(DEVICE_ID, os.environ["MQTT_PASSWORD"])
client.will_set(STATUS, "offline", qos=1, retain=True)
client.on_connect = on_connect
client.connect(os.getenv("MQTT_HOST", "127.0.0.1"), 1883, keepalive=60)
client.loop_start()

heap_min = 210_000
while True:
    heap_min -= random.randint(0, 40)  # the low-water mark only ever goes down
    client.publish(f"{BASE}/telemetry", json.dumps({
        "heap": heap_min + random.randint(5_000, 25_000),
        "heap_min": heap_min,
        "rssi": random.randint(-78, -55),
        "uptime": int(time.time() - started),
        "interval": INTERVAL,
        "fw": FW_VERSION,
    }))
    time.sleep(INTERVAL)
