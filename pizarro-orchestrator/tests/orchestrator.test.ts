import { afterEach, describe, expect, it, vi } from "vitest";
import { orchestrate } from "@/orchestrator";
import { getRunStore } from "@/services/store";
import type { WorkflowRun } from "@/types/ai";
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

/** Every provider answers successfully. */
function allHealthy(labels = { openai: "OPENAI ANSWER", claude: "CLAUDE ANSWER", pplx: "PERPLEXITY ANSWER" }) {
  return mockFetch({
    [OPENAI_URL]: () => jsonResponse(chatBody(labels.openai, "gpt-test")),
    [ANTHROPIC_URL]: () => jsonResponse(messagesBody(labels.claude, "claude-test")),
    [PERPLEXITY_URL]: () => jsonResponse(chatBody(labels.pplx, "sonar-test")),
  });
}

const textOf = (run: WorkflowRun, i: number) => {
  const r = run.responses[i];
  return r.ok ? r.text : null;
};

describe("SINGLE mode", () => {
  it("calls exactly one provider and returns its answer as the final response", async () => {
    setEnv(ALL_KEYS);
    const { calls } = allHealthy();

    const run = await orchestrate({ task: "What is 2+2?", mode: "single", providers: ["openai"] });

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toContain(OPENAI_URL);
    expect(run.status).toBe("success");
    expect(run.responses).toHaveLength(1);
    expect(run.finalResponse).toBe("OPENAI ANSWER");
  });

  it("reports failed status when the only provider is unconfigured", async () => {
    setEnv({});
    const { calls } = mockFetch({});

    const run = await orchestrate({ task: "hi", mode: "single", providers: ["openai"] });

    expect(calls).toHaveLength(0);
    expect(run.status).toBe("failed");
    expect(run.finalResponse).toBeNull();
    expect(run.responses[0].ok).toBe(false);
    expect(run.responses[0].ok === false && run.responses[0].error.code).toBe("not_configured");
  });
});

describe("PARALLEL mode", () => {
  it("fans out to every provider and keeps each answer separate", async () => {
    setEnv(ALL_KEYS);
    const { calls } = allHealthy();

    const run = await orchestrate({
      task: "Compare approaches",
      mode: "parallel",
      providers: ["openai", "anthropic", "perplexity"],
    });

    expect(calls).toHaveLength(3);
    expect(run.status).toBe("success");
    expect(run.responses.map((r) => r.provider)).toEqual(["openai", "anthropic", "perplexity"]);
    expect(textOf(run, 0)).toBe("OPENAI ANSWER");
    expect(textOf(run, 1)).toBe("CLAUDE ANSWER");
    expect(textOf(run, 2)).toBe("PERPLEXITY ANSWER");
    // Parallel deliberately has no single winner.
    expect(run.finalResponse).toBeNull();
  });

  it("isolates failures: Perplexity dying does not stop OpenAI or Claude", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [OPENAI_URL]: () => jsonResponse(chatBody("OPENAI ANSWER")),
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("CLAUDE ANSWER")),
      [PERPLEXITY_URL]: () => jsonResponse({ error: { message: "service unavailable" } }, 503),
    });

    const run = await orchestrate({
      task: "Research this",
      mode: "parallel",
      providers: ["openai", "anthropic", "perplexity"],
    });

    expect(run.status).toBe("partial");
    expect(textOf(run, 0)).toBe("OPENAI ANSWER");
    expect(textOf(run, 1)).toBe("CLAUDE ANSWER");
    const failed = run.responses[2];
    expect(failed.ok).toBe(false);
    expect(failed.ok === false && failed.error.code).toBe("server_error");
  });

  it("survives every provider failing without throwing", async () => {
    setEnv(ALL_KEYS);
    vi.stubGlobal("fetch", async () => {
      throw new TypeError("network is down");
    });

    const run = await orchestrate({
      task: "anything",
      mode: "parallel",
      providers: ["openai", "anthropic", "perplexity"],
    });

    expect(run.status).toBe("failed");
    expect(run.responses.every((r) => !r.ok)).toBe(true);
  });

  it("a provider with no key fails alone while the configured one answers", async () => {
    setEnv({ OPENAI_API_KEY: "test-openai-key" });
    allHealthy();

    const run = await orchestrate({
      task: "hi",
      mode: "parallel",
      providers: ["openai", "anthropic"],
    });

    expect(run.status).toBe("partial");
    expect(textOf(run, 0)).toBe("OPENAI ANSWER");
    expect(run.responses[1].ok === false && run.responses[1].error.code).toBe("not_configured");
  });
});

