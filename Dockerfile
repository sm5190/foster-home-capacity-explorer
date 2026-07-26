FROM node:22-bookworm-slim AS base

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app


FROM base AS dependencies

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./

RUN npm ci


FROM base AS builder

ENV NODE_ENV=production

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

RUN test -f data/generated/foster_capacity.db

RUN npm run build


FROM node:22-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
ENV FOSTER_DATABASE_PATH=/app/data/generated/foster_capacity.db

RUN groupadd \
    --system \
    --gid 1001 \
    nodejs \
    && useradd \
    --system \
    --uid 1001 \
    --gid nodejs \
    nextjs

COPY --from=builder \
    --chown=nextjs:nodejs \
    /app/public \
    ./public

COPY --from=builder \
    --chown=nextjs:nodejs \
    /app/.next/standalone \
    ./

COPY --from=builder \
    --chown=nextjs:nodejs \
    /app/.next/static \
    ./.next/static

COPY --from=builder \
    --chown=nextjs:nodejs \
    /app/data/generated/foster_capacity.db \
    ./data/generated/foster_capacity.db

USER nextjs

EXPOSE 3000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=20s \
    --retries=3 \
    CMD node -e \
    "fetch('http://127.0.0.1:' + (process.env.PORT || '3000') + '/api/health').then((response) => { if (!response.ok) process.exit(1); }).catch(() => process.exit(1));"

CMD ["node", "server.js"]