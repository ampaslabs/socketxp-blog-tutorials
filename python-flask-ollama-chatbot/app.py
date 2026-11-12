import hmac
import os

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from openai import OpenAI

app = Flask(__name__)

# Ollama exposes an OpenAI-compatible API under /v1
client = OpenAI(
    base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key="ollama",  # required by the SDK, ignored by Ollama
)

MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
SYSTEM_PROMPT = "You are a helpful, concise assistant."
MAX_HISTORY = 20  # keep the last 20 messages to stay inside the context window

# Optional HTTP Basic Auth. Set APP_PASS before exposing the app to the internet.
APP_USER = os.environ.get("APP_USER", "admin")
APP_PASS = os.environ.get("APP_PASS")


@app.before_request
def require_login():
    if not APP_PASS:
        return None
    auth = request.authorization
    if auth and auth.type == "basic":
        user_ok = hmac.compare_digest((auth.username or "").encode(), APP_USER.encode())
        pass_ok = hmac.compare_digest((auth.password or "").encode(), APP_PASS.encode())
        if user_ok and pass_ok:
            return None
    return Response(
        "Login required", 401, {"WWW-Authenticate": 'Basic realm="Chatbot", charset="UTF-8"'}
    )


@app.route("/")
def index():
    return render_template("index.html", model=MODEL)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    history = data.get("messages", [])

    if not history:
        return jsonify({"error": "messages is required"}), 400

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-MAX_HISTORY:]

    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    def generate():
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    print(f" * Basic Auth: {'ON (user: ' + APP_USER + ')' if APP_PASS else 'OFF (set APP_PASS to enable)'}")
    app.run(host="127.0.0.1", port=5001, debug=False)
