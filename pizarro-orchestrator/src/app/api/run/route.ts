import { NextResponse } from "next/server";
import { orchestrate } from "@/orchestrator";
import { validateWorkflowRequest } from "@/services/validation";
import { enforceRateLimit, jsonError, safeHandler } from "../_lib/handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * POST /api/run — execute one workflow.
 *
 * All provider calls happen here, server-side. API keys never cross to the
 * browser. Provider failures come back as data inside a 200 response; only
 * bad input or a broken server produces a non-2xx.
 */
export async function POST(request: Request): Promise<NextResponse> {
  return safeHandler("POST /api/run", async () => {
    const limited = enforceRateLimit(request);
    if (limited) return limited;

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return jsonError(400, "Request body must be valid JSON");
    }

    const validated = validateWorkflowRequest(body);
    if ("error" in validated) {
      return jsonError(400, validated.error.message, { issues: validated.error.issues });
    }

    const run = await orchestrate(validated.data);
    return NextResponse.json({ ok: true, run });
  });
}
