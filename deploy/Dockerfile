FROM node:25-bookworm-slim@sha256:81db02c4b671288a03915da9534dbd54f96d0e7c24d80ccc54f5b36b2e684370 AS frontend
WORKDIR /build/packages/estudo/frontend
RUN npm install --global pnpm@11.25.0
COPY packages/estudo/frontend/package.json packages/estudo/frontend/pnpm-lock.yaml packages/estudo/frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY packages/estudo/frontend/index.html packages/estudo/frontend/vite.config.js ./
COPY packages/estudo/frontend/src ./src
COPY packages/estudo/frontend/public ./public
COPY packages/estudo/frontend/scripts/copy-excalidraw-fonts.mjs ./scripts/
RUN pnpm run build

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
ENV PYTHONUNBUFFERED=1
ENV ESTUDO_DATA_DIR=/app/data ESTUDO_DIST_DIR=/app/frontend
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 estudo
COPY packages/contracts /tmp/packages/contracts
COPY packages/estudo/backend /tmp/packages/backend
RUN pip install --no-cache-dir /tmp/packages/contracts /tmp/packages/backend \
    && rm -rf /tmp/packages \
    && mkdir /app/data \
    && chown estudo:estudo /app/data
COPY --from=frontend /build/data/frontend ./frontend
USER estudo
VOLUME ["/app/data"]
EXPOSE 8765
CMD ["python", "-m", "estudo", "serve", "--host", "0.0.0.0"]
