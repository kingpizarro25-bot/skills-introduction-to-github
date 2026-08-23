# 03 — Evidence and limitations

**This is the single most important scientific correction in the design.**

## Do not ship this

```
Confidence: 87%
```

A percentage asserts a calibrated probability. Unless there is a model
demonstrating what 87% means — that of all candidates scored 87%, roughly 87%
behaved as predicted in an experiment — the number borrows the authority of a
measurement nobody made. It is scientific-looking astrology, and it is worse than
showing nothing, because a user cannot tell the difference by looking.

## Ship this instead

Three separate ideas, presented separately, allowed to disagree.

### 1. Prediction

```
PREDICTION
  Predicted structural agreement   8.4 / 10
  Defined only within this challenge's scoring model (nussinov-base-pair-maximisation, fast tier).
```

A metric-native number, scoped explicitly to the model that produced it.

### 2. Evidence strength

```
EVIDENCE STRENGTH
  Structural fit        Limited  — pair counting only, no energetics
  Comparison evidence   Moderate — ranked against 11 other candidates
  Experimental evidence None     — no laboratory result exists for this candidate
```

Three axes on a four-point scale (None / Limited / Moderate / Strong). There is
deliberately **no function anywhere that combines them into one figure**, because
the first thing anyone would do with such a function is put it back in a badge.

Each axis is derived, not asserted:

| Axis | Derived from |
|---|---|
| Structural fit | The capabilities the scoring backend declares, **capped before the score is considered** |
| Comparison evidence | How many other candidates this one was ranked against |
| Experimental evidence | Linked laboratory records, which is zero by default |

The cap is the load-bearing part. A perfect 10.0 from a model that only counts
base pairs is still `Limited` structural evidence, and no amount of scoring well
can lift it. Scoring well is not evidence that the model was worth trusting.

### 3. Limitations

```
THIS MODEL DOES NOT CURRENTLY ACCOUNT FOR:
  • stacking energetics between adjacent pairs
  • the entropic cost of loops and bulges
  • pseudoknotted (crossing) structures
  • competing alternative folds, not just one
  • ion concentration and buffer conditions
  • the full cellular environment
  • metabolism and degradation in a living system
  • toxicity in humans
  • clinical effectiveness
  • laboratory confirmation
```

### And then, always

```
Computational candidate. Not experimentally validated.
```

## The mechanism: limitations are derived, not written

Nobody hand-authors that list per challenge. Every scoring backend declares the
`Capability` values it actually models. The limitations list is the complement of
what the installed backends declare.

The consequence is that the honest thing happens by default:

| Installed backends | Limitations lines | Structural fit ceiling |
|---|---|---|
| Pair-counting only (this environment) | 10 | Limited |
| Pair counting + energy model + ensemble | 7 | Strong |

Remove a backend and the list gets longer on its own. Nobody has to remember.

Five capabilities are marked `NEVER_COMPUTATIONAL` — cellular environment,
metabolism, human toxicity, clinical effectiveness, laboratory confirmation — and
`validate_capabilities()` raises at registration time if a backend author claims
one. Those five always appear in the limitations list of every computational
result the platform will ever produce.

## Enforced, not encouraged

`tests/test_honesty.py` is where these promises live:

- `ScoreResult` has no `confidence`, `probability`, `certainty` or `p_value`
  field, and `EvidenceStrength` has no combined figure.
- Every rendered result contains the limitations block and the footer.
- Rendered output passes the copilot's claim guard, which rejects
  calibrated-confidence phrasing.
- Swapping in a weaker backend measurably lengthens the limitations list and
  weakens structural evidence.
- A perfect score does not raise structural evidence above the backend's ceiling.

If one of those fails, the platform has started making claims it cannot support.
