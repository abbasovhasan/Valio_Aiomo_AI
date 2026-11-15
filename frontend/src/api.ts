// Session changes retire old requests before another role can update the screen.
let sessionGeneration = 0;
const requests = new Set<AbortController>();

export function retireSessionRequests() {
  sessionGeneration += 1;
  for (const controller of requests) controller.abort();
  requests.clear();
}

export function sessionInterrupted(error: unknown) {
  return error instanceof Error && error.name === "AbortError";
}

export function announceSessionChange() {
  try { localStorage.setItem("aimo-session-change", `${Date.now()}-${Math.random()}`); }
  catch { /* Focus checks still restore the server's current identity. */ }
}

export async function api(path: string, options: RequestInit = {}) {
  const generation = sessionGeneration;
  // Public feature discovery carries no identity or protected data.
  const sessionScoped = !(path === "/auth/demo" && (!options.method || options.method === "GET"));
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (options.signal?.aborted) abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  if (sessionScoped) requests.add(controller);
  const current = () => {
    if ((sessionScoped && generation !== sessionGeneration) || controller.signal.aborted) {
      throw new DOMException("The session changed. The previous request was discarded.", "AbortError");
    }
  };
  try {
    const headers = new Headers(options.headers);
    if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    const response = await fetch("/api/v1" + path, { ...options, credentials: "same-origin", headers, signal: controller.signal });
    const data = await response.json().catch(() => ({}));
    current();
    const authentication = path.startsWith("/auth/") || path === "/session";
    if (response.status === 401 && !authentication) window.dispatchEvent(new Event("aimo-session-expired"));
    if (response.status === 403 && !authentication) window.dispatchEvent(new Event("aimo-session-check"));
    if (!response.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail
        : Array.isArray(data.detail) ? data.detail.slice(0, 3).map((item: {loc?: string[]; msg?: string}) => `${String(item.loc?.at(-1) || "Input")}: ${item.msg}`).join(". ")
          : data.detail?.message || "The service could not complete this request. Try again.");
    }
    return data;
  } finally {
    requests.delete(controller);
    options.signal?.removeEventListener("abort", abort);
  }
}
