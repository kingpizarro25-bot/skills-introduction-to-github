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
| `claude/pizarro-multi-ai-orchestrator-4q14zx` | 52 | `86f321d` 2026-08-20 — "Add Google Gemini as a fourth provider" | No — **now registered**, see `projects/pizarro-orchestrator/STATE.md` |
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

## Correction, 2026-09-04 — this file first called the orchestrator "duplicate work"

**That claim was wrong, and it was made without reading the code.** It rested on the
branch name and a file listing. The correction stands here rather than being edited away,
because this file exists to document exactly that kind of mistake.

Once the branch was actually read and run:

`pizarro-multi-ai-orchestrator` is a **runtime execution engine** — a Next.js app that
calls four AI provider APIs and reconciles their answers. Pizarro Studios OS is a
**coordination and knowledge structure** — agent definitions, project state, evidence
rules. One is software that runs; the other is how work is organized. They are
complementary, not competing, and neither replaces the other.

The genuine finding is smaller and more useful: the orchestrator implements a **working
Perplexity provider**, which is a second route to the capability that defect D-2 records
as unavailable. See `projects/pizarro-orchestrator/STATE.md`.

The real lesson is unchanged and now better evidenced: five sessions could not see each
other's work. But "they built the same thing twice" was itself an unverified claim,
asserted with more confidence than the evidence supported — the same failure the evidence
rules exist to prevent, committed while documenting that failure.

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
