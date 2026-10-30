# syntax=docker/dockerfile:1
FROM node:22-alpine AS frontend-build
WORKDIR /build/tools/ascii/frontend
COPY tools/ascii/frontend/package.json tools/ascii/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tools/ascii/frontend/ ./
COPY ui-kit/ /build/ui-kit/
RUN npm run build

FROM node:22-bookworm-slim AS youtube-js
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY --from=youtube-js /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY requirements.txt ./
COPY tools/ascii/requirements.txt ./tools/ascii/requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home app \
    && mkdir -p /data && chown app:app /data
ENV AMUZASCII_VIDEO_DIR=/data TMPDIR=/data
COPY --chown=app:app run.py server.py ./
COPY --chown=app:app frontend/ ./frontend/
COPY --chown=app:app ui-kit/ ./ui-kit/
COPY --chown=app:app tools/__init__.py ./tools/__init__.py
COPY --chown=app:app tools/ascii/__init__.py ./tools/ascii/__init__.py
COPY --chown=app:app tools/ascii/backend/ ./tools/ascii/backend/
COPY --chown=app:app tools/downloader/ ./tools/downloader/
COPY --chown=app:app tools/upscaler/ ./tools/upscaler/
COPY --from=frontend-build --chown=app:app /build/tools/ascii/frontend/dist/ ./tools/ascii/frontend/dist/
USER app
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/api/health', timeout=3).close()"]
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8010"]
