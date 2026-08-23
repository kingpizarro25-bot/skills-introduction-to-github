# 04 — Comparative scoring and the copilot

## MODEL RESULT ≠ BIOLOGICAL FACT

The AI must not say:

> This molecule binds strongly.

It should say:

> Within this challenge and scoring model, Candidate B scored higher than
> Candidates A and C primarily because it recreated two more of the target's
> base pairs.

The distinction is not politeness. A score presented alone invites the reading
"this is good". A score presented in a ranking invites the reading "this scored
higher than those, under this model" — which is the only claim the platform can
actually support. Teaching users to hold that distinction is one of the most
valuable things the product does, and it costs nothing to build in.

## The renderer refuses absolute scores

This is not a style guideline. `discovery/evaluation/comparative.py::render`
raises `NoComparatorError` when asked to present a candidate with nothing to rank
against.

```python
>>> render(lone_result, [lone_result], evidence)
NoComparatorError: candidate 'GGGGAAAACCCC' has nothing to compare against;
score at least the challenge starting point before presenting a result
```

The fix is never to relax the check — it is to score a baseline. Every challenge
ships a starting point, so a baseline always exists. The CLI scores it
automatically before anything else, which is why no user ever meets this error.

There is no `render_score_only()` and no flag that strips the limitations block,
because a caller in a hurry is exactly the caller who would strip it.

## The copilot's four jobs, and no fifth

**TEACH** — "Here's what you're trying to optimize."
Drawn from the compiled curriculum. It will not improvise on a topic the compiler
did not generate; asking about an unlisted topic raises rather than guessing.

**INTERPRET** — "Your last change improved geometric compatibility but reduced stability."
```
You changed 2 position(s): 2, 8. That recovered 2 more of the target's pairs.
Score moved 6.7 -> 10.0 under nussinov-base-pair-maximisation.
```
When a change adds pairs that are not the target's pairs, it says so explicitly:
*the sequence is folding somewhere else*.

**COMPARE** — "Candidate 17 performs better than your previous five attempts."
Always against the participant's own history, always with the reason stated in
counts rather than adjectives.

**QUESTION** — "What happens if you preserve region A and modify region B?"
Points at a region of disagreement. It does not supply a candidate, and tests
assert it never emits a held-out solution.

## What it must not do

Continuously generate authoritative biological claims. That is what preserves the
part humans are actually contributing: **search strategy and intuition**. A
copilot that hands over conclusions replaces the thing it was supposed to
amplify.

`assert_comparative()` runs on every string the copilot emits and raises
`AbsoluteClaimError` on:

| Pattern | Why |
|---|---|
| "binds strongly / tightly / well" | asserts a binding outcome |
| "is safe / toxic / effective / therapeutic" | asserts a clinical property |
| "will cure / treat / work / bind / fold" | predicts a real-world outcome |
| "proven to" | claims proof |
| "this molecule works" | asserts efficacy |
| "in vivo … will/does/shows" | extrapolates beyond the model |
| "confidence: 87", "92% confident" | reports a calibration that does not exist |

The guard runs on **output**, not on intent, so a future template cannot quietly
opt out of it. `tests/test_copilot.py` asserts each pattern is blocked and that
all four jobs survive the guard.
