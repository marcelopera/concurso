import { cpSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, "../node_modules/@excalidraw/excalidraw/dist/prod/fonts");
const target = resolve(here, "../public/fonts");
mkdirSync(target, { recursive: true });
cpSync(source, target, { recursive: true, force: true });
