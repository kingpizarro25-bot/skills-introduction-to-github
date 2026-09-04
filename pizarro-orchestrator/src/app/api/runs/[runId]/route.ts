import { NextResponse } from "next/server";
import { getRunStore } from "@/services/store";
import { jsonError, safeHandler } from "../../_lib/handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/runs/:runId — one stored run, including every provider response. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
): Promise<NextResponse> {
  return safeHandler("GET /api/runs/[runId]", async () => {
    const { runId } = await params;
    const run = await getRunStore().getRun(runId);
    if (!run) return jsonError(404, "Run not found");
    return NextResponse.json({ ok: true, run });
  });
}
