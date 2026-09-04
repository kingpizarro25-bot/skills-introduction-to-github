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
