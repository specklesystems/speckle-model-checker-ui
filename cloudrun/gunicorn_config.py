# cloudrun/gunicorn_config.py
# Gunicorn configuration for Cloud Run optimization

import multiprocessing
import os

# Worker configuration
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_connections = 1000

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Timeout configuration
timeout = 120
keepalive = 5

# Server mechanics
daemon = False
pidfile = None
tmp_upload_dir = None

# Logging configuration
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# Process naming
proc_name = "speckle-model-checker"

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
backlog = 2048

# SSL (disabled for Cloud Run)
keyfile = None
certfile = None

# Performance tuning
preload_app = True


# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Speckle Model Checker")


def on_reload(server):
    """Called when configuration is changed."""
    server.log.info("Configuration reloaded")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Listening at: %s", bind)


def worker_int(worker):
    """Called when a worker receives an INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.error("Worker received SIGABRT signal")
