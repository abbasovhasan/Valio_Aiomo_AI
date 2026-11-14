// A public branded origin for the existing authenticated purchasing service.
// Runtime provider secrets and restricted catalog data remain on Modal.
const upstreamOrigin = 'https://hasan-abbasov--aimo-order-desk-web.us-east.modal.run';
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = request.headers.get('origin');
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method) && origin && origin !== url.origin) {
      return Response.json({ detail: { code: 'origin_blocked', message: 'Cross-origin changes are not allowed.' } }, { status: 403 });
    }
    const target = new URL(url.pathname + url.search, upstreamOrigin);
    const headers = new Headers();
    for (const key of ['accept', 'content-type', 'cookie', 'authorization', 'idempotency-key', 'if-none-match', 'if-modified-since']) {
      const value = request.headers.get(key);
      if (value) headers.set(key, value);
    }
    headers.set('user-agent', 'AimoTrustedTrade/1.0');
    try {
      const response = await fetch(target, {
        method: request.method,
        headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        redirect: 'manual',
      });
      const result = new Response(response.body, response);
      const location = result.headers.get('location');
      if (location && location.startsWith(upstreamOrigin)) {
        result.headers.set('location', url.origin + location.slice(upstreamOrigin.length));
      }
      result.headers.set('x-content-type-options', 'nosniff');
      result.headers.set('referrer-policy', 'same-origin');
      if (url.pathname.startsWith('/api/') || url.pathname === '/health') result.headers.set('cache-control', 'no-store');
      return result;
    } catch {
      return Response.json({ detail: { code: 'service_unavailable', message: 'The purchasing service is starting or temporarily unavailable. Please retry shortly; your saved cart is preserved.' } }, { status: 503, headers: { 'cache-control': 'no-store', 'retry-after': '10' } });
    }
  },
};