describe("REVIEW mode", () => {
  it("runs draft → critique → revision and returns the revision", async () => {
    setEnv(ALL_KEYS);
    let claudeCalls = 0;
    const { calls } = mockFetch({
      [ANTHROPIC_URL]: () => {
        claudeCalls += 1;
        return jsonResponse(messagesBody(claudeCalls === 1 ? "DRAFT" : "REVISED ANSWER"));
      },
      [OPENAI_URL]: () => jsonResponse(chatBody("CRITIQUE: cite your sources")),
    });

    const run = await orchestrate({
      task: "Explain quorum",
      mode: "review",
      providers: ["anthropic", "openai"],
    });

    expect(calls).toHaveLength(3);
    expect(run.steps.map((s) => s.stage)).toEqual(["draft", "critique", "revision"]);
    expect(run.steps.map((s) => s.provider)).toEqual(["anthropic", "openai", "anthropic"]);
    expect(run.finalResponse).toBe("REVISED ANSWER");
    expect(run.status).toBe("success");

    // The reviewer must actually receive the draft, and the author the critique.
    expect(JSON.stringify(calls[1].body)).toContain("DRAFT");
    expect(JSON.stringify(calls[2].body)).toContain("CRITIQUE: cite your sources");
  });

  it("stops after a failed draft — there is nothing to review", async () => {
    setEnv(ALL_KEYS);
    const { calls } = mockFetch({
      [ANTHROPIC_URL]: () => jsonResponse({ error: { message: "overloaded" } }, 529),
      [OPENAI_URL]: () => jsonResponse(chatBody("never reached")),
    });

    const run = await orchestrate({
      task: "x",
      mode: "review",
      providers: ["anthropic", "openai"],
    });

    expect(calls).toHaveLength(1);
    expect(run.steps.map((s) => s.stage)).toEqual(["draft"]);
    expect(run.status).toBe("failed");
    expect(run.finalResponse).toBeNull();
  });

  it("falls back to the draft when the reviewer fails", async () => {
    setEnv(ALL_KEYS);
    mockFetch({
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("DRAFT ONLY")),
      [OPENAI_URL]: () => jsonResponse({ error: { message: "reviewer down" } }, 500),
    });

    const run = await orchestrate({
      task: "x",
      mode: "review",
      providers: ["anthropic", "openai"],
    });

    expect(run.steps.map((s) => s.stage)).toEqual(["draft", "critique"]);
    expect(run.status).toBe("partial");
    expect(run.finalResponse).toBe("DRAFT ONLY");
  });
});

