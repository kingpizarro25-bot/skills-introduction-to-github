import type { ProviderOptions, WorkflowStep } from "@/types/ai";
import { CallBudget, callProvider, isSuccess } from "./execute";
import {
  DEFAULT_SYSTEM,
  REVIEWER_SYSTEM,
  reviewPrompt,
  revisionPrompt,
} from "@/services/prompts";

/**
 * REVIEW — author drafts, reviewer critiques, author revises. Exactly three
 * provider calls, no loop: the workflow stops after one revision pass.
 *
 * If the author fails there is nothing to review, so the workflow stops early
 * and reports the failure rather than pressing on with an empty answer.
 */
export async function runReview(
  task: string,
  authorId: string,
  reviewerId: string,
  options: ProviderOptions,
  budget: CallBudget,
): Promise<WorkflowStep[]> {
  const steps: WorkflowStep[] = [];

  const draft = await callProvider(
    authorId,
    task,
    { system: DEFAULT_SYSTEM, ...options },
    budget,
  );
  steps.push({ stage: "draft", provider: authorId, result: draft });
  if (!isSuccess(draft)) return steps;

  const critique = await callProvider(
    reviewerId,
    reviewPrompt(task, draft.text),
    { system: REVIEWER_SYSTEM, ...options },
    budget,
  );
  steps.push({ stage: "critique", provider: reviewerId, result: critique });
  // Without a critique the draft is still a valid answer, so stop here and keep it.
  if (!isSuccess(critique)) return steps;

  const revision = await callProvider(
    authorId,
    revisionPrompt(task, draft.text, critique.text),
    { system: DEFAULT_SYSTEM, ...options },
    budget,
  );
  steps.push({ stage: "revision", provider: authorId, result: revision });

  return steps;
}
