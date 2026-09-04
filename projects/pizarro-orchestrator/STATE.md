# Pizarro Multi-AI Orchestrator — State

**Last updated:** 2026-09-04 by testing
**Stage:** prototype — builds and passes its own tests; never run against live providers
**Owner agent:** unassigned
**Lives on:** branch `claude/pizarro-multi-ai-orchestrator-4q14zx`, not merged to `main`

This file is the single authoritative answer to "where is this project." If it
disagrees with a chat, a note, or a memory, this file wins.

## One-line description

A Next.js web app that sends one task to OpenAI, Anthropic Claude, Perplexity, and
Google Gemini, then compares, reviews, or combines their answers from a single dashboard.

## Completed — with evidence

| What | Evidence | Date |
|---|---|---|
| Installs from lockfile, 76/76 tests pass, typecheck clean, production build succeeds | [`EVIDENCE/2026-09-04-build-and-test-verification.md`](EVIDENCE/2026-09-04-build-and-test-verification.md) | 2026-09-04 |

## Current

Not being worked on. Last commit 2026-08-20, by a session that is no longer running.

## Next

1. **Owner decision:** does this stay? It is the most complete piece of software in the
   repository and it took real effort, but nothing is using it.
2. If it stays: run it against live providers with real keys (spending gate) and open the
   dashboard to test the user journey — the two largest untested areas.
3. If it stays: decide whether it merges to `main` or moves to its own repository.

## Blocked

| What | Blocked by | Since | Needed to unblock |
|---|---|---|---|
| Live provider verification | No API keys used; calls cost money | 2026-09-04 | Owner approval + keys |
| Merge decision | Owner has not reviewed it | 2026-09-04 | Owner decision |

## Verification status

- **Verified:** builds, typechecks, 76/76 own tests pass.
- **Not tested:** live provider calls, the dashboard UI, user journeys, mobile,
  accessibility, load.
- **Not reviewed:** correctness of behavior. Passing tests prove the tests pass.

## Why this matters to Pizarro Studios OS

It implements a **working Perplexity provider with citation handling**. Defect D-2 in
`projects/business-systems/EVIDENCE/2026-09-04-mission-control-routing-test.md` records
that the research agent's primary source is unavailable because the Perplexity connector
is unauthorized. This code is a second, independent route to the same capability — via
the Perplexity HTTP API with a key, rather than a connector.

That is not a decision to adopt it; it is a fact worth knowing before anyone builds
Perplexity access a third time.

## Related files

- `PRODUCT.md` — v1 scope and acceptance criteria *(never written — see the correction
  in `UNREGISTERED-WORK.md`)*
- `EVIDENCE/` — test and build verification
