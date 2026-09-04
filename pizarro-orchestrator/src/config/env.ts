import { z } from "zod";

/**
 * Environment configuration + cost controls.
 *
 * Rules enforced here:
 *  - Secrets are read on the server only; nothing here is exported to the client.
 *  - Missing API keys are NOT a startup failure. A provider without a key is
 *    reported as "Provider not configured" instead of being faked.
 *  - Malformed limits ARE a startup failure, because silently falling back to a
 *    default budget is how you get a surprise invoice.
 */

/** Treat `FOO=` in a .env file as "unset" rather than as an empty secret. */
const optionalSecret = z.preprocess(
  (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
  z.string().trim().min(1).optional(),
);

const optionalString = (fallback: string) =>
  z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.string().trim().min(1).default(fallback),
  );

const intInRange = (fallback: number, min: number, max: number) =>
  z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.coerce.number().int().min(min).max(max).default(fallback),
  );

const boolFlag = (fallback: boolean) =>
  z.preprocess((v) => {
    if (typeof v !== "string" || v.trim() === "") return undefined;
    return ["1", "true", "yes", "on"].includes(v.trim().toLowerCase());
  }, z.boolean().default(fallback));

const EnvSchema = z.object({
  // --- Provider credentials & models -------------------------------------
  OPENAI_API_KEY: optionalSecret,
  OPENAI_MODEL: optionalString("gpt-4o"),
  OPENAI_BASE_URL: optionalString("https://api.openai.com/v1"),

  ANTHROPIC_API_KEY: optionalSecret,
  ANTHROPIC_MODEL: optionalString("claude-sonnet-5"),
  ANTHROPIC_BASE_URL: optionalString("https://api.anthropic.com/v1"),

  PERPLEXITY_API_KEY: optionalSecret,
  PERPLEXITY_MODEL: optionalString("sonar"),
  PERPLEXITY_BASE_URL: optionalString("https://api.perplexity.ai"),

  GEMINI_API_KEY: optionalSecret,
  GEMINI_MODEL: optionalString("gemini-2.5-flash"),
  GEMINI_BASE_URL: optionalString("https://generativelanguage.googleapis.com/v1beta"),

  // --- Cost controls ------------------------------------------------------
  MAX_OUTPUT_TOKENS: intInRange(1024, 1, 32000),
  REQUEST_TIMEOUT_MS: intInRange(60_000, 1_000, 300_000),
  MAX_RETRIES: intInRange(2, 0, 5),
  MAX_TASK_LENGTH: intInRange(20_000, 1, 500_000),
  /** Upper bound on provider calls in one workflow. The stopping condition. */
  MAX_PROVIDER_CALLS_PER_RUN: intInRange(8, 1, 32),
  /** Comma-separated provider ids to hard-disable regardless of keys. */
  DISABLED_PROVIDERS: optionalString(""),

  // --- Safety -------------------------------------------------------------
  RATE_LIMIT_MAX: intInRange(20, 1, 10_000),
  RATE_LIMIT_WINDOW_MS: intInRange(60_000, 1_000, 3_600_000),
  /**
   * Only enable when a proxy you control overwrites X-Forwarded-For. Otherwise
   * callers could forge the header and hand themselves a fresh rate-limit bucket.
   */
  TRUST_PROXY_HEADERS: boolFlag(false),

  // --- Storage ------------------------------------------------------------
  STORE_DRIVER: z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.enum(["sqlite", "memory"]).default("sqlite"),
  ),
  DB_PATH: optionalString("./data/orchestrator.db"),

  // --- Development only ---------------------------------------------------
  /** Enables a clearly-labelled fake provider. Never on by default. */
  ENABLE_MOCK_PROVIDER: boolFlag(false),
  LOG_LEVEL: z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.enum(["debug", "info", "warn", "error", "silent"]).default("info"),
  ),
});

export type RawEnv = z.infer<typeof EnvSchema>;

export interface AppConfig extends Omit<RawEnv, "DISABLED_PROVIDERS"> {
  disabledProviders: string[];
}

export class EnvValidationError extends Error {
  constructor(public readonly issues: string[]) {
    super(`Invalid environment configuration:\n  - ${issues.join("\n  - ")}`);
    this.name = "EnvValidationError";
  }
}

let cached: AppConfig | null = null;

/** Parse + cache config. Throws `EnvValidationError` on malformed values. */
export function getConfig(source: NodeJS.ProcessEnv = process.env): AppConfig {
  if (cached && source === process.env) return cached;

  const parsed = EnvSchema.safeParse(source);
  if (!parsed.success) {
    const issues = parsed.error.issues.map(
      (i) => `${i.path.join(".") || "(root)"}: ${i.message}`,
    );
    throw new EnvValidationError(issues);
  }

  const { DISABLED_PROVIDERS, ...rest } = parsed.data;
  const config: AppConfig = {
    ...rest,
    disabledProviders: DISABLED_PROVIDERS.split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
  };

  if (source === process.env) cached = config;
  return config;
}

/** Test helper: drop the cached config so a new env can be parsed. */
export function resetConfigCache(): void {
  cached = null;
}

/**
 * Startup validation. Returns human-readable warnings (e.g. "no providers
 * configured") rather than throwing, so the app still boots and can *tell* you
 * what is missing.
 */
export function validateEnvOnStartup(source: NodeJS.ProcessEnv = process.env): string[] {
  const config = getConfig(source);
  const warnings: string[] = [];

  const keys: Array<[string, string | undefined]> = [
    ["OPENAI_API_KEY", config.OPENAI_API_KEY],
    ["ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY],
    ["PERPLEXITY_API_KEY", config.PERPLEXITY_API_KEY],
    ["GEMINI_API_KEY", config.GEMINI_API_KEY],
  ];
  const missing = keys.filter(([, v]) => !v).map(([k]) => k);

  if (missing.length === keys.length && !config.ENABLE_MOCK_PROVIDER) {
    warnings.push(
      "No provider API keys are set. Every provider will report 'Provider not configured'. " +
        "Copy .env.example to .env.local and add at least one key.",
    );
  } else if (missing.length > 0) {
    warnings.push(`Not configured (will be shown as unavailable): ${missing.join(", ")}`);
  }

  if (config.ENABLE_MOCK_PROVIDER) {
    warnings.push(
      "ENABLE_MOCK_PROVIDER=true — the DEV-ONLY mock provider is active. " +
        "Its output is fake and is labelled as such. Never enable this in production.",
    );
  }

  return warnings;
}
