import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";

const DEV_BACKEND_TARGET = "http://127.0.0.1:8000";

function attachProxyErrorLogging(proxy) {
  proxy.on("error", (error, request) => {
    const method = request?.method || "GET";
    const url = request?.url || "/";
    const details = error?.code || error?.message || "unknown error";
    console.error(
      `[vite-proxy] ${method} ${url} -> ${DEV_BACKEND_TARGET} failed: ${details}`,
    );
  });
}

function resolveBase(command) {
  if (command === "serve") return "/";
  if (process.env.OKO_BUILD_TARGET === "desktop") return "/";
  return "/static/";
}

export default defineConfig(({ command }) => ({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  base: resolveBase(command),
  publicDir: false,
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: DEV_BACKEND_TARGET,
        changeOrigin: true,
        configure: (proxy) => {
          attachProxyErrorLogging(proxy);
        },
      },
      "/static": {
        target: DEV_BACKEND_TARGET,
        changeOrigin: true,
        configure: (proxy) => {
          attachProxyErrorLogging(proxy);
        },
      },
    },
  },
  build: {
    outDir: "../dist",
    assetsDir: "assets",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes(".node_modules/lucide-vue-next") ||
            id.includes(".node_modules/simple-icons")
          ) {
            return "vendor-icons";
          }
          if (id.includes(".node_modules")) return "vendor";
          return undefined;
        },
      },
    },
  },
}));
