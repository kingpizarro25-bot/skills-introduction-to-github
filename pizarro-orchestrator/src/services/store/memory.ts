import type { WorkflowRun } from "@/types/ai";
import type { RunStore } from "./types";

/** In-process store. Used for tests and as a fallback when SQLite is unavailable. */
export class MemoryRunStore implements RunStore {
  readonly driver = "memory";
  private runs = new Map<string, WorkflowRun>();

  async saveRun(run: WorkflowRun): Promise<void> {
    this.runs.set(run.runId, run);
  }

  async getRun(runId: string): Promise<WorkflowRun | null> {
    return this.runs.get(runId) ?? null;
  }

  async listRuns(limit = 25): Promise<WorkflowRun[]> {
    return [...this.runs.values()]
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, limit);
  }

  async close(): Promise<void> {
    this.runs.clear();
  }
}
