"""MQTT device health agent.

Publishes CPU, memory, disk, uptime and temperature as JSON every INTERVAL seconds
to fleet/{site}/{device_id}/telemetry, with a retained Last Will of "offline" on
fleet/{site}/{device_id}/status. On a Raspberry Pi it also adds throttling,
under-voltage, Wi-Fi RSSI and read-only root filesystem flags.
"""
import json
import os
import signal
import socket
import time

import paho.mqtt.client as mqtt
import psutil

import pi_metrics

BROKER = os.getenv("MQTT_HOST", "127.0.0.1")
PORT = int(os.getenv("MQTT_PORT", "1883"))
SITE = os.getenv("SITE", "site1")
DEVICE_ID = os.getenv("DEVICE_ID", socket.gethostname())
INTERVAL = int(os.getenv("INTERVAL", "30"))  # seconds between telemetry messages (the heartbeat)
FW_VERSION = os.getenv("FW_VERSION", "unknown")

BASE = f"fleet/{SITE}/{DEVICE_ID}"
STATUS_TOPIC = f"{BASE}/status"


def cpu_temperature():
    """Return the CPU temperature in °C, or None if the board doesn't expose it."""
    try:
        temps = psutil.sensors_temperatures()
    except AttributeError:  # not supported on this OS
        return None
    for name in ("cpu_thermal", "coretemp", "soc_thermal"):
        if temps.get(name):
            return temps[name][0].current
    return None


def on_connect(client, userdata, flags, reason_code, properties):
    if not reason_code.is_failure:
        # Overwrite the retained "offline" left by a previous Last Will
        client.publish(STATUS_TOPIC, "online", qos=1, retain=True)


def stop(signum, frame):
    # systemd and `docker stop` send SIGTERM; shut down cleanly like Ctrl+C
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, stop)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
client.username_pw_set(DEVICE_ID, os.environ["MQTT_PASSWORD"])
# The broker publishes this if we vanish without a clean disconnect
client.will_set(STATUS_TOPIC, "offline", qos=1, retain=True)
client.on_connect = on_connect
client.connect(BROKER, PORT, keepalive=60)
client.loop_start()  # background network thread with automatic reconnect

try:
    while True:
        payload = {
            "cpu": psutil.cpu_percent(interval=1),
            "mem": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
            "uptime": int(time.time() - psutil.boot_time()),
            "interval": INTERVAL,
            "fw": FW_VERSION,
        }
        temp = cpu_temperature()
        if temp is not None:
            payload["temp"] = round(temp, 1)
        payload.update(pi_metrics.collect())  # empty on non-Pi hardware
        client.publish(f"{BASE}/telemetry", json.dumps(payload), qos=0)
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    # A clean disconnect does NOT trigger the Last Will, so announce it ourselves
    client.publish(STATUS_TOPIC, "offline", qos=1, retain=True).wait_for_publish()
    client.disconnect()
    client.loop_stop()
