# 07 — Business model and the researcher dashboard

## Economics follow the challenge, not the user

The intuitive tiering — Free User / Academic / Pharma — prices the wrong object.
Individual participants are not the unit of value; **challenges** are.

```
PUBLIC DISCOVERY PLATFORM
        ↓
Build community + evidence
SPONSORED RESEARCH CHALLENGES
        ↓
Universities / nonprofits / biotech
PRIVATE DISCOVERY WORKSPACES
        ↓
Biotech / pharma R&D
COMPUTATIONAL ANALYTICS
        ↓
Candidate clustering · search-pattern analysis · human-AI performance analysis
VALIDATION PARTNERS
        ↓
External laboratories
```

API / platform licensing comes later, once the compiler has proven it handles
challenge types its authors did not anticipate — not before.

Note the ordering: the public platform is not a loss-leader for the paid tiers,
it is the instrument that produces the evidence the paid tiers are sold on. If
[05](05-v1-retrospective-study.md) returns a null result, the sponsored tier has
nothing to sell.

## The researcher dashboard

Researchers should see what players cannot. Not a leaderboard — a funnel:

```
10,482 simulations
       ↓
  312 unusual candidates
       ↓
   47 distinct strategy clusters
       ↓
   12 reproducible patterns
       ↓
    6 high-confidence computational candidates
       ↓
    3 selected for deeper analysis
```

`FunnelLedger.summary()` produces the top of this today: evaluations, promotions,
distinct strategy clusters, largest cluster, deep-tier runs, best fast score.

One correction to the diagram above, for consistency with
[03](03-evidence-and-limitations.md): the sixth row cannot be labelled
"high-confidence". Inside the product it reads *candidates cleared for expert
review*, with the same three-axis evidence block attached that participants see.
The dashboard is not exempt from the honesty rules — researchers are exactly the
audience most likely to act on an unearned number.

## Human search intelligence

The genuinely distinctive layer. The system studies *how people found things*:

> 318 players independently began preserving structural region A while changing
> region C.

That is a signal, and it is not in the candidates. `strategy_signature()` records
which named regions each attempt held still and which it varied; the ledger
counts them. Cluster counts are already a secondary endpoint in the study design.

The company is therefore not merely collecting molecular candidates. It is
collecting **strategies for navigating scientific search spaces**.

## Where the moat actually is

Not the AI model — comparable models are obtainable. Not the visualiser — those
exist. Not the citizen-science game itself — Foldit and Eterna demonstrated that
concept, and Eterna in particular has run the design → synthesis → assay → feedback
loop for years.

The moat is the dataset that only this loop produces:

```
Millions of human search decisions
          +
Scientific outcome data
          +
AI recommendations
          +
Experimental validation feedback
          ↓
Dataset showing HOW humans + AI search biological spaces
```

From which the system can eventually learn the question nobody currently has data
to answer:

> Which kinds of AI guidance actually improve human scientific problem solving?

That is bigger than gamification, it compounds, and it cannot be bought.

## The honest caveat about the moat

It is a moat *later*. It requires participants at volume, outcome data, and
validation feedback — none of which exist on day one, and the last of which is
gated by laboratory partners the platform does not control. Everything in this
document after "sponsored challenges" is contingent on
[05](05-v1-retrospective-study.md) returning a usable result first.
