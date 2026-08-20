import { afterEach, describe, expect, it, vi } from "vitest";
import { OpenAIProvider } from "@/providers/openai";
import { ALL_KEYS, OPENAI_URL, chatBody, jsonResponse, mockFetch, setEnv } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("retries and error classification", () => {
  it("retries transient 500s up to MAX_RETRIES, then succeeds", async () => {
    setEnv({ ...ALL_KEYS, MAX_RETRIES: "2" });
    let attempts = 0;
    mockFetch({
      [OPENAI_URL]: () => {
        attempts += 1;
        return attempts < 3
          ? jsonResponse({ error: { message: "upstream boom" } }, 500)
          : jsonResponse(chatBody("recovered"));
      },
    });

    const result = await new OpenAIProvider().sendMessage("ping");
    expect(result.text).toBe("recovered");
    expect(attempts).toBe(3);
  });

  it("gives up after the retry budget and reports the attempt count", async () => {
    setEnv({ ...ALL_KEYS, MAX_RETRIES: "1" });
    let attempts = 0;
    mockFetch({
      [OPENAI_URL]: () => {
        attempts += 1;
        return jsonResponse({ error: { message: "still down" } }, 503);
      },
    });

    const err = await new OpenAIProvider().sendMessage("ping").catch((e) => e);
    expect(attempts).toBe(2); // initial + 1 retry — bounded, never infinite
    expect(err.code).toBe("server_error");
    expect(err.attempts).toBe(2);
  });

  it("does NOT retry a permanent auth failure", async () => {
    setEnv({ ...ALL_KEYS, MAX_RETRIES: "3" });
    let attempts = 0;
    mockFetch({
      [OPENAI_URL]: () => {
        attempts += 1;
        return jsonResponse({ error: { message: "Incorrect API key provided" } }, 401);
      },
    });

    const err = await new OpenAIProvider().sendMessage("ping").catch((e) => e);
    expect(attempts).toBe(1);
    expect(err.code).toBe("auth");
    expect(err.retryable).toBe(false);
  });

  it("classifies 429 as rate_limited and retries it", async () => {
    setEnv({ ...ALL_KEYS, MAX_RETRIES: "1" });
    let attempts = 0;
    mockFetch({
      [OPENAI_URL]: () => {
        attempts += 1;
        return jsonResponse({ error: { message: "slow down" } }, 429);
      },
    });

    const err = await new OpenAIProvider().sendMessage("ping").catch((e) => e);
    expect(err.code).toBe("rate_limited");
    expect(attempts).toBe(2);
  });

  it("times out a hanging provider instead of waiting forever", async () => {
    setEnv({ ...ALL_KEYS, REQUEST_TIMEOUT_MS: "1000", MAX_RETRIES: "0" });
    mockFetch({
      [OPENAI_URL]: () =>
        // Never resolves on its own; only the abort signal ends it.
        new Promise<Response>((_resolve, reject) => {
          setTimeout(() => reject(Object.assign(new Error("aborted"), { name: "TimeoutError" })), 1200);
        }),
    });

    const err = await new OpenAIProvider().sendMessage("ping").catch((e) => e);
    expect(err.code).toBe("timeout");
  }, 10_000);

  it("classifies a socket/DNS failure as a network error", async () => {
    setEnv(ALL_KEYS);
    vi.stubGlobal("fetch", async () => {
      throw new TypeError("fetch failed");
    });

    const err = await new OpenAIProvider().sendMessage("ping").catch((e) => e);
    expect(err.code).toBe("network");
    expect(err.retryable).toBe(true);
  });
});

describe("cost controls", () => {
  it("clamps a per-request token override to MAX_OUTPUT_TOKENS", async () => {
    setEnv({ ...ALL_KEYS, MAX_OUTPUT_TOKENS: "100" });
    const { calls } = mockFetch({ [OPENAI_URL]: () => jsonResponse(chatBody("ok")) });

    await new OpenAIProvider().sendMessage("ping", { maxOutputTokens: 999_999 });
    expect(calls[0].body.max_completion_tokens).toBe(100);
  });

  it("clamps a per-request retry override to MAX_RETRIES", async () => {
    setEnv({ ...ALL_KEYS, MAX_RETRIES: "1" });
    let attempts = 0;
    mockFetch({
      [OPENAI_URL]: () => {
        attempts += 1;
        return jsonResponse({ error: { message: "down" } }, 500);
      },
    });

    await new OpenAIProvider().sendMessage("ping", { maxRetries: 50 }).catch(() => undefined);
    expect(attempts).toBe(2);
  });
});
