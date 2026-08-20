import { randomUUID } from "node:crypto";
import { getConfig } from "@/config/env";
import { logger } from "@/services/logging";
import { getRunStore } from "@/services/store";
import type {
  ProviderOptions,
  RunStatus,
  WorkflowRequest,
  WorkflowRun,
  WorkflowStep,
} from "@/types/ai";
import { CallBudget, isSuccess } from "./execute";
import { runConsensus } from "./consensus";
import { runParallel } from "./parallel";
import { runReview } from "./review";
import { runSingle } from "./single";

/**
 * TASK ROUTER — the entry point the API layer calls.
 *
 * Responsibilities: pick the workflow for the mode, enforce the per-run call
 * budget, derive the final answer and status, and log the run. It knows nothing
 * about any specific provider.
 */

export class WorkflowError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkflowError";
  }
}

/** Which step's text becomes FINAL SYNTHESIS, per mode. */
function selectFinal(mode: WorkflowRequest["mode"], steps: WorkflowStep[]): string | null {
  /** Text of the most recent *successful* step at the given stage. */
  const textOf = (stage: string): string | null => {
    for (let i = steps.length - 1; i >= 0; i--) {
      const step = steps[i];
      if (step.stage === stage && isSuccess(step.result)) return step.result.text;
    }
    return null;
  };

  switch (mode) {
    case "single":
      return textOf("answer");

    // Prefer the revised answer; fall back to the draft if the revision failed.
    case "review":
      return textOf("revision") ?? textOf("draft");

    case "consensus":
      return textOf("synthesis");

    case "parallel":
    default:
      // Parallel has no single winner by design — the per-provider panels are
      // the result. Returning null is honest; anointing one model would not be.
      return null;
  }
}

function deriveStatus(
  mode: WorkflowRequest["mode"],
  steps: WorkflowStep[],
  finalResponse: string | null,
): RunStatus {
  const ok = steps.filter((s) => isSuccess(s.result)).length;
  if (ok === 0) return "failed";
  if (ok < steps.length) return "partial";
  // Every mode except parallel is only fully successful if it produced a final answer.
  if (mode !== "parallel" && finalResponse === null) return "partial";
  return "success";
}

/** Run a workflow end to end and persist it. Never throws for provider failures. */
export async function orchestrate(request: WorkflowRequest): Promise<WorkflowRun> {
  const config = getConfig();
  const runId = randomUUID();
  const createdAt = new Date().toISOString();
  const started = Date.now();
  const budget = new CallBudget(config.MAX_PROVIDER_CALLS_PER_RUN);

  const options: ProviderOptions = {
    ...(request.maxOutputTokens !== undefined
      ? { maxOutputTokens: request.maxOutputTokens }
      : {}),
    ...(request.temperature !== undefined ? { temperature: request.temperature } : {}),
  };

  logger.info("workflow started", {
    runId,
    mode: request.mode,
    providers: request.providers,
    judge: request.judge,
  });

  let steps: WorkflowStep[] = [];
  let error: string | undefined;

  try {
    steps = await dispatch(request, options, budget);
  } catch (err) {
    // Only genuine programming/validation errors reach here; provider failures
    // are values, not exceptions.
    error = err instanceof Error ? err.message : String(err);
    logger.error("workflow aborted", { runId, error });
  }

  const finalResponse = selectFinal(request.mode, steps);
  const run: WorkflowRun = {
    runId,
    task: request.task,
    mode: request.mode,
    providers: request.providers,
    responses: steps.map((s) => s.result),
    steps,
    judge: request.judge,
    finalResponse,
    status: error ? "failed" : deriveStatus(request.mode, steps, finalResponse),
    error,
    durationMs: Date.now() - started,
    createdAt,
    completedAt: new Date().toISOString(),
  };

  try {
    await getRunStore().saveRun(run);
  } catch (err) {
    // History is useful, not load-bearing: never fail a completed run over it.
    logger.error("failed to persist run", {
      runId,
      reason: err instanceof Error ? err.message : String(err),
    });
  }

  logger.info("workflow finished", {
    runId,
    status: run.status,
    durationMs: run.durationMs,
    calls: run.responses.length,
  });

  return run;
}

function dispatch(
  request: WorkflowRequest,
  options: ProviderOptions,
  budget: CallBudget,
): Promise<WorkflowStep[]> {
  const { task, mode, providers } = request;

  switch (mode) {
    case "single":
      return runSingle(task, providers[0], options, budget);

    case "parallel":
      return runParallel(task, providers, options, budget);

    case "review": {
      const author = request.author ?? providers[0];
      const reviewer = request.reviewer ?? providers[1];
      if (!author || !reviewer) {
        throw new WorkflowError("Review mode needs an author and a reviewer provider.");
      }
      return runReview(task, author, reviewer, options, budget);
    }

    case "consensus": {
      const judge = request.judge;
      if (!judge) throw new WorkflowError("Consensus mode requires a judge provider.");
      return runConsensus(task, providers, judge, options, budget);
    }

    default: {
      const exhaustive: never = mode;
      throw new WorkflowError(`Unsupported mode: ${String(exhaustive)}`);
    }
  }
}
