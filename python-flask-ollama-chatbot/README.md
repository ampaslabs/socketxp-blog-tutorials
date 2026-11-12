# Python Flask Based Ollama Local LLM Chatbot

A private, ChatGPT-style chatbot that runs entirely on your own machine. A small Python Flask app streams replies from a local model served by [Ollama](https://ollama.com). No API keys, no cloud, no per-token cost.

📖 **Full tutorial:** [Build a Local LLM Chatbot with Python Flask and Ollama](https://www.socketxp.com/iot/flask-ollama-chatbot/)

- Streams replies word by word
- Remembers the conversation (history trimmed to fit the context window)
- About 100 lines of Python and HTML, no frontend build step
- Works with any Ollama model, such as `llama3.2`, `qwen2.5`, `gemma` or `llama3.1:8b`

## Quick start

```bash
# 1. Install Ollama from https://ollama.com, then pull a model
ollama pull llama3.2

# 2. Install the Python packages
git clone --depth 1 https://github.com/ampaslabs/socketxp-blog-tutorials.git
cd socketxp-blog-tutorials/python-flask-ollama-chatbot
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run it
python3 app.py
```

Open http://localhost:5001.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2` | Any model you've pulled with `ollama pull` |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama's OpenAI-compatible endpoint. Keep the `/v1`. |
| `APP_PASS` | unset (login off) | Turns on HTTP Basic Auth for every page and API route |
| `APP_USER` | `admin` | Basic Auth username, used only when `APP_PASS` is set |

```bash
OLLAMA_MODEL=qwen2.5 python3 app.py
```

The app uses port 5001 because, on macOS, AirPlay Receiver already occupies Flask's default port 5000.

## Run it 24/7

```bash
pip install gunicorn
gunicorn -w 1 --threads 4 -b 127.0.0.1:5001 app:app
```

Keep one worker and use threads. The model runs inside Ollama, so extra worker processes don't help. On Windows, use `waitress-serve --listen=127.0.0.1:5001 app:app` instead.

## Share it over the internet

To use the chatbot from your phone or share it with your team without port forwarding:

1. **Turn on the login first.** Otherwise anyone with the URL can use your machine's CPU or GPU. Binding to `127.0.0.1` doesn't help here, because the tunnel connects from localhost.

   ```bash
   APP_PASS='choose-a-long-password' python3 app.py
   # or: APP_PASS='...' gunicorn -w 1 --threads 4 -b 127.0.0.1:5001 app:app
   ```

   Your browser will ask for the username (`admin`, or `APP_USER`) and password. Basic Auth sends the password with every request, so only use it over HTTPS. The SocketXP URL is HTTPS.
2. Keep debug mode off. The Werkzeug debugger allows remote code execution.
3. Create a public HTTPS URL with [SocketXP](https://www.socketxp.com):

```bash
socketxp login "<your-auth-token>"
socketxp connect http://localhost:5001
```

See [Expose a Flask App to the Internet Without Port Forwarding](https://www.socketxp.com/iot/remote-access-python-flask-app-from-internet/) for the full guide.

## Benchmark

`benchmark.py` measures model speed, time to first token, and how the app behaves with several chats at once. It uses only the Python standard library.

```bash
# With the app running on localhost
python3 benchmark.py

# Through a public URL protected with Basic Auth
python3 benchmark.py --app-url https://abc.socketxp.com --password 'your-password'

# Other options
python3 benchmark.py --model qwen2.5 --runs 10 --concurrency 4
```

Example result on an Apple M1 Pro (16 GB) with `llama3.2`, Ollama 0.32.15 and the app under gunicorn:

| Test | Result |
|---|---|
| Generation speed (Ollama direct) | 39.1 tokens/sec |
| Time to first token, 1 chat (localhost) | 0.05 s median |
| Total reply time, 1 chat (~114 tokens) | 2.30 s median |
| Time to first token, 3 chats at once | 2.23 s p50 / 4.68 s p95 |

With several chats at once, time to first token goes up because Ollama queues requests for the same model. Raise `OLLAMA_NUM_PARALLEL` on machines with enough memory to serve them in parallel.

## Troubleshooting

| Problem | Fix |
|---|---|
| `NotFoundError: Error code: 404` | `OLLAMA_BASE_URL` must end in `/v1` |
| `Error code: 404 - model 'llama3.2' not found` | `ollama pull llama3.2` |
| `502` from `/api/chat` or `Connection refused` | Start Ollama (`ollama serve` or the desktop app) |
| Reply appears all at once | A proxy is buffering the response. Test with `curl -N`. |

## License

MIT. See [LICENSE](../LICENSE).
