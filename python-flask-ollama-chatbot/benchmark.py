"""Benchmark a local Ollama model and the Flask chatbot in front of it.

Measures:
  1. Model speed straight from Ollama (tokens/sec, prompt processing time)
  2. Time to first token (TTFT) and total time through the Flask app,
     e.g. on localhost vs. through a SocketXP public URL
  3. TTFT and total time with several chats streaming at once

Uses only the Python standard library.

Examples:
  python3 benchmark.py
  python3 benchmark.py --app-url https://abc.socketxp.com --user admin --password secret
  python3 benchmark.py --model qwen2.5 --runs 10 --concurrency 4
"""

import argparse
import base64
import json
import platform
import statistics
import subprocess
import threading
import sys
import time
import urllib.error
import urllib.request

PROMPT = "Explain what a reverse proxy is in about 100 words."


def post(url, payload, auth=None, timeout=600):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    if auth:
        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    return urllib.request.urlopen(req, timeout=timeout)


def ollama_run(ollama_url, model):
    """One non-streaming call to Ollama's native API, which reports exact token timings."""
    with post(f"{ollama_url}/api/chat", {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": False,
    }) as res:
        data = json.load(res)
    return {
        "tokens": data["eval_count"],
        "tok_per_sec": data["eval_count"] / (data["eval_duration"] / 1e9),
        "prompt_sec": data.get("prompt_eval_duration", 0) / 1e9,
    }


def app_run(app_url, auth):
    """One streaming chat through the Flask app. Returns (ttft, total) in seconds."""
    start = time.perf_counter()
    ttft = None
    with post(f"{app_url}/api/chat", {
        "messages": [{"role": "user", "content": PROMPT}],
    }, auth=auth) as res:
        while True:
            chunk = res.read1(1024)
            if not chunk:
                break
            if ttft is None:
                ttft = time.perf_counter() - start
    return ttft, time.perf_counter() - start


def app_concurrent(app_url, auth, n):
    results, errors = [], []

    def worker():
        try:
            results.append(app_run(app_url, auth))
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results, errors


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, round(p / 100 * (len(values) - 1)))]


def system_info(ollama_url):
    info = {"OS": f"{platform.system()} {platform.release()} ({platform.machine()})"}
    try:
        if platform.system() == "Darwin":
            info["CPU"] = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
            info["RAM"] = f"{int(subprocess.check_output(['sysctl', '-n', 'hw.memsize'])) / 2**30:.0f} GB"
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                lines = [line for line in f if line.startswith(("model name", "Model"))]
            info["CPU"] = lines[-1].split(":", 1)[1].strip() if lines else platform.processor()
            with open("/proc/meminfo") as f:
                info["RAM"] = f"{int(f.readline().split()[1]) / 2**20:.0f} GB"
        else:
            info["CPU"] = platform.processor()
    except Exception:
        pass
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/version", timeout=5) as res:
            info["Ollama"] = json.load(res)["version"]
    except Exception:
        info["Ollama"] = "unreachable"
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--app-url", default="http://localhost:5001", help="Flask app URL (localhost or public URL)")
    parser.add_argument("--model", default="llama3.2", help="must match the model the Flask app uses")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--user", default="admin", help="Basic Auth user, if the app requires a login")
    parser.add_argument("--password", help="Basic Auth password, if the app requires a login")
    parser.add_argument("--skip-ollama", action="store_true", help="skip the direct Ollama test")
    args = parser.parse_args()
    auth = (args.user, args.password) if args.password else None

    print("## System\n")
    for k, v in {**system_info(args.ollama_url), "Model": args.model}.items():
        print(f"- **{k}:** {v}")

    print("\nWarming up (loads the model into memory)...")
    try:
        app_run(args.app_url, auth)
    except urllib.error.HTTPError as e:
        sys.exit(f"Flask app returned {e.code}: {e.read().decode(errors='replace')[:200]}")
    except urllib.error.URLError as e:
        sys.exit(f"Can't reach the Flask app at {args.app_url}: {e.reason}. Is it running?")

    if not args.skip_ollama:
        runs = [ollama_run(args.ollama_url, args.model) for _ in range(args.runs)]
        print(f"\n## Model speed (Ollama direct, {args.runs} runs)\n")
        print("| Metric | Median |\n|---|---|")
        print(f"| Generation speed | {statistics.median(r['tok_per_sec'] for r in runs):.1f} tokens/sec |")
        print(f"| Prompt processing | {statistics.median(r['prompt_sec'] for r in runs) * 1000:.0f} ms |")
        print(f"| Reply length | {statistics.median(r['tokens'] for r in runs):.0f} tokens |")

    runs = [app_run(args.app_url, auth) for _ in range(args.runs)]
    print(f"\n## Flask app, one chat at a time ({args.app_url}, {args.runs} runs)\n")
    print("| Metric | Median | Min | Max |\n|---|---|---|---|")
    for name, idx in (("Time to first token", 0), ("Total reply time", 1)):
        vals = [r[idx] for r in runs]
        print(f"| {name} | {statistics.median(vals):.2f} s | {min(vals):.2f} s | {max(vals):.2f} s |")

    results, errors = app_concurrent(args.app_url, auth, args.concurrency)
    print(f"\n## Flask app, {args.concurrency} chats at once\n")
    if results:
        print("| Metric | p50 | p95 |\n|---|---|---|")
        for name, idx in (("Time to first token", 0), ("Total reply time", 1)):
            vals = [r[idx] for r in results]
            print(f"| {name} | {pct(vals, 50):.2f} s | {pct(vals, 95):.2f} s |")
    print(f"\n{len(results)} succeeded, {len(errors)} failed")
    for e in errors[:3]:
        print(f"- {e}")


if __name__ == "__main__":
    main()
