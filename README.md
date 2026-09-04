# Pizarro Studios OS

**Pizarro Studios** is the company. **Pizarro Studios OS** is the internal system it
runs on — the agents, project state, evidence, decisions, lessons, workflows, and
reusable business knowledge, in one version-controlled place.

This is an internal operating system, not a customer-facing product. Nothing here ships
to a client.

## Start here

Talk to **Mission Control**. It is the front door — it inventories what already
exists, routes the work to exactly one owning agent, and tracks what is finished,
blocked, and next.

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

Ten agents are active. Thirty more are specified but dormant — they activate on a
written trigger, not on enthusiasm. See [`agents/README.md`](agents/README.md) for the
full registry and [`agents/ACTIVATION.md`](agents/ACTIVATION.md) for the rules.

Company context, priorities, approval gates, and working style live in
[`CLAUDE.md`](CLAUDE.md) — loaded automatically by every agent, so it never has to be
re-explained.

Project status lives in [`projects/`](projects/README.md). All six projects currently
read `unknown` because nothing has been verified in this system yet — priority 1 is
fixing exactly that.

## The two rules that make this work

1. **Nothing is "done" without evidence.** A test report, a screenshot, a link, a
   number. Agents report *verified / partially verified / not tested / blocked* — never
   "it works" on faith.
2. **One owner per unit of work.** Two agents editing the same thing is worse than one
   agent being busy.

## Layout

| Path | Contents |
|---|---|
| `.claude/agents/` | The 10 active agent definitions |
| `agents/` | Registry, activation rules, dormant specialist specs |
| `business/research/` | Dated, sourced findings |
| `business/content/` | Drafted and published pieces |
| `business/growth/` | Experiments and channel plans |
| `business/sales/` | Pipeline and proposals |
| `business/knowledge-vault/` | Decisions, lessons, clients, products, reusable assets, brand |
| `projects/<name>/` | `STATE.md`, `PRODUCT.md`, `SOLUTION.md`, `EVIDENCE/` |
| `CLAUDE.md` | Company context, priorities, approval gates, working style |
| `docs/` | Standards, starting with the Agent Builder |

Start a new project by copying `projects/_TEMPLATE/STATE.md`. That file is the single
authoritative answer to "where is this project" — if it disagrees with a chat or a
memory, the file wins.

## Secrets

None, ever, in this repository. Keys, tokens, passwords, and customer data live in
environment variables or a secret manager. `business/knowledge-vault/` stores decisions
and lessons, not credentials or personal data.

## Adding an agent

Read [`docs/AGENT_BUILDER.md`](docs/AGENT_BUILDER.md) first. Its opening rule: if an
existing agent covers 80% of the work, improve that agent instead of creating another
one. Ten active agents is the target, not a starting point.
