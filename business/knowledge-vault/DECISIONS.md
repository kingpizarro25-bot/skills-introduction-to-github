# Decisions

One entry per decision. A decision without reasoning is incomplete — in six months
the reasoning is the only part that still matters.

Format:

```
## <yyyy-mm-dd> — <decision in one line>
**Context** what was true that forced a choice
**Decision** what we chose
**Why** the reasoning
**Alternatives rejected** and why
**Revisit when** the condition that would change this
```

---

## 2026-09-04 — Build 10 core agents, specify the other 30 as dormant

**Context** A 40-agent structure was drafted for Pizarro Studios. Building all 40
before the first dollar means maintaining an org chart instead of a business.

**Decision** Build 10 active agents (Mission Control, Research, AI Solutions, Product
Builder, Coding, Testing, Content, Growth, Sales, Knowledge Vault). Specify the
remaining 30 in `agents/specs/tier-2-specialists.md` with written activation triggers.

**Why** These 10 cover the full loop — find a problem, research it, design a solution,
build it, test it, prove it, publish the proof, get attention, sell it, keep the
lesson. The other 30 are specializations of work these 10 already do. Specialization
without volume is overhead.

**Alternatives rejected**
- All 40 now — maintenance burden, ambiguous ownership, no workload to justify it.
- Fewer than 10 (e.g. just Coding + Research) — leaves selling, proving, and
  remembering unowned, which is where small studios actually lose.

**Revisit when** Any activation trigger in `agents/ACTIVATION.md` is met, or a core
agent is spending more than roughly a quarter of its time on one specialist's work.

---

## 2026-09-04 — Security & Privacy is the first specialist to activate

**Context** Veridoc handles documents. Client systems will handle client data.

**Decision** Activate the Security & Privacy agent the moment any system touches real
client documents, personal data, or payments — ahead of every other Tier 2 agent.

**Why** Security failures are not recoverable the way a missed content deadline is.
The cost is a client relationship and possibly a legal exposure.

**Alternatives rejected** Covering it with the Coding agent's secure defaults
indefinitely — adequate for prototypes, not for live client data.

**Revisit when** Real client data enters any system.

---

## 2026-09-04 — Company context lives in CLAUDE.md, not in chat

**Context** The owner supplied company context, priorities, project list, approval
gates, and working style. Held only in a conversation, that context is lost the moment
the session ends, and each agent would reconstruct a slightly different version of it.

**Decision** Put it in `CLAUDE.md` at the repository root. Claude Code loads that file
automatically, so every agent inherits the same context without it being re-pasted.
Approval gates live there as the single authority; agent files reference it rather than
restating the list.

**Why** One copy cannot drift. A list repeated in eleven agent files will.

**Alternatives rejected**
- A `CONTEXT.md` that agents are instructed to read — relies on them remembering to.
- Copying the approval gates into each agent definition — guarantees drift the first
  time a gate changes.

**Revisit when** Priorities change, a project is added or retired, or an approval gate
moves.

---

## 2026-09-04 — Every project starts at "unknown," not at an assumed stage

**Context** Six projects exist (Veridoc, FluencyCoach, Artist Rollout Planner, Pizarro
Shield, Market Mentor AI, business systems). None has verified state recorded here.

**Decision** Create a `STATE.md` for each, with stage explicitly `unknown — needs owner
input`, an empty evidence table, and five intake questions. Do not infer or estimate
stage from project names or from what sounds likely.

**Why** Priority 1 is finishing and verifying existing projects. A guessed stage would
become the record, and the whole system's value rests on not doing exactly that. An
honest "unknown" is a starting point; a wrong "80% complete" is a lie that compounds.

**Alternatives rejected** Leaving the projects unrecorded until intake — they would
stay invisible, and the point is to make the gap visible.

**Revisit when** Each intake is answered; the file is updated per project as it happens.
