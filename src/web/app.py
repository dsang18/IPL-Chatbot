
import logging
import os

import requests
from flask import Flask, Response, jsonify, render_template, request, stream_with_context


BACKEND_URL = os.getenv("IPL_API_BASE_URL", "http://127.0.0.1:8000")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# Render the IPL chatbot interface.
@app.get("/")
def index():
    try:
        return render_template("index.html")
    except Exception as error:
        logger.exception("Unable to render the chatbot interface: %s", error)
        return "Unable to load the IPL Analytics interface.", 500


# Check whether the FastAPI backend is available.
@app.get("/health")
def health_check():
    try:
        backend = requests.get(f"{BACKEND_URL}/health", timeout=3)
        backend.raise_for_status()
        return jsonify({"status": "ok", "backend": "connected"})
    except requests.RequestException as error:
        logger.exception("Backend health check failed: %s", error)
        return jsonify({"status": "degraded", "backend": "unavailable"}), 503


# Relay the FastAPI SSE response to the browser.
@app.post("/api/chat/stream")
def proxy_chat_stream():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "A valid JSON request body is required."}), 400
    try:
        backend_response = requests.post(f"{BACKEND_URL}/api/chat/stream", json=payload, stream=True, timeout=(5, 300))
        backend_response.raise_for_status()
    except requests.RequestException as error:
        logger.exception("Unable to connect to the analytics backend: %s", error)
        return jsonify({"message": "The analytics service is unavailable. Please try again later."}), 503

    # Relay response chunks and close the upstream connection when finished.
    def relay():
        try:
            for chunk in backend_response.iter_content(chunk_size=None):
                if chunk:
                    yield chunk
        except requests.RequestException as error:
            logger.exception("Backend stream interrupted: %s", error)
        finally:
            backend_response.close()

    return Response(stream_with_context(relay()), content_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
