# SocketXP Blog Tutorials

Working code for the tutorials on the [SocketXP blog](https://www.socketxp.com/iot/). Each folder is self-contained and has its own README with setup steps.

| Folder | What it is | Tutorial |
|---|---|---|
| [`mqtt-iot-monitoring`](mqtt-iot-monitoring) | A self-hosted MQTT monitoring stack in Docker Compose: Mosquitto, Telegraf, InfluxDB and a provisioned Grafana dashboard, plus simulated devices, an offline watchdog, a Raspberry Pi gateway bridge and failure scenarios | [MQTT IoT Monitoring: Track Device Health, Telemetry and Offline Status](https://www.socketxp.com/iot/mqtt-iot-monitoring/) (with [offline detection](https://www.socketxp.com/iot/mqtt-device-offline-detection-last-will-heartbeat/), [Grafana dashboard](https://www.socketxp.com/iot/mqtt-grafana-dashboard-mosquitto-telegraf-influxdb/) and [Raspberry Pi / ESP32](https://www.socketxp.com/iot/raspberry-pi-esp32-mqtt-monitoring/) follow-ups) |
| [`python-flask-ollama-chatbot`](python-flask-ollama-chatbot) | A private, ChatGPT-style chatbot: a small Python Flask app streaming replies from a local Ollama model, plus a benchmark script | [Build a Local LLM Chatbot with Python Flask and Ollama](https://www.socketxp.com/iot/flask-ollama-chatbot/) |
| [`self-hosted-ngrok-reverse-ssh-tunnel`](self-hosted-ngrok-reverse-ssh-tunnel) | Hardened sshd, Nginx and systemd configs for a self-hosted ngrok on your own domain, plus a Docker Compose lab that runs 27 checks against them | [Build a Self-Hosted ngrok With a Reverse SSH Tunnel and Nginx](https://www.socketxp.com/iot/self-hosted-ngrok-reverse-ssh-tunnel-nginx/) |

## Get the code

```bash
git clone --depth 1 https://github.com/ampaslabs/socketxp-blog-tutorials.git
cd socketxp-blog-tutorials/<folder>
```

## License

MIT. See [LICENSE](LICENSE).
