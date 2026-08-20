# Pizarro Multi-AI Orchestrator

Send one task to several AI providers, then compare, review, or combine their
answers — from a single control panel.

It talks to **OpenAI**, **Anthropic Claude**, and **Perplexity** through their
HTTP APIs. It does not automate their websites.

---

## 1. What this application does

You type a task once. The orchestrator decides which models see it, in what
order, and who gets the last word:

```
USER TASK
   ↓
ORCHESTRATOR → TASK ROUTER
   ├── OpenAI
   ├── Claude
   └── Perplexity
   ↓
COLLECT RESPONSES → COMPARE / SYNTHESIZE
   ↓
FINAL RESPONSE → LOG RESULT
```

Every provider call happens on the server. API keys are read from the
environment and never reach the browser.

**Nothing is faked.** If a provider has no API key, the dashboard says
*"Provider not configured"* and the run refuses to include it. There is a mock
provider for offline UI work, but it is off by default, hidden unless enabled,
and every line it emits is stamped `[MOCK RESPONSE — NOT A REAL MODEL]`.

---

## 2. Architecture

```
src/
  types/ai.ts              The AIProvider contract everything else depends on
  config/env.ts            Env parsing, validation, cost controls
  providers/
    base.ts                Shared HTTP: timeouts, retries, error classification
    openai.ts              Chat Completions adapter
    anthropic.ts           Messages API adapter
    perplexity.ts          Chat Completions adapter (+ citations)
    mock.ts                DEV-ONLY fake provider, clearly labelled
    registry.ts            The list of providers. Add new ones here.
  orchestrator/
    execute.ts             Calls a provider; turns errors into values; call budget
    single.ts parallel.ts review.ts consensus.ts    The four modes
    router.ts              Picks the mode, derives the final answer, logs the run
  services/
    prompts.ts             Critique / revision / judge prompt templates
    logging.ts             Structured logs with secret redaction
    rateLimit.ts           Fixed-window limiter
    validation.ts          Request validation (zod + semantic checks)
    store/                 RunStore interface, SQLite + in-memory implementations
  app/
    api/                   run, providers, runs, runs/[id], health
    dashboard/             The control panel
```

Two rules hold the design together:

1. **The orchestrator never imports a specific provider.** It goes through
   `AIProvider` and the registry, so adding Gemini or a local model touches no
   workflow code.
2. **Provider failures are values, not exceptions.** `callProvider` always
   resolves — with an answer or a typed failure. One dead provider cannot take
   down a run.

### Storage is replaceable

Everything goes through the `RunStore` interface
(`src/services/store/types.ts`). V1 ships SQLite (via Node's built-in
`node:sqlite` — no native build step) and an in-memory store. To move to
PostgreSQL or Supabase, write a `PostgresRunStore` implementing the same four
methods and add a branch to `getRunStore()` in `src/services/store/index.ts`.
No call site changes.

---

## 3. How to install it

Requires **Node.js 22.5 or newer** (for `node:sqlite`).

```bash
cd pizarro-orchestrator
npm install
```

---

## 4. How to create your .env

```bash
cp .env.example .env.local
```

`.env.local` is git-ignored. **Never commit real keys.**

---

## 5. Where the API keys go

Open `.env.local` and fill in the keys you have. You need at least one:

```bash
OPENAI_API_KEY=sk-...            # https://platform.openai.com/api-keys
ANTHROPIC_API_KEY=sk-ant-...     # https://console.anthropic.com/settings/keys
PERPLEXITY_API_KEY=pplx-...      # https://www.perplexity.ai/settings/api
```

Pick models with `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `PERPLEXITY_MODEL`. The
defaults are `gpt-4o`, `claude-sonnet-5`, and `sonar`. Set them to whatever your
account actually has access to.

Providers you leave blank simply show as not configured. That is a supported
state, not an error.

### Cost controls

All of these live in `.env.local`:

| Variable | Default | What it does |
|---|---|---|
| `MAX_OUTPUT_TOKENS` | `1024` | Hard cap on generated tokens per call |
| `REQUEST_TIMEOUT_MS` | `60000` | Wall-clock budget for one provider call |
| `MAX_RETRIES` | `2` | Retries for transient failures only (max 5) |
| `MAX_TASK_LENGTH` | `20000` | Longest accepted task, in characters |
| `MAX_PROVIDER_CALLS_PER_RUN` | `8` | Hard ceiling on calls in one workflow |
| `DISABLED_PROVIDERS` | *(empty)* | Comma-separated ids to switch off |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_MS` | `20` / `60000` | API rate limit |

`MAX_PROVIDER_CALLS_PER_RUN` is the stopping condition. Every workflow has a
fixed, finite number of calls — there are no recursive agent loops, and no mode
keeps calling models until it feels satisfied.

---

## 6. How to start the application

```bash
npm run dev       # development, http://localhost:3000
```

or

```bash
npm run build && npm start
```

Then open **http://localhost:3000** — it redirects to `/dashboard`.

Check what the server thinks is configured:

```bash
curl http://localhost:3000/api/health
```

### Running a workflow from the API

