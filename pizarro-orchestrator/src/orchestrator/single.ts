import type { ProviderOptions, WorkflowStep } from "@/types/ai";
import { CallBudget, callProvider } from "./execute";
import { DEFAULT_SYSTEM } from "@/services/prompts";

/** SINGLE — one task, one model. */
export async function runSingle(
  task: string,
  providerId: string,
  options: ProviderOptions,
  budget: CallBudget,
): Promise<WorkflowStep[]> {
  const result = await callProvider(
    providerId,
    task,
    { system: DEFAULT_SYSTEM, ...options },
    budget,
  );
  return [{ stage: "answer", provider: providerId, result }];
}
