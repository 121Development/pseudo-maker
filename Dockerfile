# syntax=docker/dockerfile:1.6
#
# mutable-cosmos — web UI for Swedish-PII anonymization of documents.
# Runs the `serve` subcommand. Bind to 0.0.0.0 inside the container; operator
# restricts network exposure via docker/compose/firewall.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal runtime dependencies for python-docx (lxml needs libxml2 at runtime)
# and a safe TLS root store for optional outbound calls during build.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps in an isolated layer that cachers can reuse.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && python -m spacy download sv_core_news_lg

# Non-root user with a writable home for any runtime caches.
RUN groupadd --system --gid 10001 app \
    && useradd  --system --uid 10001 --gid app --home /home/app --create-home app
USER app

# Sessions live in /tmp/mcosmos_* — mount as tmpfs (see docker-compose.yml).
ENV MUTABLE_COSMOS_HOST=0.0.0.0 \
    MUTABLE_COSMOS_PORT=8765

EXPOSE 8765

# tini reaps zombies and forwards signals so Ctrl+C / container stop is clean.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "mutable-cosmos serve --host ${MUTABLE_COSMOS_HOST} --port ${MUTABLE_COSMOS_PORT} --no-browser"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen(f'http://127.0.0.1:${MUTABLE_COSMOS_PORT}/api/health', timeout=3).read() or sys.exit(1)" || exit 1
