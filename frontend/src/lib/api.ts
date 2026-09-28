/**
 * LIVO Footwear ERP - Resilient First-Party API Client
 * Wraps browser fetch with:
 * 1. First-party reverse proxy domain unification (/api/backend)
 * 2. End-to-end correlation tracing & support reference capture (X-Request-ID)
 * 3. Offline mutation interception, outbox queuing, and idempotency headers.
 */
import { enqueueMutation } from "./offlineQueue";

/**
 * Resolves the target API URL through the first-party reverse proxy.
 * Routes /api/v1/* through /api/backend/v1/* in production environments,
 * converting fragile 3rd-party cross-domain cookies into rock-solid 1st-party cookies.
 */
export function resolveApiUrl(pathOrUrl: string): string {
  if (/^https?:\/\//i.test(pathOrUrl) || pathOrUrl.startsWith("/api/backend")) {
    return pathOrUrl;
  }

  const isProd =
    process.env.NODE_ENV === "production" ||
    (typeof window !== "undefined" &&
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1");

  if (isProd && pathOrUrl.startsWith("/api/")) {
    return pathOrUrl.replace(/^\/api\//, "/api/backend/");
  }

  return pathOrUrl;
}

/**
 * Extracts correlation tracking reference from response headers.
 */
export function extractSupportReference(source: Response | Headers | null | undefined): string {
  if (!source) return "req_unavailable";
  const headers = "headers" in source ? source.headers : source;
  return headers.get("X-Request-ID") || "req_unavailable";
}

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method || "GET").toUpperCase();
  const isMutation = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
  const rawEndpoint = typeof input === "string" ? input : input.toString();
  const targetUrl = resolveApiUrl(rawEndpoint);

  // 1. If explicitly offline and mutating, directly buffer into outbox
  if (typeof navigator !== "undefined" && !navigator.onLine && isMutation) {
    let payload = null;
    if (init?.body && typeof init.body === "string") {
      try {
        payload = JSON.parse(init.body);
      } catch {
        payload = init.body;
      }
    }

    const queued = await enqueueMutation({
      endpoint: rawEndpoint,
      method,
      payload,
    });

    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("livo:toast", {
          detail: {
            message: "Offline: Transaction saved to local terminal queue.",
            type: "warning",
          },
        })
      );
    }

    // Return optimistic 202 Accepted response
    return new Response(
      JSON.stringify({
        status: "queued",
        offline: true,
        queue_id: queued.id,
        message: "Saved to local terminal queue. Will sync automatically when connection restores.",
      }),
      {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 2. Attempt online network request
  try {
    const res = await fetch(targetUrl, init);

    // Capture X-Request-ID on errors (4xx / 5xx)
    if (!res.ok) {
      const requestId = res.headers.get("X-Request-ID") || `req_${Math.random().toString(16).slice(2, 14)}`;
      const supportRef = `Transaction failed. Support reference: [${requestId}]`;

      // Log directly to browser console for immediate support triage
      console.error(`[LIVO API Error ${res.status}] ${rawEndpoint} — ${supportRef}`);

      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("livo:api-error", {
            detail: {
              status: res.status,
              endpoint: rawEndpoint,
              requestId,
              message: supportRef,
            },
          })
        );
      }
    }

    return res;
  } catch (error: any) {
    // 3. If network fails mid-flight on a mutating request, buffer into outbox
    if (isMutation) {
      let payload = null;
      if (init?.body && typeof init.body === "string") {
        try {
          payload = JSON.parse(init.body);
        } catch {
          payload = init.body;
        }
      }

      const queued = await enqueueMutation({
        endpoint: rawEndpoint,
        method,
        payload,
      });

      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("livo:toast", {
            detail: {
              message: "Network dropped: Transaction buffered to terminal outbox.",
              type: "warning",
            },
          })
        );
      }

      return new Response(
        JSON.stringify({
          status: "queued",
          offline: true,
          queue_id: queued.id,
          message: "Saved to local terminal queue. Will sync automatically when connection restores.",
        }),
        {
          status: 202,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    console.error(`[LIVO Network Error] ${rawEndpoint}:`, error);
    throw error;
  }
}
