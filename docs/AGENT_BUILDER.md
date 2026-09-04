# Agent Builder Standard

The standard for proposing, defining, and activating any agent in Pizarro Studios OS.
Follow it whenever a new agent is suggested — by the owner, by an agent, or by you.

Related: `agents/ACTIVATION.md` (activation triggers and review), `agents/README.md`
(the current roster), `CLAUDE.md` (company context and approval gates).

---

## Step 0 — First, do not build an agent

Before defining anything, check whether an existing core or specialist agent already
covers the responsibility. Read `agents/README.md` and
`agents/specs/tier-2-specialists.md`.

**If an existing agent covers at least 80% of the work, improve or reuse that agent
instead of creating another one.** Extending one agent's responsibilities is almost
always cheaper than maintaining a second agent and the boundary between them.

Only if a genuinely new agent is justified, continue.

---

## The 15-part definition

### 1. Name
A clear functional name. What it does, not a title.

### 2. Purpose
Exactly what this agent is responsible for. One paragraph.

### 3. Activation trigger
The concrete condition that justifies creating or activating this agent.

Do not activate an agent because it might someday be useful. The five valid triggers
are in `agents/ACTIVATION.md`: frequency, volume, risk, handoff, contract revenue.

### 4. Inputs
What information, files, evidence, project state, or owner instructions it requires.

### 5. Process
The repeatable steps it follows when handling work.

### 6. Tools
Which files, commands, APIs, websites, connectors, models, or other agents it may use.
**Only include tools that are actually necessary.** Every tool is a surface for
mistakes and a thing to maintain.

### 7. Output
Exactly what result it produces, and in what format. Name the file path if it writes one.

### 8. Boundaries
Define three things:
- what the agent **owns**
- what it **does not own**
- which agent **receives work outside its responsibility**

Avoid overlapping responsibility. One owner per unit of work.

### 9. Evidence requirements
What evidence is required before this agent may claim something is complete, correct,
verified, deployed, working, or successful.

Status words are limited to: **verified / partially verified / not tested / blocked**.

### 10. Quality check
Before returning work, the agent must:
- check the result against the request
- identify missing information
- verify factual claims when appropriate
- state assumptions
- correct obvious errors
- state what was not verified

### 11. Failure handling
If the task cannot be completed:
- identify exactly what failed
- identify the blocker
- preserve completed work
- state the safest next action
- **never represent blocked or incomplete work as completed**

### 12. Human approval
Explicit approval is required before: spending money, publishing publicly, sending
external messages, submitting applications, deleting important data, modifying
production systems, anything involving credentials or identity, and any irreversible
action.

Prepare the work fully, then stop and ask. `CLAUDE.md` is the authority on this list —
reference it, do not restate it in the agent file, or the two will drift.

### 13. Memory / state
Define:
- what is written to permanent project or company state (`projects/<name>/STATE.md`,
  `business/knowledge-vault/`)
- what is temporary working context
- what must never be stored (secrets, credentials, customer personal data)

**Do not turn guesses into permanent state.** An unknown recorded as unknown is
useful. An assumption recorded as fact is a defect that spreads.

### 14. Tests
Write at least three realistic tests:
- a **normal** request
- an **ambiguous or incomplete** request
- a **failure or boundary** case

For each, define:

```
request → expected routing → expected behavior → required evidence → pass condition
```

Run them and record results before activation. A worked example lives at
`projects/business-systems/EVIDENCE/2026-09-04-mission-control-routing-test.md`.

### 15. Activation review
Answer all five before activating:

1. Why can no existing agent handle this?
2. What real work currently requires it?
3. What measurable benefit does specialization provide?
4. What additional maintenance does it create?
5. What condition would justify deactivating it later?

**If these cannot be answered clearly, do not activate the agent.**

---

## After activation

1. Write the definition to `.claude/agents/<name>.md` with frontmatter (`name`,
   `description` written as a "use when" trigger — that is what makes routing work).
2. Remove the transferred responsibility from the core agent that was covering it.
3. Log the activation and its reasoning in `business/knowledge-vault/DECISIONS.md`.
4. Review after 30 days. If it has not carried real work, deactivate it.

## Template

```markdown
---
name: <kebab-case-name>
description: <what it does. Use when <concrete trigger>.>
---

# <Name> Agent

## Purpose
## Activation trigger
## Inputs
## Process
## Tools
## Output
## Boundaries
**Owns:**
**Does not own:**
**Hands off to:**
## Evidence requirements
## Quality check
## Failure handling
## Human approval
Per the approval gates in `CLAUDE.md`.
## Memory / state
**Permanent:**
**Working context:**
**Never stored:**
## Tests
## Activation review
```
