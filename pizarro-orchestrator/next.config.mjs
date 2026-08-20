/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Provider adapters and the SQLite store are server-only. Keeping them out of
  // the client bundle is what guarantees API keys never reach the browser.
  serverExternalPackages: ["node:sqlite"],
};

export default nextConfig;
