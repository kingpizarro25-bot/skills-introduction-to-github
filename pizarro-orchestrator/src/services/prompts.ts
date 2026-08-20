import type { ProviderResult } from "@/types/ai";

/**
 * Prompt templates for the multi-stage modes. Kept in one file so the wording
 * of a critique or a synthesis can be tuned without touching workflow logic.
 */

export const DEFAULT_SYSTEM =
  "You are a component of an automated multi-model orchestration system. " +
  "Answer directly and concisely. Do not ask clarifying questions — if the task " +
  "is ambiguous, state your assumption and answer anyway.";

export const REVIEWER_SYSTEM =
  "You are a rigorous technical reviewer inside an automated orchestration system. " +
  "You critique another model's answer. Be specific and terse. Do not rewrite the answer.";

export const JUDGE_SYSTEM =
  "You are the judge in an automated multi-model orchestration system. " +
  "You receive one task and several independent answers, and must produce a single " +
  "final answer. You are accountable for correctness, not for diplomacy.";

export function reviewPrompt(task: string, answer: string): string {
  return [
    "Another model was given the task below and produced the answer below.",
    "Critique the answer: list concrete errors, unsupported claims, and gaps.",
    "If the answer is sound, say so plainly and note only genuine weaknesses.",
    "",
    "=== TASK ===",
    task,
    "",
    "=== ANSWER TO REVIEW ===",
    answer,
    "",
    "=== YOUR CRITIQUE ===",
  ].join("\n");
}

export function revisionPrompt(task: string, answer: string, critique: string): string {
  return [
    "You previously answered the task below. A reviewer model critiqued your answer.",
    "Produce a corrected final answer. Incorporate the valid points.",
    "Where the critique is wrong, keep your position and briefly say why.",
    "Output only the final answer.",
    "",
    "=== TASK ===",
    task,
    "",
    "=== YOUR ORIGINAL ANSWER ===",
    answer,
    "",
    "=== REVIEWER CRITIQUE ===",
    critique,
    "",
    "=== YOUR FINAL ANSWER ===",
  ].join("\n");
}

/** Build the judge prompt from whichever provider answers actually succeeded. */
export function consensusPrompt(task: string, results: ProviderResult[]): string {
  const answers = results
    .filter((r): r is Extract<ProviderResult, { ok: true }> => r.ok)
    .map((r, i) => `--- ANSWER ${i + 1} — ${r.providerName} (${r.model}) ---\n${r.text}`)
    .join("\n\n");

  const failed = results
    .filter((r) => !r.ok)
    .map((r) => `${r.providerName} (unavailable)`)
    .join(", ");

  return [
    "Several models answered the same task independently. Produce ONE final answer.",
    "",
    "Requirements:",
    "1. Give the best single answer to the task.",
    "2. Then, under a heading 'Disagreements', list any material points where the",
    "   answers conflict, and say which you judge correct and why.",
    "3. If the models agree, say so explicitly instead of inventing conflict.",
    "4. Do not attribute a claim to a model that did not make it.",
    "",
    "=== TASK ===",
    task,
    "",
    "=== INDEPENDENT ANSWERS ===",
    answers || "(no model produced an answer)",
    ...(failed ? ["", `=== PROVIDERS THAT FAILED (no answer available) ===`, failed] : []),
    "",
    "=== FINAL ANSWER ===",
  ].join("\n");
}
