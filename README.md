# AI-Guided Biomedical Challenge Platform

> A platform that turns biomedical research problems into safe computational
> challenges where humans and AI explore possible solutions together, while
> scientists retain control of experimental validation.

This branch holds the V1 specification and a runnable vertical slice that proves
the central abstraction: a challenge is a **data file**, not a software project.

## Specification

| | |
|---|---|
| [00 — Product definition](docs/00-product-definition.md) | What the product is, and the experiment the company is built around |
| [01 — Architecture](docs/01-architecture.md) | The locked pipeline, and where each stage lives in code |
| [02 — Challenge compiler](docs/02-challenge-compiler.md) | Researcher inputs → playable challenge |
| [03 — Evidence and limitations](docs/03-evidence-and-limitations.md) | The replacement for the confidence meter |
| [04 — Comparative scoring](docs/04-comparative-scoring.md) | `MODEL RESULT ≠ BIOLOGICAL FACT`, and the copilot's four jobs |
| [05 — V1 retrospective study](docs/05-v1-retrospective-study.md) | The four-arm proof-of-concept protocol |
| [06 — Governance and IP](docs/06-governance-and-ip.md) | Public / sponsored / private tiers |
| [07 — Business model and dashboard](docs/07-business-model-and-dashboard.md) | Economics, human search intelligence, and where the moat actually is |

## Running the slice

No dependencies. Python 3.11+, standard library only.

```bash
# Score a candidate through the whole pipeline
python3 -m discovery.cli run challenges/rna-hairpin-v1.json --candidate GGGGAAAACCCC

# ...with the provenance of each limitation line
python3 -m discovery.cli run challenges/rna-hairpin-v1.json \
    --candidate GGGGAAAACCCC --history GGCGAAAAACCC --show-limitations

# Run the retrospective four-arm harness
python3 -m discovery.cli study challenges/rna-hairpin-v1.json --budget 200

# Tests
python3 -m unittest discover -s tests -v
```

## What this slice is and is not

**Is:** a working challenge compiler, a fast scoring tier, comparative-only
result rendering, derived limitations, a compute funnel with a real promotion
boundary, a copilot with an enforced claim guard, and a retrospective study
harness.

**Is not:** a production platform, a UI, or a source of biological claims. The
study harness's two "human" arms are scripted simulations, labelled as such in
every report — they exercise the instrument, and produce no finding about people.
An optional ViennaRNA backend is detected if installed; nothing substitutes for
it when it is absent.

---

# Introduction to GitHub

<img src="https://octodex.github.com/images/Professortocat_v2.png" align="right" height="200px" />

Hey kingpizarro25-bot!

Mona here. I'm done preparing your exercise. Hope you enjoy! 💚

Remember, it's self-paced so feel free to take a break! ☕️

[![](https://img.shields.io/badge/Go%20to%20Exercise-%E2%86%92-1f883d?style=for-the-badge&logo=github&labelColor=197935)](https://github.com/kingpizarro25-bot/skills-introduction-to-github/issues/1)

---

&copy; 2025 GitHub &bull; [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md) &bull; [MIT License](https://gh.io/mit)

