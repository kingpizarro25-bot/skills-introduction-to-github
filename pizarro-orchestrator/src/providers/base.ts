import type { ErrorCode, ProviderId, ProviderOptions } from "@/types/ai";
import { getConfig } from "@/config/env";

/**
 * Shared transport for every provider adapter: one place that owns timeouts,
 * retry policy and error classification. Adapters only translate request and
 * response shapes.
 */

export class ProviderError extends Error {
  readonly code: ErrorCode;
  readonly retryable: boolean;
  /** HTTP status when the failure came from the provider's API. */
  readonly status?: number;
  attempts = 1;

  constructor(
    code: ErrorCode,
    message: string,
    opts: { retryable?: boolean; status?: number } = {},
  ) {
    super(message);
    this.name = "ProviderError";
    this.code = code;
    this.status = opts.status;
    this.retryable = opts.retryable ?? defaultRetryable(code);
  }
}

function defaultRetryable(code: ErrorCode): boolean {
  return code === "timeout" || code === "rate_limited" || code === "server_error" || code === "network";
}

export function notConfigured(providerName: string, envVar: string): ProviderError {
  return new ProviderError(
    "not_configured",
    `Provider not configured — set ${envVar} to enable ${providerName}.`,
    { retryable: false },
  );
}

function classifyStatus(status: number): ErrorCode {
  if (status === 401 || status === 403) return "auth";
  if (status === 408) return "timeout";
  if (status === 429) return "rate_limited";
  if (status >= 500) return "server_error";
  if (status >= 400) return "bad_request";
  return "unknown";
}

/**
 * Provider APIs put the useful part of an error in different places. Dig it out
 * without ever echoing back headers (which carry the Authorization value).
 */
function extractApiMessage(body: unknown, fallback: string): string {
  if (typeof body === "string" && body.trim()) return body.slice(0, 500);
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    const error = record.error;
    if (typeof error === "string") return error.slice(0, 500);
    if (error && typeof error === "object") {
      const msg = (error as Record<string, unknown>).message;
      if (typeof msg === "string") return msg.slice(0, 500);
    }
    if (typeof record.message === "string") return record.message.slice(0, 500);
    if (typeof record.detail === "string") return record.detail.slice(0, 500);
  }
  return fallback;
}

export interface RequestSpec {
  url: string;
  headers: Record<string, string>;
  body: unknown;
}

export interface ResolvedLimits {
  maxOutputTokens: number;
  timeoutMs: number;
  maxRetries: number;
  temperature?: number;
}

/** Apply per-request overrides on top of the configured cost controls. */
export function resolveLimits(options: ProviderOptions = {}): ResolvedLimits {
  const config = getConfig();
  return {
    maxOutputTokens: Math.min(
      options.maxOutputTokens ?? config.MAX_OUTPUT_TOKENS,
      config.MAX_OUTPUT_TOKENS,
    ),
    timeoutMs: Math.min(options.timeoutMs ?? config.REQUEST_TIMEOUT_MS, config.REQUEST_TIMEOUT_MS),
    maxRetries: Math.min(options.maxRetries ?? config.MAX_RETRIES, config.MAX_RETRIES),
    temperature: options.temperature,
  };
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Exponential backoff with jitter, capped so a run can never stall for minutes. */
function backoffDelay(attempt: number): number {
  const base = Math.min(500 * 2 ** attempt, 8_000);
  return base + Math.floor(Math.random() * 250);
}

/**
 * POST JSON with a wall-clock timeout and bounded retries.
 *
 * The retry budget is finite by construction — `maxRetries` is clamped to
 * MAX_RETRIES (<= 5), so a single call can never loop indefinitely.
 */
export async function postJson<T>(
  spec: RequestSpec,
  limits: ResolvedLimits,
  externalSignal?: AbortSignal,
): Promise<T> {
  let lastError: ProviderError = new ProviderError("unknown", "Request never ran");

  for (let attempt = 0; attempt <= limits.maxRetries; attempt++) {
    const timer = AbortSignal.timeout(limits.timeoutMs);
    const signal = externalSignal
      ? AbortSignal.any([timer, externalSignal])
      : timer;

    try {
      const response = await fetch(spec.url, {
        method: "POST",
        headers: { "content-type": "application/json", ...spec.headers },
        body: JSON.stringify(spec.body),
        signal,
      });

      const raw = await response.text();
      let parsed: unknown = raw;
      try {
        parsed = raw ? JSON.parse(raw) : {};
      } catch {
        /* keep the raw text; some gateways return HTML error pages */
      }

      if (!response.ok) {
        const code = classifyStatus(response.status);
        lastError = new ProviderError(
          code,
          extractApiMessage(parsed, `HTTP ${response.status} ${response.statusText}`),
          { status: response.status },
        );
      } else {
        return parsed as T;
      }
    } catch (err) {
      lastError = toProviderError(err, externalSignal);
    }

    lastError.attempts = attempt + 1;

    // Stop immediately on permanent failures (bad key, bad request, cancelled).
    if (!lastError.retryable || attempt === limits.maxRetries) break;
    await sleep(backoffDelay(attempt));
  }

  throw lastError;
}

function toProviderError(err: unknown, externalSignal?: AbortSignal): ProviderError {
  if (err instanceof ProviderError) return err;
  if (err instanceof Error) {
    if (externalSignal?.aborted) {
      return new ProviderError("unknown", "Request cancelled by caller", { retryable: false });
    }
    if (err.name === "TimeoutError" || err.name === "AbortError") {
      return new ProviderError("timeout", "Provider request timed out");
    }
    // fetch() wraps DNS/TLS/socket problems in a generic TypeError.
    if (err.name === "TypeError") {
      return new ProviderError("network", `Network error contacting provider: ${err.message}`);
    }
    return new ProviderError("unknown", err.message);
  }
  return new ProviderError("unknown", String(err));
}

/** Uniform Authorization header builder, so no adapter hand-rolls it. */
export function bearer(apiKey: string): Record<string, string> {
  return { authorization: `Bearer ${apiKey}` };
}

export function nowIso(): string {
  return new Date().toISOString();
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

/** Both OpenAI and Perplexity speak this shape. */
export function chatMessages(prompt: string, system?: string): ChatMessage[] {
  const messages: ChatMessage[] = [];
  if (system) messages.push({ role: "system", content: system });
  messages.push({ role: "user", content: prompt });
  return messages;
}

export type { ProviderId };
