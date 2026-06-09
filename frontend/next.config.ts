import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Export static HTML during `next build` so we can serve via FastAPI
  output: "export",
};

export default nextConfig;
