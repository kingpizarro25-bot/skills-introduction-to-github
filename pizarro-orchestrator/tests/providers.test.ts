import { afterEach, describe, expect, it, vi } from "vitest";
import { AnthropicProvider } from "@/providers/anthropic";
import { OpenAIProvider } from "@/providers/openai";
import { PerplexityProvider } from "@/providers/perplexity";
import { ProviderError } from "@/providers/base";
import {
  ALL_KEYS,
  ANTHROPIC_URL,
  OPENAI_URL,
  PERPLEXITY_URL,
  chatBody,
  jsonResponse,
  messagesBody,
  mockFetch,
  setEnv,
} from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("provider adapters", () => {
  it("OpenAI sends the configured model and returns normalized output", async () => {
    setEnv({ ...ALL_KEYS, OPENAI_MODEL: "gpt-test" });
    const { calls } = mockFetch({ [OPENAI_URL]: () => jsonResponse(chatBody("hello", "gpt-test")) });

    const result = await new OpenAIProvider().sendMessage("ping", { maxOutputTokens: 64 });

    expect(result.ok).toBe(true);
    expect(result.text).toBe("hello");
    expect(result.provider).toBe("openai");
    expect(result.model).toBe("gpt-test");
    expect(result.usage?.outputTokens).toBe(20);
    expect(calls[0].url).toContain("/chat/completions");
    expect(calls[0].body.model).toBe("gpt-test");
    expect(calls[0].body.max_completion_tokens).toBe(64);
    expect(calls[0].headers.authorization).toBe("Bearer test-openai-key");
  });

  it("OpenAI retries once with max_tokens when max_completion_tokens is rejected", async () => {
    setEnv(ALL_KEYS);
    let seen = 0;
    const { calls } = mockFetch({
      [OPENAI_URL]: () => {
        seen += 1;
        return seen === 1
          ? jsonResponse({ error: { message: "Unsupported parameter: 'max_completion_tokens'" } }, 400)
          : jsonResponse(chatBody("legacy ok"));
      },
    });

    const result = await new OpenAIProvider().sendMessage("ping");

    expect(result.text).toBe("legacy ok");
    expect(calls[0].body).toHaveProperty("max_completion_tokens");
    expect(calls[1].body).toHaveProperty("max_tokens");
  });

  it("Anthropic uses x-api-key, the version header and required max_tokens", async () => {
    setEnv({ ...ALL_KEYS, ANTHROPIC_MODEL: "claude-test" });
    const { calls } = mockFetch({
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("claude says hi")),
    });

    const result = await new AnthropicProvider().sendMessage("ping", { system: "be terse" });

    expect(result.text).toBe("claude says hi");
    expect(result.provider).toBe("anthropic");
    expect(calls[0].url).toContain("/messages");
    expect(calls[0].headers["x-api-key"]).toBe("test-anthropic-key");
    expect(calls[0].headers["anthropic-version"]).toBe("2023-06-01");
    expect(calls[0].body.max_tokens).toBeGreaterThan(0);
    expect(calls[0].body.system).toBe("be terse");
  });

  it("Anthropic joins multiple text blocks and ignores non-text blocks", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [ANTHROPIC_URL]: () =>
        jsonResponse({
          model: "claude-test",
          content: [
            { type: "text", text: "part one" },
            { type: "thinking", thinking: "ignored" },
            { type: "text", text: "part two" },
          ],
        }),
    });

    const result = await new AnthropicProvider().sendMessage("ping");
    expect(result.text).toBe("part one\npart two");
  });

  it("Perplexity surfaces citations in meta", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [PERPLEXITY_URL]: () =>
        jsonResponse({ ...chatBody("grounded answer"), citations: ["https://example.com/a"] }),
    });

    const result = await new PerplexityProvider().sendMessage("ping");
    expect(result.text).toBe("grounded answer");
    expect(result.meta?.citations).toEqual(["https://example.com/a"]);
  });

  it("an empty completion is an error, not an empty answer", async () => {
    setEnv(ALL_KEYS);
    mockFetch({ [OPENAI_URL]: () => jsonResponse(chatBody("   ")) });

    await expect(new OpenAIProvider().sendMessage("ping")).rejects.toMatchObject({
      code: "server_error",
    });
  });
});

describe("missing API keys", () => {
  it("each provider reports not-configured instead of calling out", async () => {
    setEnv({});
    const { calls } = mockFetch({});

    for (const provider of [new OpenAIProvider(), new AnthropicProvider(), new PerplexityProvider()]) {
      expect(provider.isConfigured()).toBe(false);
      await expect(provider.sendMessage("ping")).rejects.toMatchObject({
        code: "not_configured",
      });
    }
    // Nothing was ever sent over the wire.
    expect(calls).toHaveLength(0);
  });

  it("the not-configured message names the env var to set", async () => {
    setEnv({});
    const err = await new AnthropicProvider().sendMessage("ping").catch((e) => e as ProviderError);
    expect(err).toBeInstanceOf(ProviderError);
    expect((err as ProviderError).message).toContain("ANTHROPIC_API_KEY");
    expect((err as ProviderError).retryable).toBe(false);
  });

  it("an empty-string key counts as unset", async () => {
    setEnv({ OPENAI_API_KEY: "   " });
    expect(new OpenAIProvider().isConfigured()).toBe(false);
  });
});
