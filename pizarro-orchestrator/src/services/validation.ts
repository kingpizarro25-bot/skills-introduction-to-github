import { z } from "zod";
import { getConfig } from "@/config/env";
import { describeProviders } from "@/providers/registry";
import type { WorkflowRequest } from "@/types/ai";

/**
 * Request validation for /api/run.
 *
 * Two layers: a static shape check (zod), then a semantic check against the
 * providers that actually exist and are configured right now.
 */

export const WorkflowRequestSchema = z
  .object({
    task: z.string().trim().min(1, "Task must not be empty"),
    mode: z.enum(["single", "parallel", "review", "consensus"]),
    providers: z.array(z.string().trim().min(1)).min(1, "Select at least one provider"),
    judge: z.string().trim().min(1).optional(),
    author: z.string().trim().min(1).optional(),
    reviewer: z.string().trim().min(1).optional(),
    maxOutputTokens: z.number().int().positive().optional(),
    temperature: z.number().min(0).max(2).optional(),
  })
  .strict();

export interface ValidationFailure {
  message: string;
  issues: string[];
}

export function validateWorkflowRequest(
  input: unknown,
): { data: WorkflowRequest } | { error: ValidationFailure } {
  const parsed = WorkflowRequestSchema.safeParse(input);
  if (!parsed.success) {
    return {
      error: {
        message: "Invalid request",
        issues: parsed.error.issues.map(
          (i) => `${i.path.join(".") || "body"}: ${i.message}`,
        ),
      },
    };
  }

  const request = parsed.data;
  const issues: string[] = [];
  const config = getConfig();

  if (request.task.length > config.MAX_TASK_LENGTH) {
    issues.push(
      `task: exceeds MAX_TASK_LENGTH (${request.task.length} > ${config.MAX_TASK_LENGTH} characters)`,
    );
  }

  const known = new Map(describeProviders().map((p) => [p.id, p]));
  const dedupedProviders = [...new Set(request.providers)];

  for (const id of dedupedProviders) {
    const info = known.get(id);
    if (!info) issues.push(`providers: unknown provider '${id}'`);
    else if (!info.enabled) issues.push(`providers: ${info.name} — ${info.status}`);
  }

  const checkRole = (role: string, id: string | undefined) => {
    if (!id) return;
    const info = known.get(id);
    if (!info) issues.push(`${role}: unknown provider '${id}'`);
    else if (!info.enabled) issues.push(`${role}: ${info.name} — ${info.status}`);
  };

  switch (request.mode) {
    case "single":
      if (dedupedProviders.length !== 1) {
        issues.push("providers: single mode takes exactly one provider");
      }
      break;

    case "review": {
      const author = request.author ?? dedupedProviders[0];
      const reviewer = request.reviewer ?? dedupedProviders[1];
      if (dedupedProviders.length > 2) {
        // Reject rather than quietly dropping the extras — a silently ignored
        // provider looks like a bug in the run history.
        issues.push("providers: review mode takes exactly two providers (author, then reviewer)");
      }
      if (!author || !reviewer) {
        issues.push("providers: review mode needs two providers (author, then reviewer)");
      } else if (author === reviewer) {
        issues.push("providers: review mode needs two different providers");
      }
      checkRole("author", request.author);
      checkRole("reviewer", request.reviewer);
      break;
    }

    case "consensus":
      if (dedupedProviders.length < 2) {
        issues.push("providers: consensus mode needs at least two providers");
      }
      if (!request.judge) issues.push("judge: required for consensus mode");
      checkRole("judge", request.judge);
      break;

    case "parallel":
      break;
  }

  if (issues.length > 0) {
    return { error: { message: "Request cannot be executed", issues } };
  }

  return { data: { ...request, providers: dedupedProviders } };
}
