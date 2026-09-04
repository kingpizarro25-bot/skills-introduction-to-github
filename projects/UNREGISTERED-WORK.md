# Unregistered Work

Work that exists in this repository but was not visible from the default branch and is
not tracked by any project's `STATE.md`.

**This file is the direct answer to "why is every session seeing something different."**
Four sessions each built on their own branch and never merged. Nothing shared a source
of truth, so no session could see any other session's work — including this one.

Found 2026-09-04, while merging the agent structure to `main`.

## What is verifiably true

Facts only — branch, file count, last commit, merge status. **No stage or status is
assigned**, because none has been verified. Assigning one would repeat the exact mistake
this file documents.

| Branch | Files | Last commit | Merged to main |
|---|---|---|---|
| `claude/pizarro-multi-ai-orchestrator-4q14zx` | 52 | `86f321d` 2026-08-20 — "Add Google Gemini as a fourth provider" | No |
| `claude/biomedical-discovery-platform-o88jjz` | 36 | `4734fc2` 2026-08-23 — "Add biomedical challenge platform spec and vertical slice" | No |
| `claude/mystery-v1-hardened-arch-4rqlzg` | 18 | `bde1977` 2026-08-22 — "Add /MYSTERY v1 schemas and runtime core" | No |
| `claude/income-strategies-s0q1co` | 2 | `eb2015f` 2026-08-24 — "Add revenue plan: five income strategies ranked by time to first dollar" | No |

### What each appears to contain

Read from the file tree only. **Nothing here has been run, tested, or reviewed.**

- **pizarro-multi-ai-orchestrator** — a Next.js/TypeScript app under `pizarro-orchestrator/`,
  with API route handlers and multiple AI provider integrations.
- **biomedical-discovery-platform** — a Python package under `discovery/` with a CLI,
  challenge compiler, and evaluation modules.
- **mystery-v1-hardened-arch** — a Python runtime under `mystery/runtime/` including
  engine, evidence, and gate modules.
- **income-strategies** — a README and a single HTML page.

## The overlap worth noting

`pizarro-multi-ai-orchestrator` is an AI-coordination system. So is Pizarro Studios OS.
They were built three weeks apart, by different sessions, in the same repository,
neither aware of the other.

That is duplicate work, and it is the specific failure the "one owner per unit of work"
rule and Mission Control's inventory step exist to prevent. It is recorded here as the
first real lesson rather than quietly deleted.

## Status

**Blocked pending owner intake.** For each one, the questions are the same five in every
`STATE.md`: what actually exists, where it lives, is anyone using it, what last worked or
broke, and what "finished" would mean.

Until then these stay listed and unassigned. They are **not** dead — none has been
reviewed closely enough to say that.

## What must not happen next

- Do not merge these branches without review. They were written by other sessions against
  a tutorial repository, and their state is unknown.
- Do not delete them. Unreviewed is not the same as worthless.
- Do not assign any of them a stage. That is intake's job.
