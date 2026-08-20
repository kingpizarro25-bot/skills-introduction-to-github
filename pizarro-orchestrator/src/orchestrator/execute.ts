import { ProviderError } from "@/providers/base";
import { requireProvider } from "@/providers/registry";
import { logger } from "@/services/logging";
import type {
  AIFailure,
  ProviderId,
  ProviderOptions,
  ProviderResult,
} from "@/types/ai";

/**
 * The single choke point for calling a provider.
 *
 * Turns exceptions into `AIFailure` values so one dead provider can never take
 * down a workflow, and enforces the per-run call budget (the stopping
 * condition — no unbounded agent loops).
 */

export class CallBudget {
  private used = 0;
  constructor(private readonly max: number) {}

  get remaining(): number {
    return Math.max(0, this.max - this.used);
  }

  /** Returns false when the budget is exhausted; callers must stop. */
  tryConsume(): boolean {
    if (this.used >= this.max) return false;
    this.used += 1;
    return true;
  }
}

function failure(
  provider: ProviderId,
  providerName: string,
  model: string,
  err: unknown,
  latencyMs: number,
): AIFailure {
  const pe =
    err instanceof ProviderError
      ? err
      : new ProviderError("unknown", err instanceof Error ? err.message : String(err));

  return {
    ok: false,
    provider,
    providerName,
    model,
    latencyMs,
    timestamp: new Date().toISOString(),
    error: {
      code: pe.code,
      message: pe.message,
      retryable: pe.retryable,
      attempts: pe.attempts,
    },
  };
}

/**
 * Call one provider and always resolve — never reject.
 * A missing API key surfaces as `not_configured`, not as a substituted answer.
 */
export async function callProvider(
  id: ProviderId,
  prompt: string,
  options: ProviderOptions = {},
  budget?: CallBudget,
): Promise<ProviderResult> {
  const started = Date.now();

  const resolved = requireProvider(id);
  if ("error" in resolved) {
    return failure(
      id,
      id,
      "unknown",
      new ProviderError("not_configured", resolved.error, { retryable: false }),
      Date.now() - started,
    );
  }
  const { provider } = resolved;

  if (budget && !budget.tryConsume()) {
    return failure(
      provider.id,
      provider.name,
      provider.model,
      new ProviderError(
        "bad_request",
        "Provider call budget for this workflow was exhausted (MAX_PROVIDER_CALLS_PER_RUN).",
        { retryable: false },
      ),
      Date.now() - started,
    );
  }

  try {
    const response = await provider.sendMessage(prompt, options);
    logger.info("provider call succeeded", {
      provider: provider.id,
      model: response.model,
      latencyMs: response.latencyMs,
      outputTokens: response.usage?.outputTokens,
    });
    return response;
  } catch (err) {
    const result = failure(provider.id, provider.name, provider.model, err, Date.now() - started);
    logger.warn("provider call failed", {
      provider: provider.id,
      code: result.error.code,
      attempts: result.error.attempts,
      message: result.error.message,
    });
    return result;
  }
}

/**
 * Fan out to many providers at once. Uses allSettled semantics via
 * `callProvider`, so a Perplexity outage still leaves OpenAI and Claude results.
 */
export async function callProvidersInParallel(
  ids: ProviderId[],
  prompt: string,
  options: ProviderOptions = {},
  budget?: CallBudget,
): Promise<ProviderResult[]> {
  const settled = await Promise.allSettled(
    ids.map((id) => callProvider(id, prompt, options, budget)),
  );

  return settled.map((outcome, i) =>
    outcome.status === "fulfilled"
      ? outcome.value
      : failure(ids[i], ids[i], "unknown", outcome.reason, 0),
  );
}

export function isSuccess(r: ProviderResult): r is Extract<ProviderResult, { ok: true }> {
  return r.ok;
}