describe("CONSENSUS mode", () => {
  it("collects independent answers then hands all of them to the judge", async () => {
    setEnv(ALL_KEYS);
    let openaiCalls = 0;
    const { calls } = mockFetch({
      [OPENAI_URL]: () => {
        openaiCalls += 1;
        return jsonResponse(chatBody(openaiCalls === 1 ? "OPENAI ANSWER" : "JUDGE VERDICT"));
      },
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("CLAUDE ANSWER")),
      [PERPLEXITY_URL]: () => jsonResponse(chatBody("PERPLEXITY ANSWER")),
    });

    const run = await orchestrate({
      task: "Is X true?",
      mode: "consensus",
      providers: ["openai", "anthropic", "perplexity"],
      judge: "openai",
    });

    expect(calls).toHaveLength(4); // 3 answers + 1 judge
    expect(run.steps.map((s) => s.stage)).toEqual(["answer", "answer", "answer", "synthesis"]);
    expect(run.judge).toBe("openai");
    expect(run.finalResponse).toBe("JUDGE VERDICT");
    expect(run.status).toBe("success");

    // The judge prompt must contain the task and every successful answer.
    const judgePrompt = JSON.stringify(calls[3].body);
    expect(judgePrompt).toContain("Is X true?");
    expect(judgePrompt).toContain("OPENAI ANSWER");
    expect(judgePrompt).toContain("CLAUDE ANSWER");
    expect(judgePrompt).toContain("PERPLEXITY ANSWER");
    expect(judgePrompt).toContain("Disagreements");
  });

  it("judges on the survivors when one provider fails, and names the failure", async () => {
    setEnv(ALL_KEYS);
    let openaiCalls = 0;
    const { calls } = mockFetch({
      [OPENAI_URL]: () => {
        openaiCalls += 1;
        return jsonResponse(chatBody(openaiCalls === 1 ? "OPENAI ANSWER" : "JUDGE VERDICT"));
      },
      [ANTHROPIC_URL]: () => jsonResponse(messagesBody("CLAUDE ANSWER")),
      [PERPLEXITY_URL]: () => jsonResponse({ error: { message: "gone" } }, 503),
    });

    const run = await orchestrate({
      task: "Q",
      mode: "consensus",
      providers: ["openai", "anthropic", "perplexity"],
      judge: "openai",
    });

    expect(run.finalResponse).toBe("JUDGE VERDICT");
    expect(run.status).toBe("partial");

    const judgePrompt = JSON.stringify(calls[calls.length - 1].body);
    expect(judgePrompt).toContain("OPENAI ANSWER");
    expect(judgePrompt).toContain("CLAUDE ANSWER");
    // The judge is told Perplexity was unavailable rather than being given a fake answer.
    expect(judgePrompt).toContain("PROVIDERS THAT FAILED");
  });

  it("never calls the judge when no provider produced an answer", async () => {
    setEnv(ALL_KEYS);
    const { calls } = mockFetch({
      [OPENAI_URL]: () => jsonResponse({ error: { message: "down" } }, 500),
      [ANTHROPIC_URL]: () => jsonResponse({ error: { message: "down" } }, 500),
    });

    const run = await orchestrate({
      task: "Q",
      mode: "consensus",
      providers: ["openai", "anthropic"],
      judge: "openai",
    });

    expect(calls).toHaveLength(2); // no judge call
    expect(run.steps.every((s) => s.stage === "answer")).toBe(true);
    expect(run.status).toBe("failed");
    expect(run.finalResponse).toBeNull();
  });
});

describe("stopping conditions", () => {
  it("refuses provider calls beyond MAX_PROVIDER_CALLS_PER_RUN", async () => {
    setEnv({ ...ALL_KEYS, MAX_PROVIDER_CALLS_PER_RUN: "2" });
    const { calls } = allHealthy();

    const run = await orchestrate({
      task: "Q",
      mode: "parallel",
      providers: ["openai", "anthropic", "perplexity"],
    });

    expect(calls).toHaveLength(2); // third call was refused by the budget
    const refused = run.responses[2];
    expect(refused.ok).toBe(false);
    expect(refused.ok === false && refused.error.message).toContain("budget");
  });
});

describe("execution history", () => {
  it("persists the run so it can be listed and fetched by id", async () => {
    setEnv(ALL_KEYS);
    allHealthy();

    const run = await orchestrate({ task: "log me", mode: "single", providers: ["openai"] });
    const store = getRunStore();

    const fetched = await store.getRun(run.runId);
    expect(fetched?.runId).toBe(run.runId);
    expect(fetched?.task).toBe("log me");
    expect(fetched?.mode).toBe("single");
    expect(fetched?.finalResponse).toBe("OPENAI ANSWER");

    const listed = await store.listRuns(10);
    expect(listed.map((r) => r.runId)).toContain(run.runId);
  });

  it("records latency, timestamps and status on every response", async () => {
    setEnv(ALL_KEYS);
    allHealthy();

    const run = await orchestrate({ task: "x", mode: "single", providers: ["anthropic"] });
    const [response] = run.responses;

    expect(response.provider).toBe("anthropic");
    expect(response.model).toBe("claude-test");
    expect(response.latencyMs).toBeGreaterThanOrEqual(0);
    expect(() => new Date(response.timestamp).toISOString()).not.toThrow();
    expect(run.durationMs).toBeGreaterThanOrEqual(0);
    expect(run.createdAt).toBeTruthy();
    expect(run.completedAt).toBeTruthy();
  });
});
