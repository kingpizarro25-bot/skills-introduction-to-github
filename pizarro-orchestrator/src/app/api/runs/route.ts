import { NextResponse } from "next/server";
import { getRunStore } from "@/services/store";
import { safeHandler } from "../_lib/handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/runs?limit=25 — execution history, newest first. */
export async function GET(request: Request): Promise<NextResponse> {
  return safeHandler("GET /api/runs", async () => {
    const raw = Number(new URL(request.url).searchParams.get("limit") ?? 25);
    const limit = Number.isFinite(raw) ? Math.min(Math.max(Math.trunc(raw), 1), 100) : 25;

    const runs = await getRunStore().listRuns(limit);
    return NextResponse.json({ ok: true, runs });
  });
}
