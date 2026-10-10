import assert from "node:assert/strict";
import { test, afterEach } from "node:test";
import worker from "../worker/index.js";

const nativeFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = nativeFetch; });
const env = { SIGNALGRAPH_BACKEND_URL: "https://backend.example/mcp", SIGNALGRAPH_BACKEND_TOKEN: "synthetic-token", SIGNALGRAPH_ALLOWED_USER_ID: "site-owner" };
function request(body = { jsonrpc: "2.0", id: 1, method: "tools/list" }, headers = {}, method = "POST") {
  return new Request("https://site.example/mcp", { method, headers: {
    "oai-authenticated-user-id": "site-owner", "content-type": "application/json",
    accept: "application/json, text/event-stream", "mcp-protocol-version": "2025-11-25", ...headers,
  }, ...(method === "POST" ? { body: typeof body === "string" ? body : JSON.stringify(body) } : {}) });
}

test("identity, membership, origin, methods and byte limits fail closed", async () => {
  globalThis.fetch = () => { throw new Error("must not forward"); };
  const anonymous = request(); anonymous.headers.delete("oai-authenticated-user-id");
  assert.equal((await worker.fetch(anonymous, env)).status, 401);
  assert.equal((await worker.fetch(request({}, { "oai-authenticated-user-id": "other" }), env)).status, 403);
  assert.equal((await worker.fetch(request(), { ...env, SIGNALGRAPH_ALLOWED_USER_ID: "" })).status, 403);
  assert.equal((await worker.fetch(request({}, { origin: "https://evil.example" }), env)).status, 403);
  assert.equal((await worker.fetch(request({}, {}, "GET"), env)).status, 405);
  assert.equal((await worker.fetch(request("あ".repeat(6000)), env)).status, 413);
  assert.equal((await worker.fetch(new Request("https://site.example/other"), env)).status, 404);
});

test("only fixed HTTPS MCP endpoint is used, without caller credentials or redirects", async () => {
  for (const endpoint of ["http://backend.example/mcp", "https://user:pass@backend.example/mcp", "https://backend.example/other", "https://backend.example/mcp?url=evil", "invalid"]) {
    assert.equal((await worker.fetch(request(), { ...env, SIGNALGRAPH_BACKEND_URL: endpoint })).status, 503);
  }
  assert.equal((await worker.fetch(request(), { ...env, SIGNALGRAPH_BACKEND_TOKEN: "" })).status, 503);
  globalThis.fetch = async (url, options) => {
    assert.equal(String(url), env.SIGNALGRAPH_BACKEND_URL);
    assert.equal(options.headers.get("authorization"), `Bearer ${env.SIGNALGRAPH_BACKEND_TOKEN}`);
    for (const header of ["cookie", "origin", "oai-authenticated-user-id", "oai-sites-authorization", "mcp-session-id"]) assert.equal(options.headers.get(header), null);
    assert.equal(options.headers.get("mcp-protocol-version"), "2025-11-25");
    assert.equal(options.redirect, "manual");
    return new Response(null, { status: 302, headers: { location: "https://evil.example", "set-cookie": "secret" } });
  };
  const response = await worker.fetch(request({}, { cookie: "private", authorization: "Bearer caller", origin: "https://site.example", "oai-sites-authorization": "bypass", "mcp-session-id": "untrusted" }), env);
  assert.equal(response.status, 502);
  assert.equal(response.headers.get("set-cookie"), null);
  assert.equal(response.headers.get("location"), null);
});

test("SSE is streamed before completion and preserves protocol result", async () => {
  let finish;
  const stream = new ReadableStream({ start(controller) {
    controller.enqueue(new TextEncoder().encode(": ping\n\n"));
    finish = () => { controller.enqueue(new TextEncoder().encode('data: {"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n\n')); controller.close(); };
  } });
  globalThis.fetch = async () => new Response(stream, { headers: { "content-type": "text/event-stream", "set-cookie": "secret" } });
  const response = await worker.fetch(request(), env);
  assert.equal(response.headers.get("content-type"), "text/event-stream");
  assert.equal(response.headers.get("cache-control"), "no-store, no-transform");
  assert.equal(response.headers.get("set-cookie"), null);
  const reader = response.body.getReader();
  assert.equal(new TextDecoder().decode((await reader.read()).value), ": ping\n\n");
  finish();
  assert.match(new TextDecoder().decode((await reader.read()).value), /"tools":\[\]/);
  assert.equal((await reader.read()).done, true);
});

test("SDK JSON and notification responses survive; upstream failures are redacted", async () => {
  globalThis.fetch = async () => new Response('{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"unknown"}}', { headers: { "content-type": "application/json" } });
  assert.equal(JSON.parse(await (await worker.fetch(request(), env)).text()).error.code, -32601);
  globalThis.fetch = async () => new Response(null, { status: 202 });
  assert.equal((await worker.fetch(request(), env)).status, 202);
  for (const fail of [async () => new Response("secret-path", { status: 500 }), async () => { throw new Error("secret-path"); }]) {
    globalThis.fetch = fail;
    const response = await worker.fetch(request(), env);
    assert.equal(response.status, 502);
    assert.doesNotMatch(await response.text(), /secret-path/);
  }
});
