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

# Expose the http port
ARG HTTP_PORT=8080
ENV HTTP_PORT=$HTTP_PORT
EXPOSE $HTTP_PORT

# Create non-root user for security
RUN useradd -m -u 1000 memorial && \
    chown -R memorial:memorial /app
USER memorial

# Startup hypercorn
CMD ["hypercorn", "--config", "hypercorn.toml", "memorial:app"]
