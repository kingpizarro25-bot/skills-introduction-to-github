# Activation Rules for Tier 2 Specialists

A specialist agent exists to absorb work that has become too frequent, too
specialized, or too risky for a core agent to keep carrying. Until then it stays
dormant and a core agent covers it.

## An agent may be activated when any one of these is true

1. **Frequency** — the work has come up in three separate weeks, or is now recurring on a schedule.
2. **Volume** — the covering core agent is spending more than roughly a quarter of its work on it.
3. **Risk** — getting it wrong has a material cost: security, money, a legal commitment, or a client relationship.
4. **Handoff** — someone other than the owner needs to be able to do it consistently.
5. **Contract revenue** — a client is paying for this specific capability by name.

## An agent must NOT be activated because

- It sounds impressive on a diagram.
- It exists in a framework someone posted.
- It might be useful eventually.
- The work has happened exactly once.

## Activation procedure

1. Mission Control records which trigger was met, with the evidence.
2. Write the definition into `.claude/agents/<name>.md` using the standard spec:
   mission, responsibilities, inputs, outputs, KPIs, constraints, escalation,
   failure conditions.
3. Name the core agent it takes work *from*, and remove that responsibility from
   the core agent's file. Two owners is worse than one overloaded owner.
4. Log the activation in `business/knowledge-vault/DECISIONS.md`.
5. Review after 30 days. If it has not carried real work, deactivate it — move the
   file back to a dormant spec rather than keeping a decorative agent.

## Deactivation

Any agent that has not been used in 60 days is deactivated at the next review. The
spec is preserved; only the active definition is removed.

## Standing exception — Red-Team

Red-Team may be invoked ad hoc at any time without formal activation, on any
significant decision, architecture, or business plan. Its whole purpose is to
disagree, and a system that only consults its critic on schedule is not being
criticized. Invoke it directly against a specific proposal.
