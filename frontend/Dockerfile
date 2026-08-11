# syntax=docker/dockerfile:1
#
# Next.js frontend image (#427).
#
# Multi-stage: deps -> build -> runtime. The runtime stage carries only the
# standalone server bundle, so it does not need npm or the full node_modules.
#
# Requires `output: "standalone"` in next.config.ts, which also pins
# outputFileTracingRoot to the frontend directory. Without that pin Next roots the
# trace at the nearest lockfile ancestor — the repo root has its own package.json
# (a PM2 shell), so it walked up to the home directory and emitted the entrypoint
# at .next/standalone/projects/auto-author/frontend/server.js instead of
# .next/standalone/server.js. The COPY paths below assume the pinned layout.

ARG NODE_VERSION=24-alpine

# ---- deps: install with the lockfile only, so this layer caches on lock changes
FROM node:${NODE_VERSION} AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- build
FROM node:${NODE_VERSION} AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Next inlines NEXT_PUBLIC_* into the client bundle at build time, so anything the
# browser needs must be present here rather than only at runtime.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_BETTER_AUTH_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_BETTER_AUTH_URL=${NEXT_PUBLIC_BETTER_AUTH_URL} \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runtime
FROM node:${NODE_VERSION} AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3002 \
    HOSTNAME=0.0.0.0

# Non-root. node:alpine already ships a `node` user (uid 1000); reuse it rather
# than creating another.
USER node

# The standalone bundle excludes static assets and public/ by design — they are
# served from disk, so they must be copied alongside it or every asset 404s.
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public

EXPOSE 3002

# Published on the host port nginx already fronts (3002), so upstreams are unchanged.
CMD ["node", "server.js"]
