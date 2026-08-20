import { NextResponse } from "next/server";
import { getConfig } from "@/config/env";
import { describeProviders } from "@/providers/registry";
import { safeHandler } from "../_lib/handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/providers — what the dashboard renders its toggles from.
 * Returns configuration *status* only; no keys, no URLs.
 */
export async function GET(): Promise<NextResponse> {
  return safeHandler("GET /api/providers", async () => {
    const config = getConfig();
    return NextResponse.json({
      ok: true,
      providers: describeProviders(),
      limits: {
        maxOutputTokens: config.MAX_OUTPUT_TOKENS,
        requestTimeoutMs: config.REQUEST_TIMEOUT_MS,
        maxRetries: config.MAX_RETRIES,
        maxTaskLength: config.MAX_TASK_LENGTH,
        maxProviderCallsPerRun: config.MAX_PROVIDER_CALLS_PER_RUN,
      },
      mockEnabled: config.ENABLE_MOCK_PROVIDER,
    });
  });
}
