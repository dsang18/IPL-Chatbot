import os

import requests
from flask import Flask, Response, jsonify, render_template, request, stream_with_context


BACKEND_URL = os.getenv("IPL_API_BASE_URL", "http://127.0.0.1:8000")

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health_check():
    try:
        backend = requests.get(f"{BACKEND_URL}/health", timeout=3)
        backend.raise_for_status()
        return jsonify({"status": "ok", "backend": "connected"})
    except requests.RequestException:
        return jsonify({"status": "degraded", "backend": "unavailable"}), 503


@app.post("/api/chat/stream")
def proxy_chat_stream():
    """Keep the browser on the Flask origin while relaying FastAPI SSE events."""
    payload = request.get_json(silent=True) or {}

    try:
        backend_response = requests.post(
            f"{BACKEND_URL}/api/chat/stream",
            json=payload,
            stream=True,
            timeout=(5, 300),
        )
        backend_response.raise_for_status()
    except requests.RequestException:
        return jsonify({"message": "The analytics service is unavailable. Start the FastAPI backend and try again."}), 503

    def relay():
        try:
            for chunk in backend_response.iter_content(chunk_size=None):
                if chunk:
                    yield chunk
        finally:
            backend_response.close()

    return Response(
        stream_with_context(relay()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
