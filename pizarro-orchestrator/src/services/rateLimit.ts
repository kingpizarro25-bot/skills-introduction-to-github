import { getConfig } from "@/config/env";

/**
 * Fixed-window in-memory rate limiter.
 *
 * Adequate for a single-process V1. For multi-instance deployments, replace the
 * `hits` map with Redis — the `checkRateLimit` signature stays the same.
 */
interface Window {
  count: number;
  resetAt: number;
}

const hits = new Map<string, Window>();

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  limit: number;
  resetAt: number;
  retryAfterSeconds: number;
}

export function checkRateLimit(key: string, now = Date.now()): RateLimitResult {
  const { RATE_LIMIT_MAX: limit, RATE_LIMIT_WINDOW_MS: windowMs } = getConfig();

  // Opportunistic cleanup so the map cannot grow without bound.
  if (hits.size > 10_000) {
    for (const [k, w] of hits) if (w.resetAt <= now) hits.delete(k);
  }

  const existing = hits.get(key);
  const window: Window =
    !existing || existing.resetAt <= now ? { count: 0, resetAt: now + windowMs } : existing;

  window.count += 1;
  hits.set(key, window);

  const allowed = window.count <= limit;
  return {
    allowed,
    limit,
    remaining: Math.max(0, limit - window.count),
    resetAt: window.resetAt,
    retryAfterSeconds: Math.max(1, Math.ceil((window.resetAt - now) / 1000)),
  };
}

/** Best-effort client identity. Falls back to a shared bucket behind proxies. */
export function clientKey(headers: Headers): string {
  const forwarded = headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return headers.get("x-real-ip") ?? "unknown";
}

/** Test helper. */
export function resetRateLimits(): void {
  hits.clear();
}
