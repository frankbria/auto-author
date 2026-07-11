import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
