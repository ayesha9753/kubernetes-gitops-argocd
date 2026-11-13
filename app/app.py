"""Tiny Flask sample app for the Kubernetes GitOps / ArgoCD demo.

Endpoints:
    /        -> greeting + pod hostname (handy for watching load balancing)
    /health  -> health JSON, used by Kubernetes readiness/liveness probes
"""

import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)

APP_ENV = os.environ.get("APP_ENV", "prod")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")


@app.get("/")
def index():
    return jsonify(
        message="Hello from Kubernetes GitOps!",
        environment=APP_ENV,
        version=APP_VERSION,
        pod=socket.gethostname(),
    )


@app.get("/health")
def health():
    return jsonify(status="ok", environment=APP_ENV, version=APP_VERSION)


if __name__ == "__main__":
    # Local development only; in the container gunicorn serves the app.
    app.run(host="0.0.0.0", port=5000)
