/** @type {import('next').NextConfig} */
const nextConfig = {

  // Tắt StrictMode để tránh double-mount WebSocket trong development
  reactStrictMode: false,

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
