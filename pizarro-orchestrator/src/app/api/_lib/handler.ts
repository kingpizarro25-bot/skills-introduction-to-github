import { NextResponse } from "next/server";
import { EnvValidationError, getConfig } from "@/config/env";
import { logger } from "@/services/logging";
import { checkRateLimit, clientKey } from "@/services/rateLimit";

/**
 * Shared API concerns: rate limiting and safe error responses.
 *
 * "Safe" means the client gets a useful message and never a stack trace,
 * provider URL, or anything derived from a credential.
 */

export function jsonError(
  status: number,
  message: string,
  extra: Record<string, unknown> = {},
): NextResponse {
  return NextResponse.json({ ok: false, error: message, ...extra }, { status });
}

/** Returns a 429 response when the caller is over budget, otherwise null. */
export function enforceRateLimit(request: Request): NextResponse | null {
  const result = checkRateLimit(clientKey(request.headers));
  if (result.allowed) return null;

  return NextResponse.json(
    {
      ok: false,
      error: `Rate limit exceeded (${result.limit} requests per window). Try again in ${result.retryAfterSeconds}s.`,
    },
    {
      status: 429,
      headers: {
        "retry-after": String(result.retryAfterSeconds),
        "x-ratelimit-limit": String(result.limit),
        "x-ratelimit-remaining": "0",
      },
    },
  );
}

/** Wrap a handler so nothing internal ever leaks to the client. */
export async function safeHandler(
  route: string,
  fn: () => Promise<NextResponse>,
): Promise<NextResponse> {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof EnvValidationError) {
      logger.error("invalid environment configuration", { route, issues: err.issues });
      return jsonError(500, "Server configuration is invalid. Check the server logs.");
    }
    logger.error("unhandled API error", {
      route,
      reason: err instanceof Error ? err.message : String(err),
    });
    return jsonError(500, "Internal server error");
  }
}

/** Touch config early so a malformed .env fails loudly at request time. */
export function assertConfigured(): void {
  getConfig();
}
