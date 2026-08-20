import { vi } from "vitest";
import { resetConfigCache } from "@/config/env";
import { MemoryRunStore, setRunStore } from "@/services/store";
import { resetRateLimits } from "@/services/rateLimit";

/** Env vars the tests manipulate; cleared between tests for isolation. */
const MANAGED = [
  "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL",
  "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_BASE_URL",
  "PERPLEXITY_API_KEY", "PERPLEXITY_MODEL", "PERPLEXITY_BASE_URL",
  "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_BASE_URL",
  "MAX_OUTPUT_TOKENS", "REQUEST_TIMEOUT_MS", "MAX_RETRIES", "MAX_TASK_LENGTH",
  "MAX_PROVIDER_CALLS_PER_RUN", "DISABLED_PROVIDERS",
  "RATE_LIMIT_MAX", "RATE_LIMIT_WINDOW_MS", "TRUST_PROXY_HEADERS",
  "STORE_DRIVER", "DB_PATH", "ENABLE_MOCK_PROVIDER", "LOG_LEVEL",
];

/** Reset config, store and rate limits, then apply the given env. */
export function setEnv(env: Record<string, string> = {}): void {
  for (const key of MANAGED) delete process.env[key];
  process.env.LOG_LEVEL = "silent";
  process.env.STORE_DRIVER = "memory";
  // Keep retries off unless a test opts in, so failure tests stay fast.
  process.env.MAX_RETRIES = "0";
  Object.assign(process.env, env);
  resetConfigCache();
  resetRateLimits();
  setRunStore(new MemoryRunStore());
}

/** All three real providers configured with dummy keys. */
export const ALL_KEYS = {
  OPENAI_API_KEY: "test-openai-key",
  ANTHROPIC_API_KEY: "test-anthropic-key",
  PERPLEXITY_API_KEY: "test-perplexity-key",
  GEMINI_API_KEY: "test-gemini-key",
};

export interface FetchCall {
  url: string;
  headers: Record<string, string>;
  body: Record<string, unknown>;
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** OpenAI / Perplexity shaped completion. */
export function chatBody(text: string, model = "test-model") {
  return {
    model,
    choices: [{ message: { content: text }, finish_reason: "stop" }],
    usage: { prompt_tokens: 10, completion_tokens: 20 },
  };
}

/** Anthropic shaped completion. */
export function messagesBody(text: string, model = "claude-test") {
  return {
    model,
    content: [{ type: "text", text }],
    stop_reason: "end_turn",
    usage: { input_tokens: 10, output_tokens: 20 },
  };
}

/**
 * Install a fake `fetch` that dispatches on URL, recording every call.
 * `routes` maps a URL substring to a handler.
 */
export function mockFetch(
  routes: Record<string, (call: FetchCall) => Response | Promise<Response>>,
): { calls: FetchCall[] } {
  const calls: FetchCall[] = [];

  vi.stubGlobal("fetch", async (url: string | URL, init?: RequestInit) => {
    const href = String(url);
    const call: FetchCall = {
      url: href,
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: init?.body ? JSON.parse(String(init.body)) : {},
    };
    calls.push(call);

    for (const [fragment, handler] of Object.entries(routes)) {
      if (href.includes(fragment)) return handler(call);
    }
    throw new TypeError(`No mock route for ${href}`);
  });

  return { calls };
}

export const OPENAI_URL = "api.openai.com";
export const ANTHROPIC_URL = "api.anthropic.com";
export const PERPLEXITY_URL = "api.perplexity.ai";
export const GEMINI_URL = "generativelanguage.googleapis.com";

/** Gemini shaped completion. */
export function generateContentBody(text: string, model = "gemini-test") {
  return {
    modelVersion: model,
    candidates: [{ content: { parts: [{ text }] }, finishReason: "STOP" }],
    usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 20 },
  };
}
