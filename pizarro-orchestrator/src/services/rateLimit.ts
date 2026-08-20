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

/**
 * Client identity for rate limiting.
 *
 * `X-Forwarded-For` is set by the caller, so trusting it by default would make
 * the limit meaningless: send a fresh value per request and every request gets
 * its own bucket. So it is only honoured when TRUST_PROXY_HEADERS=true, which
 * you set when the app genuinely sits behind a proxy that overwrites the header.
 *
 * Off (the default), every caller shares one bucket. That is the right shape for
 * a single-operator deployment: the limit still caps total spend.
 */
export function clientKey(headers: Headers): string {
  if (!getConfig().TRUST_PROXY_HEADERS) return "shared";

  const forwarded = headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return headers.get("x-real-ip") ?? "unknown";
}

/** Test helper. */
export function resetRateLimits(): void {
  hits.clear();
}
