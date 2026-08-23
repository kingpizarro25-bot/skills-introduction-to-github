# 06 — Governance, IP and attribution

## The rule we are explicitly not adopting

> High-scoring public hypotheses automatically enter a shared IP pool controlled
> by the platform.

Not as a default. Biomedical citizen science raises real questions about
ownership, access, credit, commercialisation and benefit sharing, and the
governance literature is consistent on the remedy: make the arrangements
transparent up front and account for contributors' reasonable expectations.

An automatic assignment to the platform fails both halves. Contributors who
believe they are doing open science discover afterwards that they were doing
unpaid R&D for a company, and the platform's most valuable asset — people's
willingness to contribute — is the thing it spends.

## Three tiers, declared before anyone plays

### Public challenges

Explicitly open research.

```
Contributor attribution
        +
Open research license
        +
Transparent publication policy
```

Nothing is assigned to the platform. Negative results are published too — a
platform that only publishes wins is producing marketing, not evidence.

### Sponsored challenges

A university, nonprofit or company defines the terms in advance.

```
Sponsor owns / licenses agreed outputs
        +
Participants knowingly accept terms before their first submission
        +
Possible rewards or prizes
```

The load-bearing word is *beforehand*. A participant must see the terms before
their first submission, not in a footer.

### Private institutional challenges

Not crowdsourced publicly at all.

```
Private datasets · private models · private IP · institutional license
```

Used by a single institution's own researchers. It shares the compiler, funnel
and evidence discipline; it shares no data with the public platform.

## Enforced at the spec level

`governance` is a required field. A challenge cannot compile without it:

```python
if tier not in ("public", "sponsored", "private"):
    raise SpecError("Every challenge must state its IP and attribution terms up front.")
if tier == "public" and not governance.get("license"):
    raise SpecError("public challenges must name an open research license")
```

The tier, licence, attribution and publication policy are rendered as a banner
above the challenge brief — the participant sees the terms in the same view as
the problem, every time, not once at sign-up.

```
GOVERNANCE: PUBLIC CHALLENGE
  License: CC BY 4.0
  Attribution: Contributors are named on any publication describing results from this challenge.
  Publication: Results, including negative results, are published openly. No contribution is assigned to the platform.
```

## Open questions this document does not settle

Deliberately flagged rather than papered over — each needs a decision before a
sponsored challenge runs, and none should be decided by an engineer:

- What attribution threshold earns named authorship versus a contributor list?
- Who decides when a public candidate moves to laboratory validation, and who
  pays?
- What happens when a public-challenge candidate turns out to be commercially
  valuable? (The publication policy is the answer, which is why it must be
  written before the situation arises, not after.)
- How are contributions from minors handled, given that both precedent platforms
  attract them?
