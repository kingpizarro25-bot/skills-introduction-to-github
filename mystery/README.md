# /MYSTERY — v1 hardened architecture (work in progress)

An evidence-driven investigation engine: scope-locked cases, multi-factor
hypothesis ranking, gated tests, append-only evidence, and findings that are
allowed to end inconclusive.

**Status: partial implementation, not wired to anything, untested.**
Schemas (`schema/json/`) and the runtime core (`runtime/mystery/`) exist. There
is no CLI, no test suite, no `/MYSTERY` skill, and no case has ever been run
through it.

## What the gate does and does not do

`runtime/mystery/gate.py` checks a proposed test against the locked scope, an
allowlist of action classes, and a risk ceiling. Read this before trusting it:

- **It is advisory bookkeeping, not an enforcement boundary.** It runs inside
  the caller and only sees what the caller declares. A test labelled
  `actions=['read_file']` passes every check no matter what it actually does.
- **It is bypassable by design of the current API.** `record_evidence()` and
  `derive_evidence()` do not call the gate, and accept evidence sourced from
  out-of-scope assets.
- **Append-only is a convention, not a mechanism.** Records are hashed
  individually but not chained, so deleting a line from `evidence.jsonl` is
  undetectable.

Real enforcement has to sit between the agent and the tool it invokes (e.g. a
Claude Code `PreToolUse` hook), not in a library the agent chooses to call.

## Known defects

- `test_id` is derived from evidence count, so tests producing no evidence reuse ids.
- A single gate rejection marks the whole hypothesis `untestable`, not just that route.
- `case_status` is overwritten by the most recent finding's status.
- `store.append_evidence` re-parses the full ledger per append (O(n^2)).

## Layout

    schema/json/     JSON Schema (draft 2020-12) for case, hypothesis,
                     evidence, finding, lesson, plus shared enums
    runtime/mystery/ stdlib-only Python implementation of the same model
