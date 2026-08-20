import type { ProviderOptions, WorkflowStep } from "@/types/ai";
import { CallBudget, callProvidersInParallel } from "./execute";
import { DEFAULT_SYSTEM } from "@/services/prompts";

/**
 * PARALLEL — same task to every selected provider simultaneously.
 * Failures are isolated: each provider's outcome stands on its own.
 */
export async function runParallel(
  task: string,
  providerIds: string[],
  options: ProviderOptions,
  budget: CallBudget,
): Promise<WorkflowStep[]> {
  const results = await callProvidersInParallel(
    providerIds,
    task,
    { system: DEFAULT_SYSTEM, ...options },
    budget,
  );
  return results.map((result, i) => ({
    stage: "answer",
    provider: providerIds[i],
    result,
  }));
}
