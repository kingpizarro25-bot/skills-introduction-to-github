import type { WorkflowRun } from "@/types/ai";

/**
 * Storage contract. The orchestrator only ever sees this interface, so swapping
 * SQLite for PostgreSQL/Supabase later means writing one new implementation and
 * changing the factory in `index.ts` — no call sites change.
 */
export interface RunStore {
  readonly driver: string;
  saveRun(run: WorkflowRun): Promise<void>;
  getRun(runId: string): Promise<WorkflowRun | null>;
  listRuns(limit?: number): Promise<WorkflowRun[]>;
  close(): Promise<void>;
}
