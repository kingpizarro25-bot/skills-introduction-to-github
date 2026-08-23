# 00 — Product definition

> A platform that turns biomedical research problems into safe computational
> challenges where humans and AI explore possible solutions together, while
> scientists retain control of experimental validation.

## What the product is not

It is not a binding-affinity app. Binding affinity is *one challenge type*. If the
company is built around a single scoring method, then RNA design, structure
problems, biomarker puzzles and optimisation tasks each require rebuilding the
company. The product is the layer that makes a new scientific problem a
**configuration**, not a software project: the compiler, the compute funnel, the
evidence discipline, and the governance around them.

Disease Sandbox is a feature of that platform, not the platform.

## The precedent, and the part that is actually new

Citizen science in this space is established, not speculative. Foldit showed that
non-experts could produce protein structure and design results that were taken
seriously enough to test. Eterna runs the full loop — players design RNA,
scientists synthesise and assay submissions, results return to the players — and
that loop has fed published work. The premise that non-experts can contribute to
hard computational search is not the risky part of this idea.

What is not established is the thing this platform exists to measure:

> Can thousands of humans working with AI systematically search scientific
> problem spaces better than either humans or AI working independently?

Foldit and Eterna demonstrate *that* people can help. They do not answer *when*,
*how much*, or *what kind of AI assistance makes human search better rather than
worse*. That is the open question, it is measurable, and it is the experiment the
company should be built around.

## The four questions the company is organised to answer

1. Do crowds outperform random search on bounded scientific problems?
2. Does AI assistance improve human results, or merely speed them up?
3. Does human + AI beat AI alone?
4. Which *kinds* of AI guidance improve human scientific problem solving?

Question 4 is the durable one. Questions 1–3 have a finite answer; question 4
produces a dataset that compounds — see [07](07-business-model-and-dashboard.md).

## Why "computational challenge" is the right unit

A challenge is bounded, safe, and evaluable:

- **Bounded** — the researcher declares the variables and constraints, so the
  search space is explicitly finite and reviewable before anyone plays.
- **Safe** — the platform hosts scoring of candidate designs against published
  computational models. It does not produce laboratory protocols, and it does not
  put anything in a body. Validation stays with accredited researchers.
- **Evaluable** — every challenge has a metric declared up front, which is what
  makes the retrospective study in [05](05-v1-retrospective-study.md) possible.

## Read next

- [01 — Architecture](01-architecture.md), the locked pipeline
- [03 — Evidence and limitations](03-evidence-and-limitations.md), the correction
  that matters most scientifically
- [05 — V1 retrospective study](05-v1-retrospective-study.md), how "did this
  work?" becomes answerable this year rather than in two
