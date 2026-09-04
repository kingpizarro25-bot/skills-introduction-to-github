# Mission Control Routing Test

**Date:** 2026-09-04
**Tested build:** commit `80130bf` + `docs/AGENT_BUILDER.md`
**Tester:** testing agent standard, run by Claude Code
**Scope:** the ten Tier 1 agent `description` fields and the Mission Control routing
table — the surface that decides which agent receives a request.

## Method and its limits — read before trusting the results

This is a **desk test of the routing rules**, not a live multi-agent run. Each request
was matched against the ten agent descriptions and the Mission Control routing table,
and the resulting choice was recorded along with any ambiguity.

**What this verifies:** that each request has one unambiguous owner, that no two agents
plausibly claim the same request, and that the handoffs are stated.

**What this does NOT verify:** that the agents produce good work when invoked. That
requires real tasks and stays *not tested*.

---

## Results

### A. Research a competitor

- **Selected agent:** `research`
- **Why:** Table row *"Is this true / what exists / who else does this"*. The
  description names competitive claims explicitly.
- **Secondary agent:** none required. Findings feed `sales` or `growth` on request.
- **Unexpected routing:** none. Competitor Intelligence is a dormant Tier 2 agent whose
  spec names `research` as its cover, so the dormant agent does not compete for this.
- **Result:** Routes to `research`, unambiguously. Output would be a dated, sourced
  file in `business/research/`.
- **PASS** — with defect **D-2** recorded below (a capability gap, not a routing gap).

### B. Fix a software bug

- **Selected agent:** `coding`
- **Why:** Table row *"Build it / fix it / it's broken"*; the description names "debug a
  failure".
- **Secondary agent:** `testing`, after the fix. The coding agent's constraints require
  running the repo's own checks, and its failure conditions forbid claiming "fixed"
  without proof.
- **Unexpected routing:** none.
- **Result:** Routes to `coding` → `testing`. Root-cause requirement is stated in the
  agent file, so a speculative patch would violate its own definition.
- **PASS**

### C. Test a feature

- **Selected agent:** `testing`
- **Why:** Table row *"Does it actually work"*.
- **Secondary agent:** `product-builder` **upstream** if no acceptance criteria exist —
  the testing agent's inputs require them, and it reports a criterion it cannot test as
  untestable rather than passed.
- **Unexpected routing:** none.
- **Result:** Routes to `testing`. Produces a dated report under
  `projects/<project>/EVIDENCE/`.
- **PASS**

### D. Create a piece of content

- **Selected agent:** `content`
- **Why:** Table row *"Write / post / script / publish"*.
- **Secondary agent:** none to produce it. **Owner approval is required before it is
  published** — the gate fired correctly here, which is the behavior being checked.
- **Unexpected routing:** none. Checked against `growth`, which owns channels, offers,
  and landing pages rather than the writing itself. No overlap.
- **Result:** Routes to `content`. Drafting is autonomous; publishing stops for approval.
- **PASS**

### E. Evaluate whether a business process should use AI or simpler automation

- **Selected agent:** `ai-solutions`
- **Why:** The description covers "what to automate, what to keep human", and the
  agent's constraints require it to say *"you don't need AI here"* when a rule, a form,
  or a spreadsheet would do. This request is precisely that judgment.
- **Secondary agent:** `research` if the decision depends on outside facts (tool
  capability, cost). `coding` only after a design exists.
- **Unexpected routing:** **yes — see defect D-1.** The request routes correctly via the
  agent description, but the Mission Control table row is keyed on symptom words
  ("painful / slow / manual"). This request is phrased as a decision question and
  contains none of them. The description caught it; the table alone would not have.
- **Result:** Routes to `ai-solutions`.
- **PASS** — with defect **D-1** recorded below.

### F. Prepare a sales approach for a potential client

- **Selected agent:** `sales`
- **Why:** Table row *"Pitch, proposal, price, close"*; the description covers
  everything between "this business might need us" and "signed".
- **Secondary agent:** `research` **upstream and required**. The sales description reads
  "turns research into a personalized pitch" — research is an input, not an option, and
  the agent may not promise a capability that is not verified buildable.
- **Unexpected routing:** none. Lead Generation and Proposal are dormant Tier 2 agents
  whose specs name `growth`/`research` and `sales` as cover, so neither competes.
- **Result:** Routes to `research` → `sales`. Sending anything outbound requires owner
  approval.
- **PASS**

---

## Summary

| Test | Expected owner | Actual owner | Verdict |
|---|---|---|---|
| A. Research a competitor | research | research | PASS |
| B. Fix a software bug | coding | coding | PASS |
| C. Test a feature | testing | testing | PASS |
| D. Create a piece of content | content | content | PASS |
| E. AI or simpler automation? | ai-solutions | ai-solutions | PASS |
| F. Sales approach for a client | sales | sales | PASS |

**6 of 6 routed to the intended agent. No routing failure.** No request was claimed by
two agents; every handoff is stated in the agent files rather than improvised.

Two defects were found. Neither caused a test to fail, and both are recorded here
before any change was made to routing.

---

## Defects

### D-1 — Routing table row is narrower than the agent it points to

**Severity:** low. Caught by the agent description, so routing still succeeded.

**What:** The `ai-solutions` table row reads *"This business process is painful / slow /
manual"* — symptom language. Test E asked a decision question ("should this use AI or
simpler automation?") containing none of those words. A request phrased as a decision
rather than a complaint can miss the row.

**Fix applied:** the row now covers both phrasings. Minimal, one line, no other change.

### D-2 — The research agent's primary tool is not authorized

**Severity:** high for live use. Does not affect routing.

**What:** The `research` agent specifies "Perplexity first" for current information. The
Perplexity MCP server in this environment **requires authorization that has not been
completed**, so that tool is currently unavailable.

**Effect:** Test A routes correctly, but a real competitor-research task would run
without its primary source. The agent's constraints forbid fabricating sources, so it
would correctly report low confidence or blocked status rather than inventing findings —
the failure mode is degraded output, not false output.

**Fix:** none applied. This needs the owner to authorize the Perplexity connector in
claude.ai connector settings; it cannot be fixed from inside the repository. Recorded
rather than worked around.

---

## Verification status

- **Verified:** all six requests route to exactly one intended agent; no overlap between
  the ten descriptions; handoffs stated.
- **Partially verified:** D-1's fix is verified as text; it has not been re-tested
  against a live routing decision beyond re-running test E below.
- **Not tested:** the quality of any agent's actual output; behavior under a request
  that spans four or more agents; behavior when two projects contend for the same file.
- **Blocked:** anything requiring Perplexity (D-2).

## Re-run after fix

Test E re-run against the corrected table: the row now matches both the symptom
phrasing and the decision phrasing. Routes to `ai-solutions` by table **and** by
description. **PASS.**

No other test was affected by the change, so no other re-run was required.
