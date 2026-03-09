FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Base location for application source code
WORKDIR /app

# Install runtime and build dependencies required for uWSGI
# Runtime deps: libexpat1, libpcre2-8-0 (needed by uWSGI at runtime)
# Build deps: gcc, python3-dev, libpcre2-dev (only needed for compilation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libexpat1 \
        libpcre2-8-0 \
        gcc \
        python3-dev \
        libpcre2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and install dependencies
COPY pyproject.toml setup.py README.md ./
RUN pip install --upgrade pip && \
    pip install . && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false gcc python3-dev libpcre2-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Expose the http port
ARG HTTP_PORT=8080
ENV HTTP_PORT=$HTTP_PORT
EXPOSE $HTTP_PORT

# Expose the socket port
ARG SOCKET_PORT=8181
ENV SOCKET_PORT=$SOCKET_PORT
EXPOSE $SOCKET_PORT

# Create non-root user for security
RUN useradd -m -u 1000 memorial && \
    chown -R memorial:memorial /app
USER memorial

# Startup uwsgi
CMD ["uwsgi", "--ini", "uwsgi.ini"]
