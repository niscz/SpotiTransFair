# backend/config/gunicorn.conf.py
"""
Gunicorn-Konfigurationsdatei für die SpotiTransFair-Anwendung.
"""
# pylint: disable=C0103

import multiprocessing

# Server socket
bind = "0.0.0.0:8001"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120

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
