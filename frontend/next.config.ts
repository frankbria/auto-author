import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Next generates AGENTS.md and CLAUDE.md on every `next dev` start (#611).
  // Turned off rather than ignored: this repo already has a considered root
  // CLAUDE.md, and a second auto-generated instruction file one directory down
  // competes with it silently — every agent session started in `frontend/`
  // would read the generated one as project instructions. They were also
  // untracked and unignored, so any `git add -A` mid-task swept them in.
  // `frontend/.gitignore` still lists both as a second line of defence, in case
  // a future Next version regenerates them regardless of this flag.
  agentRules: false,

  // Emit a self-contained server bundle at .next/standalone for container images
  // (#427). This is additive: `next build` still produces the normal .next output,
  // so `next start` — which the current PM2 deploy uses — keeps working unchanged.
  output: "standalone",
  // Pin the trace root to this directory. The repo root carries its own
  // package.json (a PM2 shell), so Next walked further up and rooted the trace at
  // the home directory — emitting the server at
  // .next/standalone/projects/auto-author/frontend/server.js and sweeping ~/.nvm
  // into a 197 MB bundle. Pinning it puts the entrypoint at the documented
  // .next/standalone/server.js, which is what the Dockerfile COPYs.
  outputFileTracingRoot: path.join(__dirname),

  // Enable SWC minification and optimization
  // swcMinify: true,

  // Explicitly enable SWC compilation
  compiler: {
    // This ensures SWC is used even with custom Babel config
    styledComponents: true,
  },

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Content-Security-Policy is set per-request in src/middleware.ts
          // (#190) — it carries a nonce, which a static header can't.
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ];
  },

  async redirects() {
    return [
      {
        source: '/sign-in',
        destination: '/sign-in/',
        permanent: true,
      },
      {
        source: '/sign-up',
        destination: '/sign-up/',
        permanent: true,
      }
    ];
  },
};

export default nextConfig;
