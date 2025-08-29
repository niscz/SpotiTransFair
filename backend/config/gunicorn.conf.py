# backend/config/gunicorn.conf.py
"""
Gunicorn configuration file for the SpotiTransFair application.
"""
# pylint: disable=C0103

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8001"
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("WEB_TIMEOUT", "120"))

# Worker settings
max_requests = 1000
max_requests_jitter = 50
keepalive = 500

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'spotitransfair-api'

# Production settings
reload = False
