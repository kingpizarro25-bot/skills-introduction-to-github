import { afterEach, describe, expect, it, vi } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { SqliteRunStore } from "@/services/store/sqlite";
import { MemoryRunStore } from "@/services/store/memory";
import type { RunStore } from "@/services/store";
import { redact } from "@/services/logging";
import { MOCK_BANNER, MockProvider } from "@/providers/mock";
import { describeProviders } from "@/providers/registry";
import { orchestrate } from "@/orchestrator";
import type { WorkflowRun } from "@/types/ai";
import { PerplexityProvider } from "@/providers/perplexity";
import {
  ALL_KEYS,
  OPENAI_URL,
  PERPLEXITY_URL,
  chatBody,
  jsonResponse,
  mockFetch,
  setEnv,
} from "./helpers";
import { safeCitations } from "@/lib/citations";

afterEach(() => vi.unstubAllGlobals());

function sampleRun(overrides: Partial<WorkflowRun> = {}): WorkflowRun {
  const now = new Date().toISOString();
  return {
    runId: "run-1",
    task: "persist me",
    mode: "consensus",
    providers: ["openai", "anthropic"],
    responses: [
      {
        ok: true,
        provider: "openai",
        providerName: "OpenAI",
        model: "gpt-test",
        text: "answer",
        latencyMs: 120,
        timestamp: now,
        usage: { inputTokens: 5, outputTokens: 7 },
      },
      {
        ok: false,
        provider: "anthropic",
        providerName: "Claude",
        model: "claude-test",
        latencyMs: 40,
        timestamp: now,
        error: { code: "rate_limited", message: "429", retryable: true, attempts: 2 },
      },
    ],
    steps: [],
    judge: "openai",
    finalResponse: "final",
    status: "partial",
    durationMs: 200,
    createdAt: now,
    completedAt: now,
    ...overrides,
  };
}

/** The same contract must hold for every RunStore implementation. */
function storeContract(name: string, make: () => { store: RunStore; cleanup: () => void }) {
  describe(`${name} store`, () => {
    it("round-trips a run including failures and usage", async () => {
      const { store, cleanup } = make();
      try {
        const run = sampleRun();
        await store.saveRun(run);

        const loaded = await store.getRun("run-1");
        expect(loaded).not.toBeNull();
        expect(loaded!.task).toBe("persist me");
        expect(loaded!.mode).toBe("consensus");
        expect(loaded!.providers).toEqual(["openai", "anthropic"]);
        expect(loaded!.judge).toBe("openai");
        expect(loaded!.finalResponse).toBe("final");
        expect(loaded!.status).toBe("partial");
        expect(loaded!.responses).toHaveLength(2);
        expect(loaded!.responses[1].ok).toBe(false);
      } finally {
        cleanup();
      }
    });

    it("returns null for an unknown id and lists newest first", async () => {
      const { store, cleanup } = make();
      try {
        expect(await store.getRun("nope")).toBeNull();

        await store.saveRun(sampleRun({ runId: "old", createdAt: "2024-01-01T00:00:00.000Z" }));
        await store.saveRun(sampleRun({ runId: "new", createdAt: "2025-01-01T00:00:00.000Z" }));

        const listed = await store.listRuns(10);
        expect(listed[0].runId).toBe("new");
        expect(listed).toHaveLength(2);

        expect(await store.listRuns(1)).toHaveLength(1);
      } finally {
        cleanup();
      }
    });
  });
}

storeContract("memory", () => ({ store: new MemoryRunStore(), cleanup: () => undefined }));

storeContract("sqlite", () => {
  const dir = mkdtempSync(join(tmpdir(), "orchestrator-test-"));
  const store = new SqliteRunStore(join(dir, "nested", "test.db"));
  return {
    store,
    cleanup: () => {
      void store.close();
      rmSync(dir, { recursive: true, force: true });
    },
  };
});

