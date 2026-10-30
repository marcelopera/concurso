FROM node:24-bookworm-slim AS frontend
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate
COPY sistema-estudo/package.json sistema-estudo/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY sistema-estudo/index.html sistema-estudo/vite.config.js ./
COPY sistema-estudo/src ./src
COPY sistema-estudo/public ./public
COPY sistema-estudo/scripts/copy-excalidraw-fonts.mjs ./scripts/
RUN pnpm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app/sistema-estudo
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 estudo
COPY sistema-estudo/*.py ./
COPY sistema-estudo/scripts/preparar_container.py ./scripts/
COPY sistema-estudo/roadmaps/apofp-2026/roadmap.json ./roadmaps/apofp-2026/
COPY sistema-estudo/roadmaps/apofp-2026/vinculacao/vinculos.jsonl sistema-estudo/roadmaps/apofp-2026/vinculacao/relatorio.json ./roadmaps/apofp-2026/vinculacao/
COPY base-questoes/dados/conteudo.sqlite /app/base-questoes/dados/conteudo.sqlite
COPY biblioteca-concursos/ /app/biblioteca-concursos/
COPY --from=frontend /app/dist ./dist
RUN python scripts/preparar_container.py \
    && chown -R estudo:estudo /app/sistema-estudo/dados
USER estudo
VOLUME ["/app/sistema-estudo/dados"]
EXPOSE 8765
CMD ["python", "server.py", "--host", "0.0.0.0"]
