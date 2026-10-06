# node:20.20.0-bookworm-slim, resolved 2026-08-14. The index digest supports
# both linux/amd64 and linux/arm64 and is deliberately immutable.
FROM node:20.20.0-bookworm-slim@sha256:d8a35d586fad3af7abb6fdb9ba972388395405f4d462da9e4a4ddcde67b5e0fb AS base

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# python:3.14.2-slim-bookworm, resolved 2026-08-14. Its index digest supports
# both linux/amd64 and linux/arm64 and keeps evidence generation on the pinned
# release Python rather than Debian's system interpreter.
FROM python:3.14.2-slim-bookworm@sha256:e87711ef5c86aaeaa7031718a69db79d334d94c545c709583f651b8185870941 AS portfolio-builder

WORKDIR /portfolio
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --requirement requirements.lock
COPY . ./
ARG SOURCE_DATE_EPOCH=0
RUN PYTHONPATH=src python scripts/bootstrap_portfolio.py \
  --run-id "abay-container-${SOURCE_DATE_EPOCH}"

FROM base AS build

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./
COPY --from=portfolio-builder /portfolio/reports ./reports
RUN npm run build

FROM base AS production-dependencies

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

FROM base AS runtime

ENV NODE_ENV=production \
  PORT=3000 \
  HOSTNAME=0.0.0.0

COPY --from=production-dependencies --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/reports ./reports

USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/api/dossier').then((response) => process.exit(response.ok ? 0 : 1)).catch(() => process.exit(1))"
CMD ["node", "node_modules/next/dist/bin/next", "start"]
