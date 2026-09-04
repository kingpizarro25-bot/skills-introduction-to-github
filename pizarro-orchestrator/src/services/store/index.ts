import { getConfig } from "@/config/env";
import { logger } from "@/services/logging";
import { MemoryRunStore } from "./memory";
import type { RunStore } from "./types";

export type { RunStore } from "./types";
export { MemoryRunStore } from "./memory";

let instance: RunStore | null = null;

/**
 * Process-wide store singleton.
 *
 * Swap in PostgreSQL/Supabase by adding a `PostgresRunStore` and another branch
 * here; every caller goes through `RunStore` so nothing else changes.
 */
export function getRunStore(): RunStore {
  if (instance) return instance;

  const config = getConfig();
  if (config.STORE_DRIVER === "memory") {
    instance = new MemoryRunStore();
    return instance;
  }

  try {
    // Required lazily so environments without node:sqlite still boot.
    const { SqliteRunStore } = require("./sqlite") as typeof import("./sqlite");
    instance = new SqliteRunStore(config.DB_PATH);
  } catch (err) {
    logger.warn("SQLite store unavailable, falling back to in-memory history", {
      reason: err instanceof Error ? err.message : String(err),
    });
    instance = new MemoryRunStore();
  }
  return instance;
}

/** Test helper. */
export function setRunStore(store: RunStore | null): void {
  instance = store;
}