```bash
curl -X POST http://localhost:3000/api/run \
  -H 'content-type: application/json' \
  -d '{
    "task": "Explain optimistic locking in two sentences.",
    "mode": "consensus",
    "providers": ["openai", "anthropic", "perplexity"],
    "judge": "anthropic"
  }'
```

| Endpoint | Purpose |
|---|---|
| `POST /api/run` | Execute a workflow |
| `GET /api/providers` | Provider list with configuration status |
| `GET /api/runs?limit=25` | Execution history, newest first |
| `GET /api/runs/:runId` | One run with every provider response |
| `GET /api/health` | Store driver, configured providers, config warnings |

Provider failures come back inside a `200` response as part of the run. Only bad
input (`400`), rate limiting (`429`), or a broken server (`500`) is non-2xx.

---

## 7. How to run tests

```bash
npm test           # full suite
npm run typecheck  # tsc --noEmit
```

Tests stub `fetch`, so they need no API keys, cost nothing, and never touch a
real provider.

---

## 8. How to add another AI provider

Three steps. None of them touch the orchestrator.

**Step 1 — write the adapter** (`src/providers/gemini.ts`):

```ts
export class GeminiProvider implements AIProvider {
  readonly id = "gemini";
  readonly name = "Gemini";
  get model() { return getConfig().GEMINI_MODEL; }

  isConfigured() { return Boolean(getConfig().GEMINI_API_KEY); }

  async sendMessage(prompt: string, options: ProviderOptions = {}): Promise<AIResponse> {
    const config = getConfig();
    if (!config.GEMINI_API_KEY) throw notConfigured(this.name, "GEMINI_API_KEY");

    const limits = resolveLimits(options);          // applies your cost controls
    const data = await postJson<GeminiShape>(       // gives you timeout + retries
      { url: ..., headers: ..., body: ... },
      limits,
      options.signal,
    );
    return { ok: true, provider: this.id, /* ...normalize the response... */ };
  }
}
```

**Step 2 — add its config** to `src/config/env.ts` and `.env.example`:

```ts
GEMINI_API_KEY: optionalSecret,
GEMINI_MODEL: optionalString("gemini-2.5-pro"),
```

**Step 3 — register it** in `src/providers/registry.ts`:

```ts
const ALL_PROVIDERS: AIProvider[] = [
  new OpenAIProvider(),
  new AnthropicProvider(),
  new PerplexityProvider(),
  new GeminiProvider(),   // ← the only orchestrator-facing change
  new MockProvider(),
];
```

It now appears in the dashboard, can be selected in any mode, and can serve as a
judge. Nothing in `src/orchestrator/` changed.

---

## 9. How the four orchestration modes work

### SINGLE — 1 call
One provider answers. Its answer is the final answer.

### PARALLEL — N calls
Every selected provider gets the same task simultaneously
(`Promise.allSettled`). Each answer is shown on its own.

There is deliberately **no** final synthesis in this mode — picking a winner
without a judge would be arbitrary. Use Consensus for that.

If Perplexity fails, OpenAI and Claude still return. The run is marked
`partial`, and the failure shows its error code and attempt count.

### REVIEW — up to 3 calls
```
provider A  → drafts an answer
provider B  → critiques the draft
provider A  → revises, given the critique
```
The revision is the final answer. Select exactly two providers; the first
drafts, the second reviews.

It stops after one revision — there is no critique/revise loop. If the draft
fails there is nothing to review, so the run stops. If the *critique* fails, the
draft still stands and is returned.

### CONSENSUS — N + 1 calls
Every selected provider answers independently. Then the judge model receives the
original task and all the answers, and produces one final answer plus a
`Disagreements` section.

The judge only ever sees answers that actually succeeded, and is told which
providers were unavailable — so it can't attribute a claim to a model that never
spoke. If *no* provider answered, the judge is not called at all.

### Status values

| Status | Meaning |
|---|---|
| `success` | Every call succeeded (and a final answer exists, except in parallel) |
| `partial` | Some calls failed, but usable output was produced |
| `failed` | Nothing usable came back |

---

## 10. Security

- All provider calls are server-side; keys never enter client code or HTML.
- Secrets are redacted from logs by key name and by value pattern. Token
  *counts* are preserved, so telemetry stays useful.
- Every request is validated with zod, with unknown fields rejected outright.
- Fixed-window rate limiting on the API.
- Errors returned to the client are sanitized — no stack traces, no internal URLs.
- `.env*` files are git-ignored.

For a multi-instance deployment, replace the in-memory limiter in
`src/services/rateLimit.ts` with Redis, and add authentication — V1 assumes a
trusted local operator.

---

## 11. Fitting into AI-BOS later

This is deliberately one layer of the eventual stack:

```
AI-BOS → MISSION → COMMAND → WORKFLOW → [ AI ORCHESTRATOR ] → SPECIALIST MODELS
                                              ↓
                                    EVIDENCE → STATE → OUTCOME → LEARN
```

The seams that make that plug-in possible are already here: `orchestrate()` is a
pure function from `WorkflowRequest` to `WorkflowRun` with no UI coupling, every
run is persisted with its full provider-call trail (the **evidence**), and
storage sits behind an interface ready for a shared database.
