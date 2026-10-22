/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produces a self-contained .next/standalone output (server + only the
  // node_modules it actually needs) — the Docker image copies just that,
  // instead of the full node_modules tree, which is significantly smaller.
  output: "standalone",
};

export default nextConfig;
