import { defineConfig } from "vite";

function selfHostExcalidrawFonts() {
  const packageChunk = "/node_modules/@excalidraw/excalidraw/dist/prod/chunk-K2UTITRG.js";
  const fallbackAppend = "return r.push(new URL(n,jn.ASSETS_FALLBACK_URL)),r";
  return {
    name: "self-host-excalidraw-fonts",
    apply: "build",
    enforce: "pre",
    transform(code, id) {
      const normalizedId = id.replaceAll("\\", "/");
      if (!normalizedId.includes(packageChunk)) return null;
      const matches = code.split(fallbackAppend).length - 1;
      if (matches !== 1) {
        throw new Error("A estrutura do fallback de fontes do Excalidraw mudou; revise o transform local antes de compilar.");
      }
      return { code: code.replace(fallbackAppend, "return r"), map: null };
    },
  };
}

export default defineConfig({
  base: "/",
  build: { sourcemap: false, emptyOutDir: true },
  plugins: [selfHostExcalidrawFonts()],
});
