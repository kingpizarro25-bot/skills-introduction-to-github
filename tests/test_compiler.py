"""The compiler turns a scientific problem into a playable one -- and keeps the answer."""

from __future__ import annotations

import json
import unittest

from discovery.challenge.compiler import CompilerError, compile_challenge
from discovery.challenge.spec import ChallengeSpec, SpecError

from support import CHALLENGE_PATH, PERFECT, challenge, raw_spec, spec_with


class HeldOutAnswerTests(unittest.TestCase):
    def test_player_facing_output_never_contains_a_held_out_solution(self):
        compiled = challenge()
        rendered = json.dumps(compiled.player_facing()).upper()
        for solution in compiled.held_out_answer()["held_out_solutions"]:
            self.assertNotIn(solution.upper(), rendered)

    def test_brief_and_curriculum_do_not_contain_the_answer(self):
        compiled = challenge()
        text = (compiled.brief + " ".join(p.explanation for p in compiled.curriculum)).upper()
        for solution in compiled.held_out_answer()["held_out_solutions"]:
            self.assertNotIn(solution.upper(), text)

    def test_held_out_answer_is_still_reachable_for_the_study_harness(self):
        compiled = challenge()
        self.assertEqual(compiled.held_out_answer()["hit_threshold"], 1.0)
        self.assertIn(PERFECT, compiled.held_out_answer()["held_out_solutions"])

    def test_compilation_fails_when_a_validation_value_would_leak(self):
        data = raw_spec()
        # A researcher who names the answer as the starting point should not be
        # able to publish the challenge at all.
        data["variables"]["starting_point"] = "GCGCAAAAGCGC"
        data["validation"]["held_out_solutions"] = ["GCGCAAAAGCGC"]
        with self.assertRaises(CompilerError) as caught:
            compile_challenge(ChallengeSpec.from_dict(data))
        self.assertIn("leaked", str(caught.exception))


class CompilerValidationTests(unittest.TestCase):
    def test_starting_point_must_satisfy_the_challenge_constraints(self):
        data = raw_spec()
        data["variables"]["starting_point"] = "AAAAAAAAAAAA"
        with self.assertRaises(CompilerError) as caught:
            compile_challenge(ChallengeSpec.from_dict(data))
        self.assertIn("starting_point is not a legal candidate", str(caught.exception))

    def test_target_structure_length_must_match_declared_length(self):
        data = raw_spec()
        data["metric"]["target_structure"] = "((((....))))...."
        with self.assertRaises(CompilerError):
            compile_challenge(ChallengeSpec.from_dict(data))

    def test_unbalanced_target_structure_is_rejected(self):
        data = raw_spec()
        data["metric"]["target_structure"] = "((((....)))("
        with self.assertRaises(CompilerError):
            compile_challenge(ChallengeSpec.from_dict(data))

    def test_unknown_metric_is_rejected_rather_than_guessed(self):
        data = raw_spec()
        data["metric"] = {"id": "protein_binding_affinity"}
        with self.assertRaises(CompilerError) as caught:
            compile_challenge(ChallengeSpec.from_dict(data))
        self.assertIn("no compiler support", str(caught.exception))

    def test_compiler_emits_every_downstream_artifact(self):
        compiled = challenge()
        self.assertTrue(compiled.brief)
        self.assertTrue(compiled.curriculum)
        self.assertTrue(compiled.analytics_keys)
        self.assertEqual(compiled.sandbox.length, 12)
        self.assertEqual(compiled.governance.tier, "public")


class SpecTests(unittest.TestCase):
    def test_governance_tier_is_mandatory_and_checked(self):
        with self.assertRaises(SpecError):
            spec_with(governance={"tier": "whatever"})

    def test_public_challenge_must_name_a_license(self):
        with self.assertRaises(SpecError) as caught:
            spec_with(governance={"tier": "public"})
        self.assertIn("license", str(caught.exception))

    def test_missing_required_field_names_the_field(self):
        data = raw_spec()
        del data["objective"]
        with self.assertRaises(SpecError) as caught:
            ChallengeSpec.from_dict(data)
        self.assertIn("objective", str(caught.exception))

    def test_candidate_must_match_declared_length_and_alphabet(self):
        spec = ChallengeSpec.load(CHALLENGE_PATH)
        with self.assertRaises(SpecError):
            spec.validate_candidate("GGGG")
        with self.assertRaises(SpecError):
            spec.validate_candidate("GGGGTTTTCCCC")  # T is not in the RNA alphabet

    def test_candidate_is_checked_against_declared_constraints(self):
        spec = ChallengeSpec.load(CHALLENGE_PATH)
        with self.assertRaises(SpecError) as caught:
            spec.validate_candidate("AAAAAAAAAAAA")
        self.assertIn("no long homopolymer runs", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
