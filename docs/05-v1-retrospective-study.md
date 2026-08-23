# 05 — V1: the retrospective study

## Why V1 is retrospective

The obvious V1 is *one disease → one protein → candidate binders*, then wait and
hope somebody finds something useful. That is a two-year experiment with a
binary, low-probability payoff and no interim signal.

A retrospective challenge makes "did the platform work?" answerable now:

```
KNOWN RESEARCH DATA
        ↓
  Hide known solution
        ↓
Give users the computational challenge
        ↓
  Users generate solutions
        ↓
   Platform ranks them
        ↓
Compare against known experimental data
```

Early on, that proof is worth more than 100,000 users. It is the difference
between "people played our science game" and "human-guided AI exploration
improves candidate discovery under controlled conditions" — the second is
research-paper territory, and it is what a sponsored challenge is sold against.

## The four arms

| Arm | Method |
|---|---|
| A | AI alone |
| B | Human alone |
| C | Human + AI copilot |
| D | Random computational search |

The result that matters:

```
Human + AI  >  AI alone  >  Human alone  >  Random
```

Any ordering is informative. `C ≈ A` says the copilot adds nothing; `C < A` says
it actively misleads, which is a finding worth publishing and worth knowing
before scaling.

## Primary endpoint

**Hit rate @ k.** For each arm, the fraction of its top *k* distinct candidates
(k = 10) reaching the held-out standard, under a fixed evaluation budget.

Fixed budget is what makes the arms comparable. An arm that evaluates ten times
as many candidates will find more; that is not intelligence, it is compute.

## Secondary endpoints

- **Evaluations to first hit** — search efficiency, not just eventual success.
- **Rediscovery** — how many of the specific held-out solutions were recovered.
  Distinct from hit rate: an arm can reach the target standard by a route the
  original researchers never took, which is the interesting case rather than a
  failure.
- **Distinct strategy clusters** — how much of the space the arm's approach
  covered (see [07](07-business-model-and-dashboard.md)).
- **Improvement over time** — best score in the final quarter of the budget
  versus the first quarter. For human arms this is learning; for automated arms
  it is convergence.
- **Teams versus individuals** — a distinct participant-level comparison.
- **Beginner trajectory** — do novices improve, and how fast.

## Success thresholds, declared in advance

| Claim | Threshold |
|---|---|
| The platform beats chance | Arm A, B or C hit rate exceeds Arm D by a margin surviving the pre-registered test |
| Humans contribute something | Arm C exceeds Arm A |
| The copilot helps rather than merely accelerates | Arm C exceeds Arm B **and** Arm A |
| Participants learn | Positive improvement slope in Arm B |

Declared before data collection. Choosing thresholds afterwards is how a null
result becomes a press release.

## Confounds that would invalidate the result

1. **Answer leakage.** If the target is searchable, participants find it outside
   the platform. Mitigation: compilation fails if any held-out value reaches
   player-facing output (see [02](02-challenge-compiler.md)); challenge selection
   must also confirm the answer is not trivially retrievable from public sources.
2. **Unequal budgets.** Compute per arm must be counted in evaluations, not
   wall-clock or session time.
3. **Selection bias in participants.** People who volunteer for RNA puzzles are
   not a general population. This limits generalisation, not internal validity —
   and it must be stated, not corrected away.
4. **Easy targets.** A structure that random search solves in forty draws
   discriminates between nothing. Difficulty must be calibrated against Arm D
   *before* recruiting.
5. **Multiple comparisons.** Four arms and six endpoints is twenty-four tests.
   Pre-register the primary endpoint; everything else is exploratory and labelled
   as such.
6. **The scoring model is not the world.** Every arm is measured against a
   computational model. Recovering a known answer under that model is evidence
   the *platform* works, not that any candidate is biologically meaningful.

## The harness, and what it is not

`discovery/study/` implements all of this and runs today:

```
$ python3 -m discovery.cli study challenges/rna-hairpin-v1.json --budget 200
```

**Arms B and C contain no humans.** They are scripted policies — a structural
move for the "human", a score-guided tweak for the "AI" — that exist to exercise
the harness before a single participant is recruited. They are marked `SIMULATED`
in every report, and the report prints:

> Arms marked SIMULATED contain no human participants. They are scripted policies
> used to exercise this harness. No result below is evidence about how people search.

No number this harness prints today is a finding about people. The study
specified above requires real participants; the code is the instrument, not the
result.

## Choosing the real V1 challenge

The bundled `rna-hairpin-v1.json` is a demonstration target constructed for this
repository, and says so in its own provenance field. A production retrospective
challenge needs:

- a published dataset with measured outcomes, cited by accession;
- a target hard enough that random search does not solve it within budget;
- a hold-out the platform's own authors cannot see during challenge design;
- a difficulty calibration run of Arm D before recruitment opens.
