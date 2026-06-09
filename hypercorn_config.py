# Hypercorn Configuration for Memorial
# ASGI server configuration for production deployment
import os

# Bind to all interfaces on port 8000
bind = ["0.0.0.0:8000"]

# Worker configuration
workers = int(os.environ.get("WORKERS", 4))
worker_class = "asyncio"

# Logging
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = "info"

# Keep-alive settings
keep_alive_timeout = 5

# Graceful shutdown timeout
graceful_timeout = 30
