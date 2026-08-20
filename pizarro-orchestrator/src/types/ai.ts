/**
 * Core contracts for the orchestrator.
 *
 * Everything the orchestrator knows about a model provider lives behind
 * `AIProvider`. Adding Gemini, Grok or a local model means writing one adapter
 * that satisfies this interface and registering it — no orchestrator changes.
 */

export type ProviderId = string;

/** Stable, machine-readable failure classes used for retry decisions and UI. */
export type ErrorCode =
  | "not_configured"
  | "timeout"
  | "rate_limited"
  | "auth"
  | "bad_request"
  | "server_error"
  | "network"
  | "unknown";

export interface ProviderOptions {
  /** Hard cap on tokens the provider may generate. Defaults to MAX_OUTPUT_TOKENS. */
  maxOutputTokens?: number;
  temperature?: number;
  /** Per-request wall clock budget. Defaults to REQUEST_TIMEOUT_MS. */
  timeoutMs?: number;
  /** Retries for *transient* failures only. Defaults to MAX_RETRIES. */
  maxRetries?: number;
  /** Optional system instruction. */
  system?: string;
  /** Lets a caller cancel an in-flight request. */
  signal?: AbortSignal;
}

export interface TokenUsage {
  inputTokens?: number;
  outputTokens?: number;
}

/** A successful call to a provider. */
export interface AIResponse {
  ok: true;
  provider: ProviderId;
  providerName: string;
  model: string;
  text: string;
  latencyMs: number;
  timestamp: string;
  usage?: TokenUsage;
  finishReason?: string;
  /** Provider-specific extras, e.g. Perplexity citations. Never contains secrets. */
  meta?: Record<string, unknown>;
}

/** A failed call. Failures are values, not exceptions, once they reach the orchestrator. */
export interface AIFailure {
  ok: false;
  provider: ProviderId;
  providerName: string;
  model: string;
  latencyMs: number;
  timestamp: string;
  error: {
    code: ErrorCode;
    message: string;
    retryable: boolean;
    /** How many attempts were made in total (1 = no retry happened). */
    attempts: number;
  };
}

export type ProviderResult = AIResponse | AIFailure;

export interface AIProvider {
  /** Stable id used in API payloads and storage, e.g. "openai". */
  readonly id: ProviderId;
  /** Human label for the dashboard, e.g. "OpenAI". */
  readonly name: string;
  /** Model this provider will use unless overridden by env. */
  readonly model: string;
  /** True when the provider has the credentials it needs to make a real call. */
  isConfigured(): boolean;
  /**
   * Send one prompt and return the completion.
   * Throws `ProviderError` on failure; the orchestrator converts that to `AIFailure`.
   */
  sendMessage(prompt: string, options?: ProviderOptions): Promise<AIResponse>;
}

/** What the dashboard needs to render provider toggles honestly. */
export interface ProviderInfo {
  id: ProviderId;
  name: string;
  model: string;
  configured: boolean;
  enabled: boolean;
  /** Present when the provider cannot be used, e.g. "Provider not configured". */
  status: string;
  /** True for the development-only mock provider. Surfaced loudly in the UI. */
  mock: boolean;
}

export type WorkflowMode = "single" | "parallel" | "review" | "consensus";

export type RunStatus = "success" | "partial" | "failed";

/** One step of a multi-stage workflow (review / consensus), for transparency. */
export interface WorkflowStep {
  stage: string;
  provider: ProviderId;
  result: ProviderResult;
}

export interface WorkflowRequest {
  task: string;
  mode: WorkflowMode;
  providers: ProviderId[];
  /** Consensus only: which provider synthesizes the final answer. */
  judge?: ProviderId;
  /** Review only: defaults to providers[0] / providers[1]. */
  author?: ProviderId;
  reviewer?: ProviderId;
  maxOutputTokens?: number;
  temperature?: number;
}

export interface WorkflowRun {
  runId: string;
  task: string;
  mode: WorkflowMode;
  providers: ProviderId[];
  /** Every individual provider call made during the run, in order. */
  responses: ProviderResult[];
  /** Named stages, so the UI can explain *why* each call happened. */
  steps: WorkflowStep[];
  judge?: ProviderId;
  finalResponse: string | null;
  status: RunStatus;
  error?: string;
  durationMs: number;
  createdAt: string;
  completedAt: string;
}
