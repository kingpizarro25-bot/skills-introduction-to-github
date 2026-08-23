# 01 — Architecture

The canonical pipeline. Other documents reference this diagram rather than
redrawing it.

```
                 RESEARCH INSTITUTION
                         │
                         ▼
                CHALLENGE COMPILER            ← docs/02
                         │
                         ▼
                  DISEASE CHALLENGE
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
            LEARN    EXPERIMENT   AI COPILOT  ← docs/04
                          │
                          ▼
                   FAST SIMULATION            ← discovery/scoring
                          │
                          ▼
                  COMPARATIVE SCORE           ← docs/04
                          │
                          ▼
                     LIMITATIONS              ← docs/03
                          │
                          ▼
                   CANDIDATE FILTER           ← discovery/funnel.py
                         / \
                        /   \
                     LOW    HIGH
                      │       │
                    STORE     ▼
                         DEEP COMPUTE
                              │
                              ▼
                      RESEARCH DASHBOARD      ← docs/07
                              │
                              ▼
                        EXPERT REVIEW
                              │
                              ▼
                     EXTERNAL VALIDATION
                              │
                              ▼
                        RESULT DATA
                              │
                              ▼
                    MODEL + HUMAN LEARNING
```

## The five properties this shape is chosen for

**1. The compiler is the only place that knows about game design.**
Everything downstream consumes a `CompiledChallenge`. Adding a challenge type
means adding a metric to the compiler, not building a product.

**2. Scoring is tiered, and the tiers are honest about each other.**
The fast tier runs on every edit. The deep tier runs on candidates that earn it.
When no deep backend is installed, the funnel records a candidate as *queued* —
never as refined. `discovery/funnel.py` returns `deep=None` with an explicit
status string rather than silently substituting the fast score.

**3. Limitations are derived, not authored.**
Backends declare capabilities; the limitations list is the complement of that
declaration. Install a weaker backend and the list lengthens by itself. This is
the mechanism that makes [03](03-evidence-and-limitations.md) structural rather
than a matter of editorial discipline.

**4. The validation boundary is one-way.**
The platform ranks and explains. It does not run experiments, and it does not
assert that a candidate is biologically meaningful. External laboratory
validation is a separate step performed by researchers who own that
responsibility.

**5. Results return to both the model and the participants.**
The final arrow is not decorative. Experimental outcomes are the only thing that
can eventually calibrate the platform's predictions, and they are what turn the
search-strategy dataset in [07](07-business-model-and-dashboard.md) from
interesting into valuable.

## Where the code sits

| Pipeline stage | Module |
|---|---|
| Challenge definition | `discovery/challenge/spec.py` |
| Challenge compiler | `discovery/challenge/compiler.py` |
| Fast simulation | `discovery/scoring/nussinov.py` |
| Deep compute | `discovery/scoring/vienna.py` (optional) |
| Backend capability reporting | `discovery/scoring/registry.py` |
| Comparative score | `discovery/evaluation/comparative.py` |
| Evidence strength | `discovery/evaluation/evidence.py` |
| Limitations | `discovery/evaluation/limitations.py` |
| Candidate filter / funnel | `discovery/funnel.py` |
| AI copilot | `discovery/copilot.py` |
| Retrospective study | `discovery/study/` |
