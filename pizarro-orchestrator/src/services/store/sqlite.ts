import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import type { WorkflowRun, ProviderResult, WorkflowStep, WorkflowMode, RunStatus } from "@/types/ai";
import type { RunStore } from "./types";

/**
 * SQLite store built on Node's built-in `node:sqlite` — no native build step.
 *
 * Rows keep the schema from the spec (run_id, task, mode, providers, responses,
 * judge, final_response, status, created_at) with JSON columns for the arrays.
 */
interface RunRow {
  run_id: string;
  task: string;
  mode: string;
  providers: string;
  responses: string;
  steps: string;
  judge: string | null;
  final_response: string | null;
  status: string;
  error: string | null;
  duration_ms: number;
  created_at: string;
  completed_at: string;
}

export class SqliteRunStore implements RunStore {
  readonly driver = "sqlite";
  private db: DatabaseSync;

  constructor(dbPath: string) {
    const absolute = resolve(dbPath);
    mkdirSync(dirname(absolute), { recursive: true });
    this.db = new DatabaseSync(absolute);
    this.db.exec(`
      PRAGMA journal_mode = WAL;
      CREATE TABLE IF NOT EXISTS runs (
        run_id         TEXT PRIMARY KEY,
        task           TEXT NOT NULL,
        mode           TEXT NOT NULL,
        providers      TEXT NOT NULL,
        responses      TEXT NOT NULL,
        steps          TEXT NOT NULL,
        judge          TEXT,
        final_response TEXT,
        status         TEXT NOT NULL,
        error          TEXT,
        duration_ms    INTEGER NOT NULL DEFAULT 0,
        created_at     TEXT NOT NULL,
        completed_at   TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC);
    `);
  }

  async saveRun(run: WorkflowRun): Promise<void> {
    this.db
      .prepare(
        `INSERT OR REPLACE INTO runs
         (run_id, task, mode, providers, responses, steps, judge, final_response,
          status, error, duration_ms, created_at, completed_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        run.runId,
        run.task,
        run.mode,
        JSON.stringify(run.providers),
        JSON.stringify(run.responses),
        JSON.stringify(run.steps),
        run.judge ?? null,
        run.finalResponse,
        run.status,
        run.error ?? null,
        run.durationMs,
        run.createdAt,
        run.completedAt,
      );
  }

  async getRun(runId: string): Promise<WorkflowRun | null> {
    const row = this.db.prepare("SELECT * FROM runs WHERE run_id = ?").get(runId) as
      | RunRow
      | undefined;
    return row ? rowToRun(row) : null;
  }

  async listRuns(limit = 25): Promise<WorkflowRun[]> {
    const rows = this.db
      .prepare("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?")
      .all(limit) as unknown as RunRow[];
    return rows.map(rowToRun);
  }

  async close(): Promise<void> {
    this.db.close();
  }
}

function rowToRun(row: RunRow): WorkflowRun {
  return {
    runId: row.run_id,
    task: row.task,
    mode: row.mode as WorkflowMode,
    providers: JSON.parse(row.providers) as string[],
    responses: JSON.parse(row.responses) as ProviderResult[],
    steps: JSON.parse(row.steps) as WorkflowStep[],
    judge: row.judge ?? undefined,
    finalResponse: row.final_response,
    status: row.status as RunStatus,
    error: row.error ?? undefined,
    durationMs: row.duration_ms,
    createdAt: row.created_at,
    completedAt: row.completed_at,
  };
}
