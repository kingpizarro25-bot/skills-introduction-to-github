import { NextResponse } from "next/server";
import { validateEnvOnStartup } from "@/config/env";
import { describeProviders } from "@/providers/registry";
import { getRunStore } from "@/services/store";
import { safeHandler } from "../_lib/handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/health — boot diagnostics: config warnings, provider readiness, store driver. */
export async function GET(): Promise<NextResponse> {
  return safeHandler("GET /api/health", async () => {
    const warnings = validateEnvOnStartup();
    const providers = describeProviders();
    return NextResponse.json({
      ok: true,
      store: getRunStore().driver,
      configuredProviders: providers.filter((p) => p.enabled).map((p) => p.id),
      warnings,
    });
  });
}
