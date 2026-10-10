import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../dist/", import.meta.url);
const source = await readFile(new URL("server/index.js", root), "utf8");
const manifest = JSON.parse(await readFile(new URL(".openai/hosting.json", root), "utf8"));
assert.deepEqual(manifest.capabilities, ["mcp"]);
assert.equal(manifest.d1, null);
assert.equal(manifest.r2, null);
const worker = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(typeof worker.default.fetch, "function");
console.log("Sites artifact: valid Worker ESM, MCP capability, no storage bindings");
