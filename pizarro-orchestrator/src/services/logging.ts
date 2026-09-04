import { getConfig } from "@/config/env";

/**
 * Minimal structured logger with secret redaction.
 *
 * Every value logged passes through `redact()`. API keys are never logged even
 * if a provider error or request object accidentally carries one.
 */

type Level = "debug" | "info" | "warn" | "error";
const ORDER: Record<Level | "silent", number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
  silent: 100,
};

/**
 * Matches whole key names that hold credentials — anchored so that harmless
 * fields containing the substring "token" (e.g. `outputTokens`) keep their
 * values. Over-redaction hides the telemetry the logs exist for.
 */
const SECRET_KEY_PATTERN =
  /^(.*[_-])?(api[_-]?key|authorization|access[_-]?token|refresh[_-]?token|auth[_-]?token|bearer|token|secret|password|credentials?)$/i;
/** Common provider key shapes: sk-..., sk-ant-..., pplx-... */
const SECRET_VALUE_PATTERN = /\b(sk-[A-Za-z0-9_-]{8,}|pplx-[A-Za-z0-9_-]{8,})\b/g;

export function redact(value: unknown, depth = 0): unknown {
  if (depth > 6) return "[truncated]";
  if (typeof value === "string") return value.replace(SECRET_VALUE_PATTERN, "[redacted]");
  if (Array.isArray(value)) return value.map((v) => redact(v, depth + 1));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = SECRET_KEY_PATTERN.test(k) ? "[redacted]" : redact(v, depth + 1);
    }
    return out;
  }
  return value;
}

function emit(level: Level, message: string, context?: Record<string, unknown>): void {
  const configured = getConfig().LOG_LEVEL;
  if (ORDER[level] < ORDER[configured]) return;

  const line = {
    ts: new Date().toISOString(),
    level,
    message,
    ...(context ? { context: redact(context) as Record<string, unknown> } : {}),
  };
  const sink = level === "error" ? console.error : level === "warn" ? console.warn : console.log;
  sink(JSON.stringify(line));
}

export const logger = {
  debug: (m: string, c?: Record<string, unknown>) => emit("debug", m, c),
  info: (m: string, c?: Record<string, unknown>) => emit("info", m, c),
  warn: (m: string, c?: Record<string, unknown>) => emit("warn", m, c),
  error: (m: string, c?: Record<string, unknown>) => emit("error", m, c),
};
