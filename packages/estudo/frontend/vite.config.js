import { defineConfig } from "vite";

function selfHostExcalidrawFonts() {
  const packageChunk = "/node_modules/@excalidraw/excalidraw/dist/prod/chunk-K2UTITRG.js";
  const fallbackAppend = "return r.push(new URL(n,jn.ASSETS_FALLBACK_URL)),r";
  let patched = false;
  return {
    name: "self-host-excalidraw-fonts",
    apply: "build",
    enforce: "pre",
    buildStart() { patched = false; },
    transform(code, id) {
      const normalizedId = id.replaceAll("\\", "/");
      if (!normalizedId.includes(packageChunk)) return null;
      const matches = code.split(fallbackAppend).length - 1;
      if (matches !== 1) {
        throw new Error("A estrutura do fallback de fontes do Excalidraw mudou; revise o transform local antes de compilar.");
      }
      patched = true;
      return { code: code.replace(fallbackAppend, "return r"), map: null };
    },
    buildEnd(error) {
      if (!error && !patched) throw new Error("O chunk esperado do Excalidraw não foi encontrado; revise a adaptação das fontes.");
    },
  };
}

export default defineConfig({
  base: "/",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (request, incoming) => {
            if (incoming.headers.origin === "http://127.0.0.1:5173") {
              request.setHeader("Origin", "http://127.0.0.1:8765");
            }
          });
        },
      },
    },
  },
  build: {
    outDir: "../../../data/frontend", sourcemap: false, emptyOutDir: true,
    rolldownOptions: {
      onLog(level, log, handler) {
        if (log.code === "MODULE_LEVEL_DIRECTIVE" && log.message.includes("use client")) return;
        handler(level, log);
      },
    },
  },
  plugins: [selfHostExcalidrawFonts()],
});
