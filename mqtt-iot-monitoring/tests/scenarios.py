"""Failure scenarios that `docker stop/kill/pause` can't simulate.

  hung       connected, keepalive alive, but the app stops sending telemetry
  reboot     uptime goes backwards (device restarted between two messages)
  site       4 devices at one site disappear together -> one site-outage alert
  willdelay  MQTT 5 Will Delay: a quick reconnect cancels the Will; a long outage doesn't

Run inside the compose network:  ./tests/run.sh <scenario>
"""
import json
import os
import socket
import sys
import time

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

HOST = os.getenv("MQTT_HOST", "mosquitto")
PASSWORD = os.environ["MQTT_PASSWORD"]


def log(*args):
    print(time.strftime("%H:%M:%S"), *args, flush=True)


def device(device_id, site="site9", **kw):
    status = f"fleet/{site}/{device_id}/status"
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=device_id, **kw)
    c.username_pw_set(device_id, PASSWORD)
    c.on_connect = lambda c, u, f, rc, p: c.publish(status, "online", qos=1, retain=True)
    return c, f"fleet/{site}/{device_id}"


def telemetry(c, base, uptime, interval=5):
    c.publish(f"{base}/telemetry", json.dumps({"cpu": 5.0, "uptime": uptime, "interval": interval}))


def hung():
    c, base = device("sim01")
    c.will_set(f"{base}/status", "offline", qos=1, retain=True)
    c.connect(HOST, 1883, keepalive=60)
    c.loop_start()
    for i in range(3):
        telemetry(c, base, 1000 + i * 5)
        time.sleep(5)
    log("main loop 'hangs' now; network thread keeps answering keepalive pings")
    time.sleep(120)
    c.loop_stop()


def reboot():
    c, base = device("sim01")
    c.connect(HOST, 1883, keepalive=60)
    c.loop_start()
    telemetry(c, base, 86400)
    time.sleep(2)
    log("uptime drops from 86400 to 12")
    telemetry(c, base, 12)
    time.sleep(3)
    c.publish(f"{base}/status", "", qos=1, retain=True)  # clean up retained status
    time.sleep(1)
    c.loop_stop()


def site():
    clients = []
    for n in range(1, 5):
        c, base = device(f"sim0{n}")
        c.will_set(f"{base}/status", "offline", qos=1, retain=True)
        c.connect(HOST, 1883, keepalive=60)
        c.loop_start()
        clients.append((c, base))
    for _ in range(2):
        for c, base in clients:
            telemetry(c, base, 5000)
        time.sleep(5)
    log("whole site loses power: dropping all 4 connections without DISCONNECT")
    for c, _ in clients:
        c.loop_stop()                         # stop the network thread so it can't reconnect
        c._sock.shutdown(socket.SHUT_RDWR)   # simulate a dead link (no DISCONNECT packet)
    time.sleep(100)


def willdelay():
    def connect():
        c, base = device("sim01", protocol=mqtt.MQTTv5)
        will_props = Properties(PacketTypes.WILLMESSAGE)
        will_props.WillDelayInterval = 20
        c.will_set(f"{base}/status", "offline", qos=1, retain=True, properties=will_props)
        connect_props = Properties(PacketTypes.CONNECT)
        connect_props.SessionExpiryInterval = 60
        c.connect(HOST, 1883, keepalive=60, clean_start=False, properties=connect_props)
        c.loop_start()
        time.sleep(2)
        return c

    def drop(c):
        c.loop_stop()
        c._sock.shutdown(socket.SHUT_RDWR)

    c = connect()
    log("blip: drop the connection, reconnect after 8 s (Will Delay is 20 s)")
    drop(c)
    time.sleep(8)
    c = connect()
    log("reconnected; expect NO offline above this line. Now a real outage:")
    drop(c)
    time.sleep(30)
    log("expect exactly one offline about 20 s after the drop")


{"hung": hung, "reboot": reboot, "site": site, "willdelay": willdelay}[sys.argv[1]]()
