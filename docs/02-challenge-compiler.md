# 02 — The Challenge Compiler

Researchers should not have to design games.

Without this layer, every new disease is a custom software project — and humans
apparently enjoy rebuilding identical infrastructure until venture funding runs
out. With it, a new challenge is a data file.

## What the researcher provides

Six things, none of which require knowing anything about interface design:

| Input | Meaning | Field |
|---|---|---|
| Scientific objective | What you are trying to find out | `objective` |
| Known data | What is already public or given | `known_data` |
| Allowed variables | What participants may change | `variables` |
| Constraints | What makes a candidate illegal | `constraints` |
| Evaluation metric | How candidates are scored | `metric` |
| Validation data | The held-out answer, if there is one | `validation` |

Plus one thing that is not optional: `governance`, which states the IP and
attribution terms before anyone plays. See [06](06-governance-and-ip.md).

## What the compiler produces

```
Scientific research problem
          ↓
   CHALLENGE COMPILER
          ↓
Beginner-friendly objective   →  brief
Interactive sandbox           →  alphabet, length, starting point, editable positions
Scoring rules                 →  metric id, params, promotion threshold
AI teaching system            →  curriculum (what the copilot may explain)
Researcher analytics          →  analytics keys the dashboard aggregates on
```

The generated brief for the V1 challenge, produced entirely from the spec:

```
You are designing an RNA sequence 12 letters long, using only A, C, G, U.
RNA folds back on itself: some letters pair up, and the pattern of pairs is its shape.
Your goal is to find a sequence that folds into this target shape:
    ((((....))))
'(' and ')' mark a paired position; '.' marks an unpaired one.
You score higher the more positions fold the way the target says they should.
```

Nobody wrote that for this challenge. Changing the target structure changes the
brief, the sandbox and the scoring together.

## The compiler is a security boundary

`validation` holds the answer. The retrospective design in
[05](05-v1-retrospective-study.md) depends on it never reaching a participant, so
the split is enforced in code rather than by convention:

- `CompiledChallenge.player_facing()` builds the participant's view field by
  field. It cannot accidentally include a field nobody listed.
- `CompiledChallenge.held_out_answer()` is named awkwardly on purpose. Every call
  site is greppable, and no player-facing code path contains one.
- `compile_challenge()` **fails compilation** if any held-out value appears in
  the player-facing output. A researcher who sets the answer as the starting
  point cannot publish the challenge at all.

Tests: `tests/test_compiler.py::HeldOutAnswerTests`.

## Adding a challenge type

One entry in each of three tables in `discovery/challenge/compiler.py`:

```python
_METRIC_BRIEFS      = {"rna_structure_match": "...", "binding_affinity": "..."}
_METRIC_CURRICULUM  = {...}   # what the copilot is allowed to teach
_METRIC_ANALYTICS   = {...}   # what the researcher dashboard aggregates
```

...plus a scorer declaring its capabilities. Everything else — funnel,
comparative rendering, evidence, limitations, study harness — already works,
because none of it knows what RNA is.

That is the claim this slice exists to test. It is one metric today; the second
metric is the one that proves it, and it is deliberately not written yet.

## Validation the compiler performs

- Required fields present; governance tier recognised; public challenges name a
  licence.
- Target structure is balanced and matches the declared length.
- The starting point is itself a legal candidate under the challenge's own
  constraints. (This was a real bug during development: a starting sequence of
  twelve A's violated the challenge's own homopolymer limit, and every arm of the
  study crashed on its first move.)
- Unknown metric ids are rejected rather than guessed at.
