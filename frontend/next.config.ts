/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fix Turbopack panic: resolve tailwindcss từ đúng thư mục frontend/node_modules
  turbopack: {
    resolveAlias: {
      tailwindcss: './node_modules/tailwindcss',
    },
  },

  // Rewrites để proxy API requests trong development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },

  // Cho phép images từ external sources nếu cần
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/media/**',
      },
    ],
  },
};

export default nextConfig;
