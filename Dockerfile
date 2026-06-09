FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Base location for application source code
WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml setup.py README.md ./
RUN pip install --upgrade pip && \
    pip install .

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 memorial && \
    chown -R memorial:memorial /app
USER memorial

# Health check
HEALTHCHECK --interval=10s --timeout=10s --retries=3 --start-period=10s \
    CMD bash -c "echo > /dev/tcp/localhost/8000"

# Startup hypercorn
CMD ["hypercorn", "--config", "file:/app/hypercorn_config.py", "memorial:app"]
