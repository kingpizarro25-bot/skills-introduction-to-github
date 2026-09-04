import { afterEach, describe, expect, it, vi } from "vitest";
import { GeminiProvider } from "@/providers/gemini";
import { describeProviders } from "@/providers/registry";
import { orchestrate } from "@/orchestrator";
import { validateWorkflowRequest } from "@/services/validation";
import {
  ALL_KEYS,
  ANTHROPIC_URL,
  GEMINI_URL,
  OPENAI_URL,
  chatBody,
  generateContentBody,
  jsonResponse,
  messagesBody,
  mockFetch,
  setEnv,
} from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("Gemini adapter", () => {
  it("translates the request into Gemini's wire format", async () => {
    setEnv({ ...ALL_KEYS, GEMINI_MODEL: "gemini-test" });
    const { calls } = mockFetch({
      [GEMINI_URL]: () => jsonResponse(generateContentBody("gemini answers")),
    });

    const result = await new GeminiProvider().sendMessage("ping", {
      system: "be terse",
      maxOutputTokens: 64,
    });

    expect(result.ok).toBe(true);
    expect(result.text).toBe("gemini answers");
    expect(result.provider).toBe("gemini");
    expect(result.usage?.outputTokens).toBe(20);

    // The model goes in the path, and the key in a header — never the URL.
    expect(calls[0].url).toContain("/models/gemini-test:generateContent");
    expect(calls[0].url).not.toContain("test-gemini-key");
    expect(calls[0].headers["x-goog-api-key"]).toBe("test-gemini-key");

    expect(calls[0].body.contents).toEqual([{ role: "user", parts: [{ text: "ping" }] }]);
    expect(calls[0].body.systemInstruction).toEqual({ parts: [{ text: "be terse" }] });
    expect(calls[0].body.generationConfig).toMatchObject({ maxOutputTokens: 64 });
  });

  it("joins multi-part responses", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [GEMINI_URL]: () =>
        jsonResponse({
          candidates: [{ content: { parts: [{ text: "part one " }, { text: "part two" }] } }],
        }),
    });

    const result = await new GeminiProvider().sendMessage("ping");
    expect(result.text).toBe("part one part two");
  });

  it("explains a safety block instead of reporting an empty answer", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [GEMINI_URL]: () => jsonResponse({ promptFeedback: { blockReason: "SAFETY" } }),
    });

    const err = await new GeminiProvider().sendMessage("ping").catch((e) => e);
    expect(err.message).toContain("SAFETY");
    expect(err.retryable).toBe(false);
  });

  it("points at MAX_OUTPUT_TOKENS when the answer was cut off before any text", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [GEMINI_URL]: () =>
        jsonResponse({ candidates: [{ content: { parts: [] }, finishReason: "MAX_TOKENS" }] }),
    });

    const err = await new GeminiProvider().sendMessage("ping").catch((e) => e);
    expect(err.message).toContain("MAX_OUTPUT_TOKENS");
  });

  it("reports not-configured without calling out when the key is missing", async () => {
    setEnv({ OPENAI_API_KEY: "k" });
    const { calls } = mockFetch({});

    expect(new GeminiProvider().isConfigured()).toBe(false);
    await expect(new GeminiProvider().sendMessage("ping")).rejects.toMatchObject({
      code: "not_configured",
    });
    expect(calls).toHaveLength(0);
  });

  it("inherits retry behaviour from the shared transport", async () => {
    setEnv({ ...ALL_KEYS, MAX_RETRIES: "2" });
    let attempts = 0;
    mockFetch({
      [GEMINI_URL]: () => {
        attempts += 1;
        return attempts < 3
          ? jsonResponse({ error: { message: "backend overloaded" } }, 503)
          : jsonResponse(generateContentBody("recovered"));
      },
    });

    const result = await new GeminiProvider().sendMessage("ping");
    expect(result.text).toBe("recovered");
    expect(attempts).toBe(3);
  });
});

describe("Gemini is a first-class provider with no orchestrator changes", () => {
  it("appears in the dashboard provider list", () => {
    setEnv(ALL_KEYS);
    const gemini = describeProviders().find((p) => p.id === "gemini");
    expect(gemini).toMatchObject({ name: "Gemini", configured: true, enabled: true });
  });

  it("is selectable and honours DISABLED_PROVIDERS", () => {
    setEnv({ ...ALL_KEYS, DISABLED_PROVIDERS: "gemini" });
    const result = validateWorkflowRequest({ task: "x", mode: "single", providers: ["gemini"] });
    expect(JSON.stringify(result)).toContain("Disabled by configuration");
  });

  it("runs in parallel mode alongside the other providers", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [OPENAI_URL]: () => jsonResponse(chatBody("OPENAI ANSWER")),
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("CLAUDE ANSWER")),
      [GEMINI_URL]: () => jsonResponse(generateContentBody("GEMINI ANSWER")),
    });

    const run = await orchestrate({
      task: "Q",
      mode: "parallel",
      providers: ["openai", "anthropic", "gemini"],
    });

    expect(run.status).toBe("success");
    expect(run.responses.map((r) => (r.ok ? r.text : null))).toEqual([
      "OPENAI ANSWER",
      "CLAUDE ANSWER",
      "GEMINI ANSWER",
    ]);
  });

  it("can serve as the consensus judge", async () => {
    setEnv(ALL_KEYS);
    const { calls } = mockFetch({
      [OPENAI_URL]: () => jsonResponse(chatBody("OPENAI ANSWER")),
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("CLAUDE ANSWER")),
      [GEMINI_URL]: () => jsonResponse(generateContentBody("GEMINI VERDICT")),
    });

    const run = await orchestrate({
      task: "Q",
      mode: "consensus",
      providers: ["openai", "anthropic"],
      judge: "gemini",
    });

    expect(run.judge).toBe("gemini");
    expect(run.finalResponse).toBe("GEMINI VERDICT");

    // The judge really did receive both answers.
    const judgePrompt = JSON.stringify(calls[calls.length - 1].body);
    expect(judgePrompt).toContain("OPENAI ANSWER");
    expect(judgePrompt).toContain("CLAUDE ANSWER");
  });

  it("a Gemini outage does not affect the other providers", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [OPENAI_URL]: () => jsonResponse(chatBody("OPENAI ANSWER")),
      [GEMINI_URL]: () => jsonResponse({ error: { message: "down" } }, 503),
    });

    const run = await orchestrate({
      task: "Q",
      mode: "parallel",
      providers: ["openai", "gemini"],
    });

    expect(run.status).toBe("partial");
    expect(run.responses[0].ok).toBe(true);
    expect(run.responses[1].ok).toBe(false);
  });
});
