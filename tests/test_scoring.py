"""Synthetic acceptance checks for the offline answer-to-report workflow."""
from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
from importlib import resources
import io
import json
from pathlib import Path
import tempfile
import unittest

from evidence_preview.artifacts import read_json
from evidence_preview.cli import main
from evidence_preview.records import validate_records
from evidence_preview.scoring import normalize_answer, score_answers


def answers():
    text = resources.files("evidence_preview").joinpath("examples/synthetic_answers.json").read_text(encoding="utf-8")
    return json.loads(text)


class ScoringChecks(unittest.TestCase):
    def test_unicode_case_punctuation_and_whitespace(self):
        self.assertEqual(normalize_answer("  ＢＬＵＥ\tＣＵＢＥ！ "), "blue cube")

    def test_normalization_does_not_silently_change_the_convention(self):
        self.assertNotEqual(normalize_answer("A-B"), normalize_answer("A B"))
        self.assertEqual(normalize_answer("the blue cube"), "the blue cube")
        self.assertNotEqual(normalize_answer("café"), normalize_answer("cafe"))

    def test_scored_fixture_matches_the_explicit_score_fixture(self):
        result = score_answers(answers())
        expected = json.loads(resources.files("evidence_preview").joinpath(
            "examples/synthetic_records.json").read_text(encoding="utf-8"))
        for field, value in expected.items():
            self.assertEqual(result[field], value)
        self.assertEqual(result["grading_protocol"], "normalized_exact_match_v1")
        self.assertEqual(validate_records(result)["grading_protocol"], "normalized_exact_match_v1")

    def test_null_and_empty_answers_are_distinct(self):
        source = answers()
        source["rows"][0]["answer"] = None
        source["rows"][1]["answer"] = ""
        result = score_answers(source)
        self.assertIsNone(result["rows"][0]["score"])
        self.assertEqual(result["rows"][1]["score"], 0)

    def test_output_does_not_copy_reference_or_answer_text(self):
        result = score_answers(answers())
        self.assertNotIn("accepted_answers", result)
        self.assertTrue(all(set(row) == {"question_id", "method", "run_pair_id", "score"}
                            for row in result["rows"]))

    def test_alias_validation_and_missing_references(self):
        for bad in ([], [""], ["!!!"], [None], "blue cube"):
            with self.subTest(alias=bad):
                source = answers()
                source["accepted_answers"]["toy-item-a"] = bad
                with self.assertRaises(ValueError):
                    score_answers(source)
        source = answers()
        del source["accepted_answers"]["toy-item-a"]
        with self.assertRaises(ValueError):
            score_answers(source)

    def test_population_and_type_errors_do_not_become_incorrect_answers(self):
        for mutation in ("missing", "duplicate", "invalid-answer", "wrong-grader"):
            source = answers()
            if mutation == "missing":
                source["rows"].pop()
            elif mutation == "duplicate":
                source["rows"].append(copy.deepcopy(source["rows"][0]))
            elif mutation == "invalid-answer":
                source["rows"][0]["answer"] = False
            else:
                source["grading_protocol"] = "undeclared-grader"
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    score_answers(source)

    def test_cli_answer_to_paired_report(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "answers.json"
            scored = Path(folder) / "scores.json"
            output = Path(folder) / "report.json"
            source.write_text(json.dumps(answers()), encoding="utf-8")
            self.assertEqual(main(["score", "--input", str(source), "--output", str(scored)]), 0)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["validate", "--input", str(scored)]), 0)
            self.assertEqual(main(["summarize", "--input", str(scored), "--output", str(output),
                                   "--treatment", "system_a", "--control", "system_b",
                                   "--resamples", "64", "--seed", "0"]), 0)
            report = read_json(output)
            self.assertTrue(report["synthetic"])
            self.assertEqual(report["descriptive"]["validation"]["grading_protocol"], "normalized_exact_match_v1")

    def test_cli_scoring_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "answers.json"
            output = Path(folder) / "scores.json"
            source.write_text(json.dumps(answers()), encoding="utf-8")
            output.write_text("preserve", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["score", "--input", str(source), "--output", str(output)]), 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
