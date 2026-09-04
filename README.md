# Pizarro Studios — AI Business Operating System

Version-controlled source of truth for how Pizarro Studios runs: the agents, the
decisions, the evidence, and the projects.

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

Start a new project by copying `projects/_TEMPLATE/STATE.md`. That file is the single
authoritative answer to "where is this project" — if it disagrees with a chat or a
memory, the file wins.

## Secrets

None, ever, in this repository. Keys, tokens, passwords, and customer data live in
environment variables or a secret manager. `business/knowledge-vault/` stores decisions
and lessons, not credentials or personal data.

---

*This repository began as a GitHub Skills exercise fork; the original tutorial
workflows remain under `.github/`.*
