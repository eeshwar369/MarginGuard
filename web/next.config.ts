import type { NextConfig } from 'next';

const dev = process.env.NODE_ENV === 'development';
const config: NextConfig = {
  output: dev ? undefined : 'export',
  poweredByHeader: false,
  reactStrictMode: true,
  images: { unoptimized: true },
  ...(dev
    ? {
        async rewrites() {
          return [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' }];
        },
      }
    : {}),
};
export default config;
