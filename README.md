# SocketXP Blog Tutorials

Working code for the tutorials on the [SocketXP blog](https://www.socketxp.com/iot/). Each folder is self-contained and has its own README with setup steps.

| Folder | What it is | Tutorial |
|---|---|---|
| [`python-flask-ollama-chatbot`](python-flask-ollama-chatbot) | A private, ChatGPT-style chatbot: a small Python Flask app streaming replies from a local Ollama model, plus a benchmark script | [Build a Local LLM Chatbot with Python Flask and Ollama](https://www.socketxp.com/iot/flask-ollama-chatbot/) |
| [`self-hosted-ngrok-reverse-ssh-tunnel`](self-hosted-ngrok-reverse-ssh-tunnel) | Hardened sshd, Nginx and systemd configs for a self-hosted ngrok on your own domain, plus a Docker Compose lab that runs 27 checks against them | [Build a Self-Hosted ngrok With a Reverse SSH Tunnel and Nginx](https://www.socketxp.com/iot/self-hosted-ngrok-reverse-ssh-tunnel-nginx/) |

## Get the code

```bash
git clone --depth 1 https://github.com/ampaslabs/socketxp-blog-tutorials.git
cd socketxp-blog-tutorials/<folder>
```

## License

MIT. See [LICENSE](LICENSE).
