import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable SWC minification and optimization
  swcMinify: true,
  
  // Explicitly enable SWC compilation
  compiler: {
    // This ensures SWC is used even with custom Babel config
    styledComponents: true,
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
