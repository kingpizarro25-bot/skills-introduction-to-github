"""Command line entry point for the vertical slice.

    python3 -m discovery.cli run   challenges/rna-hairpin-v1.json --candidate GGGGAAAACCCC
    python3 -m discovery.cli study challenges/rna-hairpin-v1.json --budget 200

`run` plays one candidate through the whole pipeline: compile, score on the fast
tier, rank comparatively, report evidence and limitations, and show what the
copilot would say. `study` runs the retrospective four-arm harness.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Sequence

from .challenge.compiler import CompiledChallenge, compile_challenge
from .challenge.spec import ChallengeSpec, SpecError
from .copilot import Copilot
from .evaluation.comparative import render
from .evaluation.evidence import assess
from .evaluation.limitations import provenance_for
from .funnel import FunnelLedger, evaluate
from .scoring.base import ScoreResult
from .scoring.registry import deployment_report
from .study.retrospective import run_study


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="discovery", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="score a candidate through the full pipeline")
    run_parser.add_argument("challenge", help="path to a challenge JSON file")
    run_parser.add_argument("--candidate", required=True, help="the candidate to score")
    run_parser.add_argument(
        "--history",
        nargs="*",
        default=[],
        help="earlier attempts by the same participant, oldest first",
    )
    run_parser.add_argument(
        "--show-limitations",
        action="store_true",
        help="show which missing backend capability produced each limitation",
    )

    study_parser = sub.add_parser("study", help="run the retrospective four-arm harness")
    study_parser.add_argument("challenge", help="path to a challenge JSON file")
    study_parser.add_argument("--budget", type=int, default=200, help="evaluations per arm")
    study_parser.add_argument("--seed", type=int, default=20260823)

    args = parser.parse_args(argv)
    try:
        compiled = compile_challenge(ChallengeSpec.load(args.challenge))
    except (SpecError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.command == "run":
        return _run(compiled, args)
    return _study(compiled, args)


def _run(compiled: CompiledChallenge, args) -> int:
    ledger = FunnelLedger()
    cohort: List[ScoreResult] = []

    # The challenge's own starting point is always scored, so every result has
    # something to be compared against and the renderer never has to be bypassed.
    baseline = evaluate(compiled, compiled.sandbox.starting_point, ledger=ledger)
    cohort.append(baseline.fast)

    try:
        for attempt in args.history:
            record = evaluate(compiled, attempt, cohort=cohort, ledger=ledger)
            cohort.append(record.fast)
        record = evaluate(compiled, args.candidate, cohort=cohort, ledger=ledger)
    except SpecError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    result = record.fast

    print(compiled.governance.as_banner())
    print()
    print(compiled.brief)
    print()
    print("=" * 72)
    print()

    evidence = assess(
        result,
        cohort_size=len(cohort),
        experimental_records=compiled.experimental_records,
    )
    print(render(result, cohort + [result], evidence))
    print()

    if args.show_limitations:
        print("WHERE THOSE LIMITATIONS COME FROM")
        deployment = deployment_report()
        print(f"  fast backend: {deployment['fast_backend']}")
        print(f"  deep backend: {deployment['deep_backend'] or 'none installed'}")
        for phrase, capability in provenance_for(result.modeled).items():
            print(f"  • {phrase}  <- no active backend declares {capability!r}")
        print()

    print("=" * 72)
    print()
    print("COMPUTE FUNNEL")
    print(f"  {record.reason}")
    print(f"  deep tier: {record.deep_status}")
    print(f"  strategy signature: {record.strategy_signature}")
    print()

    copilot = Copilot(compiled)
    print("COPILOT")
    print(f"  compare:   {copilot.compare(result, cohort)}")
    if len(cohort) >= 1:
        print(f"  interpret: {copilot.interpret(cohort[-1], result)}")
    print(f"  question:  {copilot.question(result)}")
    return 0


def _study(compiled: CompiledChallenge, args) -> int:
    print(run_study(compiled, budget=args.budget, seed=args.seed).render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
