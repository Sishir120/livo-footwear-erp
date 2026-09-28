/**
 * LIVO Footwear ERP - Resilient API Client
 * Wraps browser fetch with offline mutation interception, outbox queuing, and idempotency headers.
 */
import { enqueueMutation } from "./offlineQueue";

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method || "GET").toUpperCase();
  const isMutation = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
  const endpoint = typeof input === "string" ? input : input.toString();

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
      endpoint,
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
    const res = await fetch(input, init);
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
        endpoint,
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

    throw error;
  }
}
