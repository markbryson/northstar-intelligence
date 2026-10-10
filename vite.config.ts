import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const projectRoot = process.cwd();
const projectNodeModules = resolve(projectRoot, "node_modules");

export default defineConfig({
  root: projectRoot,
  plugins: [react()],
  optimizeDeps: {
    noDiscovery: true,
  },
  server: {
    port: 5173,
    fs: {
      allow: [projectRoot, projectNodeModules],
    },
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
