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
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://clerk.auto-author.dev https://*.clerk.accounts.dev https://challenges.cloudflare.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: https: blob:",
              "media-src 'self'",
              "connect-src 'self' https://clerk.auto-author.dev https://*.clerk.accounts.dev https://api.auto-author.dev https://clerk-telemetry.com wss:",
              "frame-src 'self' https://*.clerk.accounts.dev",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "upgrade-insecure-requests",
            ].join('; '),
          },
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
