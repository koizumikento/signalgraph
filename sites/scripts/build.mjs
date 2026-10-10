import { mkdir, copyFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
for (const dir of ["dist/server/", "dist/.openai/"]) await mkdir(new URL(dir, root), { recursive: true });
await copyFile(new URL("worker/index.js", root), new URL("dist/server/index.js", root));
await copyFile(new URL(".openai/hosting.json", root), new URL("dist/.openai/hosting.json", root));
