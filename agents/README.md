# Pizarro Studios — Agent Structure

Ten active agents. Thirty specified but dormant. Specialists get activated when the
workload justifies them, not because the org chart looks impressive.

## Tier 1 — Active core (built)

Definitions live in `.claude/agents/` and load automatically as Claude Code subagents.

| Agent | Owns | File |
|---|---|---|
| Mission Control | Routing, sequencing, project state, duplicate prevention | `.claude/agents/mission-control.md` |
| Research | Evidence, verification, market and technical research | `.claude/agents/research.md` |
| AI Solutions | Business problem → AI/automation solution design | `.claude/agents/ai-solutions.md` |
| Product Builder | Idea → scoped v1 plan and acceptance criteria | `.claude/agents/product-builder.md` |
| Coding | Building and fixing software | `.claude/agents/coding.md` |
| Testing | Breaking it, and proving what works | `.claude/agents/testing.md` |
| Content | Content Studio: ideas, writing, repurposing | `.claude/agents/content.md` |
| Growth | Attention, funnels, offers, experiments | `.claude/agents/growth.md` |
| Sales | Pitch, proposals, objections, pipeline | `.claude/agents/sales.md` |
| Knowledge Vault | Decisions, lessons, reusable assets, memory | `.claude/agents/knowledge-vault.md` |

### The loop these ten form

```
Mission Control
  ├─ Research ────────── finds and verifies the problem
  ├─ AI Solutions ────── designs the fix
  ├─ Product Builder ─── scopes version one
  ├─ Coding ──────────── builds it
  ├─ Testing ─────────── proves it works
  ├─ Content ─────────── publishes the proof
  ├─ Growth ──────────── gets it in front of people
  ├─ Sales ───────────── sells the deployment
  └─ Knowledge Vault ─── keeps what was learned
```

Pizarro Studios finds problems → researches them → designs AI solutions → builds
them → tests them → proves they work → publishes the proof → finds customers →
sells deployments → learns from every project.

## Tier 2 — Specified, dormant (30)

Full specifications: `agents/specs/tier-2-specialists.md`.
Activation rules: `agents/ACTIVATION.md`.

Lead Generation · Client Discovery · Proposal · Web Modernization · Automation
Architect · Integration · Security & Privacy · Quality Control · Evidence ·
Project Manager · Finance · Pricing · Operations · Customer Success · Analytics ·
Competitor Intelligence · Opportunity Scout · Partnership · Case Study · Portfolio ·
Social Listening · SEO · Video Content · Brand · Customer Research · Offer Designer ·
SOP · Learning · Decision · Red-Team

Each one names the core agent covering its work in the meantime, so nothing is
dropped — it is just not yet its own agent.

## How work flows

1. Talk to **Mission Control**. It is the front door.
2. It inventories what exists before commissioning anything new.
3. It routes to exactly one owning agent per unit of work.
4. Nothing is "done" until Testing or Evidence produces the artifact named in the
   acceptance criteria.
5. Knowledge Vault records the decision and the lesson.

## Repository layout

```
.claude/agents/            active agent definitions (Tier 1)
agents/                    registry, activation rules, dormant specs
business/
  research/                dated, sourced findings
  content/                 published and drafted pieces
  growth/                  experiments and channel plans
  sales/                   pipeline and proposals
  knowledge-vault/         decisions, lessons, clients, products, reusable assets, brand
projects/<project>/
  STATE.md                 current state — the single answer to "where is this"
  PRODUCT.md               v1 scope and acceptance criteria
  SOLUTION.md              problem and solution architecture
  EVIDENCE/                test reports, screenshots, results
```
