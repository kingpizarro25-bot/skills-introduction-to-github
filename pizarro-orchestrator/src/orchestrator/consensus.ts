import type { ProviderOptions, WorkflowStep } from "@/types/ai";
import { CallBudget, callProvider, callProvidersInParallel, isSuccess } from "./execute";
import { DEFAULT_SYSTEM, JUDGE_SYSTEM, consensusPrompt } from "@/services/prompts";

/**
 * CONSENSUS — every selected provider answers independently, then a judge model
 * receives the task plus all answers and produces one final answer, naming the
 * disagreements.
 *
 * The judge runs on whatever answers succeeded. If none did, the judge is not
 * called at all — there is nothing to synthesize and calling it would invent one.
 */
export async function runConsensus(
  task: string,
  providerIds: string[],
  judgeId: string,
  options: ProviderOptions,
  budget: CallBudget,
): Promise<WorkflowStep[]> {
  const answers = await callProvidersInParallel(
    providerIds,
    task,
    { system: DEFAULT_SYSTEM, ...options },
    budget,
  );

  const steps: WorkflowStep[] = answers.map((result, i) => ({
    stage: "answer",
    provider: providerIds[i],
    result,
  }));

  if (!answers.some(isSuccess)) return steps;

  const verdict = await callProvider(
    judgeId,
    consensusPrompt(task, answers),
    { system: JUDGE_SYSTEM, ...options },
    budget,
  );
  steps.push({ stage: "synthesis", provider: judgeId, result: verdict });

  return steps;
}
