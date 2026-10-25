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

# The one place the base image is named, by tag and by digest (#818). The tag
# alone floats: each build took whatever it pointed at that day. Dependabot's
# docker entry moves the digest, as a pull request the image scan runs on. It
# reads a literal FROM line only; with the tag in a build argument it found no
# dependency here at all.
FROM node:24-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS base

# ---- deps: install with the lockfile only, so this layer caches on lock changes
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- build
FROM base AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Next inlines NEXT_PUBLIC_* into the client bundle at build time, so anything the
# browser needs must be present here rather than only at runtime — and the image
# is only valid for the environment these came from (#779). No defaults: CI and
# docker-compose.build.yml supply each environment's own values.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_BETTER_AUTH_URL
ARG NEXT_PUBLIC_SENTRY_DSN
ARG NEXT_PUBLIC_ENVIRONMENT
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_BETTER_AUTH_URL=${NEXT_PUBLIC_BETTER_AUTH_URL} \
    NEXT_PUBLIC_SENTRY_DSN=${NEXT_PUBLIC_SENTRY_DSN} \
    NEXT_PUBLIC_ENVIRONMENT=${NEXT_PUBLIC_ENVIRONMENT} \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runtime
FROM base AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3002 \
    HOSTNAME=0.0.0.0

# The runtime runs `node server.js` and installs nothing, so the base image's
# npm, corepack and yarn go (#818). npm carries its own dependencies, which is
# what an image scan finds, and a package manager is the first thing an
# intruder would reach for.
RUN rm -rf /usr/local/lib/node_modules /opt/yarn-* \
      /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
      /usr/local/bin/yarn /usr/local/bin/yarnpkg

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