describe("secret handling", () => {
  it("redacts secret-looking keys and values from logs", () => {
    const redacted = redact({
      authorization: "Bearer sk-secret-value-123456789",
      "x-api-key": "sk-ant-abcdefgh12345678",
      nested: { OPENAI_API_KEY: "sk-live-abcdefgh12345678", safe: "keep me" },
      message: "call failed with key sk-proj-abcdefgh12345678 attached",
    }) as Record<string, unknown>;

    const serialized = JSON.stringify(redacted);
    expect(serialized).not.toContain("secret-value");
    expect(serialized).not.toContain("abcdefgh12345678");
    expect(redacted.authorization).toBe("[redacted]");
    expect((redacted.nested as Record<string, unknown>).safe).toBe("keep me");
    expect(redacted.message).toContain("[redacted]");
  });

  it("does not over-redact: token *counts* survive so telemetry stays useful", () => {
    const redacted = redact({
      usage: { inputTokens: 12, outputTokens: 44 },
      maxOutputTokens: 1024,
      latencyMs: 210,
      // ...while real credential fields are still removed.
      access_token: "abc123",
      token: "abc123",
    }) as Record<string, unknown>;

    expect((redacted.usage as Record<string, unknown>).outputTokens).toBe(44);
    expect((redacted.usage as Record<string, unknown>).inputTokens).toBe(12);
    expect(redacted.maxOutputTokens).toBe(1024);
    expect(redacted.latencyMs).toBe(210);
    expect(redacted.access_token).toBe("[redacted]");
    expect(redacted.token).toBe("[redacted]");
  });

  it("keeps API keys out of the provider list served to the browser", () => {
    setEnv(ALL_KEYS);
    const serialized = JSON.stringify(describeProviders());
    for (const key of Object.values(ALL_KEYS)) {
      expect(serialized).not.toContain(key);
    }
  });

  it("never puts a key into a stored run", async () => {
    setEnv(ALL_KEYS);
    mockFetch({ [OPENAI_URL]: () => jsonResponse(chatBody("ok")) });

    const run = await orchestrate({ task: "x", mode: "single", providers: ["openai"] });
    const serialized = JSON.stringify(run);
    for (const key of Object.values(ALL_KEYS)) {
      expect(serialized).not.toContain(key);
    }
  });
});

describe("untrusted provider output", () => {
  it("drops non-http(s) citation URLs so a hostile provider cannot inject a javascript: link", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [PERPLEXITY_URL]: () =>
        jsonResponse({
          ...chatBody("grounded"),
          citations: [
            "https://example.com/ok",
            "http://example.com/also-ok",
            // eslint-disable-next-line no-script-url
            "javascript:alert(document.cookie)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "not a url at all",
            42,
          ],
        }),
    });

    const result = await new PerplexityProvider().sendMessage("ping");
    const rendered = safeCitations(result);

    expect(rendered).toEqual(["https://example.com/ok", "http://example.com/also-ok"]);
    expect(rendered.join(" ")).not.toContain("javascript:");
    expect(rendered.join(" ")).not.toContain("data:");
  });
});

describe("mock provider", () => {
  it("is hidden unless explicitly enabled", () => {
    setEnv(ALL_KEYS);
    expect(describeProviders().some((p) => p.id === "mock")).toBe(false);
    expect(new MockProvider().isConfigured()).toBe(false);
  });

  it("is flagged as mock and labels its output when enabled", async () => {
    setEnv({ ENABLE_MOCK_PROVIDER: "true" });

    const info = describeProviders().find((p) => p.id === "mock");
    expect(info?.mock).toBe(true);
    expect(info?.name).toContain("DEV ONLY");

    const result = await new MockProvider().sendMessage("do a thing");
    expect(result.text.startsWith(MOCK_BANNER)).toBe(true);
    expect(result.meta?.mock).toBe(true);
  });

  it("is never substituted for a provider that failed", async () => {
    setEnv({ ENABLE_MOCK_PROVIDER: "true", OPENAI_API_KEY: "k" });
    mockFetch({ [OPENAI_URL]: () => jsonResponse({ error: { message: "down" } }, 500) });

    const run = await orchestrate({ task: "x", mode: "single", providers: ["openai"] });

    expect(run.status).toBe("failed");
    expect(run.responses).toHaveLength(1);
    expect(run.responses[0].provider).toBe("openai");
    expect(JSON.stringify(run)).not.toContain(MOCK_BANNER);
  });
});
