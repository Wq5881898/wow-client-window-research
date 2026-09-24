from __future__ import annotations

import json
import os
import socket
import time
import urllib.request as urlrequest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

_original_getaddrinfo = socket.getaddrinfo


def ipv4_getaddrinfo(*args, **kwargs):
    rows = _original_getaddrinfo(*args, **kwargs)
    ipv4_rows = [row for row in rows if row[0] == socket.AF_INET]
    return ipv4_rows or rows


socket.getaddrinfo = ipv4_getaddrinfo

PROMPT = (
    'Emit only minified JSON: {"plan":[...]}. '
    "Include 12 short, non-actionable synthetic planning labels."
)


def stream_probe(base_url: str, model: str, api_key: str, max_tokens: int = 300) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
    }
    request = urlrequest.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
            "Accept": "text/event-stream",
        },
    )
    started = time.perf_counter()
    ttfb = None
    first_content = None
    content = ""
    with urlrequest.urlopen(request, timeout=90) as response:
        while True:
            line = response.readline()
            if not line:
                break
            if ttfb is None:
                ttfb = time.perf_counter() - started
            text = line.decode("utf-8", "ignore").strip()
            if not text.startswith("data:"):
                continue
            payload = text[5:].strip()
            if payload in ("", "[DONE]"):
                continue
            try:
                parsed = json.loads(payload)
                piece = (parsed.get("choices", [{}])[0].get("delta") or {}).get("content") or ""
            except (ValueError, IndexError, AttributeError):
                continue
            if piece:
                if first_content is None:
                    first_content = time.perf_counter() - started
                content += piece
            if len(content) > 1200:
                break
    finished = time.perf_counter()
    return {
        "schema_version": 1,
        "ttfb_ms": round(1000 * (ttfb or 0), 1),
        "first_content_ms": round(1000 * (first_content or 0), 1),
        "total_ms": round(1000 * (finished - started), 1),
        "content_chars": len(content),
    }


def main() -> int:
    base_url = os.environ.get("LAT_BASE_URL", "")
    model = os.environ.get("LAT_MODEL", "")
    api_key = os.environ.get("LAT_API_KEY", "")
    if not all((base_url, model, api_key)):
        print("Set LAT_BASE_URL, LAT_MODEL, and LAT_API_KEY outside the project.")
        return 2
    result = stream_probe(base_url, model, api_key)
    output = RESULTS / "lat_stream_generic.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote de-identified timing metrics to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
