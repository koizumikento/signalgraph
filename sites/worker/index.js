const MAX_BODY = 16384;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/mcp") return new Response("SignalGraph MCP: POST /mcp", { status: url.pathname === "/" ? 200 : 404 });
    const origin = request.headers.get("origin");
    if (origin !== null && origin !== url.origin) return new Response(null, { status: 403 });
    if (request.method !== "POST") return new Response(null, { status: 405, headers: { Allow: "POST" } });
    const actor = request.headers.get("oai-authenticated-user-id");
    if (!actor) return new Response(null, { status: 401 });
    if (!env.SIGNALGRAPH_ALLOWED_USER_ID || actor !== env.SIGNALGRAPH_ALLOWED_USER_ID) return new Response(null, { status: 403 });
    let backend;
    try {
      backend = new URL(env.SIGNALGRAPH_BACKEND_URL);
      if (backend.protocol !== "https:" || backend.username || backend.password || backend.pathname !== "/mcp" || backend.search || backend.hash) throw new Error();
      if (!env.SIGNALGRAPH_BACKEND_TOKEN) throw new Error();
    } catch {
      return new Response("Backend is not configured; contact the operator", { status: 503 });
    }
    const chunks = [];
    let size = 0;
    const reader = request.body?.getReader();
    if (reader) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > MAX_BODY) {
            await reader.cancel();
            return new Response(null, { status: 413 });
          }
          chunks.push(value);
        }
      } catch {
        return new Response(null, { status: 400 });
      } finally {
        reader.releaseLock();
      }
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
    const headers = new Headers({ Authorization: `Bearer ${env.SIGNALGRAPH_BACKEND_TOKEN}` });
    for (const name of ["accept", "content-type", "mcp-protocol-version"]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    try {
      const response = await fetch(backend, {
        method: "POST", headers, body, redirect: "manual", signal: request.signal,
      });
      if (response.status >= 300 && response.status < 400 || response.status >= 500) {
        await response.body?.cancel();
        return new Response("Backend unavailable; contact the operator", { status: 502 });
      }
      const output = new Headers({ "Cache-Control": "no-store, no-transform" });
      for (const name of ["content-type", "allow"]) {
        const value = response.headers.get(name);
        if (value) output.set(name, value);
      }
      // Stream SDK SSE (including keepalives) so long research does not buffer.
      return new Response(response.body, { status: response.status, headers: output });
    } catch {
      return new Response("Backend unavailable; contact the operator", { status: 502 });
    }
  },
};
