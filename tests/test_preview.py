"""Synthetic CPU checks; no research data, model weights, or services."""
from __future__ import annotations

import copy
import csv
from importlib import resources
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from evidence_preview.artifacts import identity, read_json, seal, verify, write_json
from evidence_preview.cli import main
from evidence_preview.records import validate_records
from evidence_preview.reporting import descriptive_csv
from evidence_preview.statistics import holm, paired_comparison, score_summaries, summarize


def fixture():
    text = resources.files("evidence_preview").joinpath("examples/synthetic_records.json").read_text(encoding="utf-8")
    return json.loads(text)


def contrast(document, **options):
    return paired_comparison(document, treatment="system_a", control="system_b",
                             resamples=128, seed=0, **options)


class RecordChecks(unittest.TestCase):
    def test_complete_synthetic_grid(self):
        result = validate_records(fixture())
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["record_count"], 16)
        self.assertEqual(result["unresolved_count"], 0)

    def test_missing_cell_is_not_silently_dropped(self):
        document = fixture()
        document["rows"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete grid"):
            validate_records(document)

    def test_duplicate_cell_is_rejected(self):
        document = fixture()
        document["rows"].append(copy.deepcopy(document["rows"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_records(document)

    def test_undeclared_method_is_rejected(self):
        document = fixture()
        document["rows"][0]["method"] = "undeclared"
        with self.assertRaisesRegex(ValueError, "Undeclared"):
            validate_records(document)

    def test_extra_raw_content_fields_are_rejected(self):
        document = fixture()
        document["rows"][0]["question_text"] = "synthetic extra content"
        with self.assertRaisesRegex(ValueError, "Unexpected fields"):
            validate_records(document)

    def test_invalid_scores_are_rejected(self):
        for bad in (True, False, "1", float("nan"), float("inf"), -0.1, 1.1, [], {}):
            with self.subTest(value=repr(bad)):
                document = fixture()
                document["rows"][0]["score"] = bad
                with self.assertRaises(ValueError):
                    validate_records(document)

    def test_metadata_types_are_strict(self):
        for field, bad in (("format_version", True), ("synthetic", "true")):
            document = fixture()
            document[field] = bad
            with self.assertRaises(ValueError):
                validate_records(document)

    def test_clusters_must_partition_declared_questions(self):
        for clusters in ((["toy-item-a"],), [["toy-item-a"], ["toy-item-a"]], [[]]):
            document = fixture()
            document["clusters"] = clusters
            with self.assertRaises(ValueError):
                validate_records(document)

    def test_identifiers_cannot_inject_spreadsheet_formulas(self):
        document = fixture()
        document["methods"][0] = "=SUM(1,2)"
        with self.assertRaises(ValueError):
            validate_records(document)


class StatisticsChecks(unittest.TestCase):
    def test_equal_means_in_synthetic_example(self):
        result = score_summaries(fixture())
        self.assertTrue(all(row["mean_score"] == .5 for row in result["per_run"]))
        self.assertTrue(all(row["mean_score"] == .5 for row in result["macro"]))
        self.assertEqual(contrast(fixture())["estimate"], 0)

    def test_null_preserves_denominator_and_bounds(self):
        document = fixture()
        document["rows"][0]["score"] = None
        validation = validate_records(document)
        self.assertEqual(validation["unresolved_count"], 1)
        self.assertFalse(validation["all_scores_resolved"])
        result = score_summaries(document)
        row = next(row for row in result["per_run"]
                   if row["run_pair_id"] == "toy-pair-a" and row["method"] == "system_a")
        self.assertIsNone(row["mean_score"])
        self.assertEqual((row["score_lower"], row["score_upper"]), (.25, .5))
        self.assertEqual(row["question_count"], 4)
        with self.assertRaisesRegex(ValueError, "unresolved records cannot be dropped"):
            contrast(document)

    def test_all_unknown_scores_do_not_turn_into_zero(self):
        document = fixture()
        for row in document["rows"]:
            row["score"] = None
        report = score_summaries(document)
        for row in report["macro"]:
            self.assertIsNone(row["mean_score"])
            self.assertEqual((row["score_lower"], row["score_upper"]), (0, 1))

    def test_constant_effect_has_constant_interval(self):
        document = fixture()
        for row in document["rows"]:
            row["score"] = 1 if row["method"] == "system_a" else 0
        result = contrast(document)
        self.assertEqual(result["estimate"], 1)
        self.assertEqual(result["question_cluster_ci95"], [1, 1])
        self.assertEqual(result["run_effect_std"], 0)

    def test_negative_effect_is_retained(self):
        document = fixture()
        for row in document["rows"]:
            row["score"] = 0 if row["method"] == "system_a" else 1
        result = contrast(document)
        self.assertEqual(result["estimate"], -1)
        self.assertEqual(result["question_cluster_ci95"], [-1, -1])

    def test_order_of_input_rows_does_not_change_comparison(self):
        document = fixture()
        original = contrast(document)
        document["rows"].reverse()
        reordered = contrast(document)
        for field in ("estimate", "question_cluster_ci95", "run_pair_effects", "run_effect_std"):
            self.assertEqual(original[field], reordered[field])

    def test_point_estimate_is_question_weighted_with_unequal_clusters(self):
        document = fixture()
        document["clusters"] = [["toy-item-a", "toy-item-b", "toy-item-c"], ["toy-item-d"]]
        for row in document["rows"]:
            row["score"] = int(row["method"] == "system_a" and row["question_id"] != "toy-item-d")
        self.assertEqual(contrast(document)["estimate"], .75)

    def test_single_run_std_is_unknown_not_zero(self):
        document = fixture()
        document["run_pair_ids"] = ["toy-pair-a"]
        document["rows"] = [row for row in document["rows"] if row["run_pair_id"] == "toy-pair-a"]
        self.assertIsNone(contrast(document)["run_effect_std"])

    def test_single_cluster_cannot_claim_bootstrap_uncertainty(self):
        document = fixture()
        document["clusters"] = [document["question_ids"]]
        with self.assertRaisesRegex(ValueError, "At least two"):
            contrast(document)

    def test_paired_options_must_be_complete(self):
        with self.assertRaisesRegex(ValueError, "together"):
            summarize(fixture(), treatment="system_a")
        for resamples, seed in ((0, 0), (True, 0), (8, -1), (8, True)):
            with self.subTest(resamples=resamples, seed=seed):
                with self.assertRaises(ValueError):
                    paired_comparison(fixture(), treatment="system_a", control="system_b",
                                      resamples=resamples, seed=seed)

    def test_holm_family_and_monotonic_adjustment(self):
        result = holm({"a": .01, "b": .04, "c": .03}, ["a", "b", "c"])
        self.assertAlmostEqual(result["a"]["holm_p"], .03)
        self.assertAlmostEqual(result["c"]["holm_p"], .06)
        self.assertAlmostEqual(result["b"]["holm_p"], .06)
        with self.assertRaises(ValueError):
            holm({"a": .01}, ["a", "b"])
        with self.assertRaises(ValueError):
            holm({"a": True}, ["a"])

    def test_csv_labels_synthetic_and_keeps_unknown_means(self):
        document = fixture()
        document["rows"][0]["score"] = None
        rows = list(csv.DictReader(io.StringIO(descriptive_csv(summarize(document)))))
        self.assertTrue(all(row["synthetic"] == "True" for row in rows))
        self.assertEqual(sum(row["mean_score"] == "TBD" for row in rows), 1)


class ArtifactAndCliChecks(unittest.TestCase):
    def test_fingerprint_is_stable_and_detects_changes(self):
        self.assertEqual(identity({"a": 1, "b": 2}), identity({"b": 2, "a": 1}))
        report = seal("toy", {"synthetic": True, "value": 1})
        verify(report, "toy")
        report["value"] = 2
        with self.assertRaises(ValueError):
            verify(report, "toy")

    def test_artifact_metadata_cannot_be_overridden(self):
        for field in ("kind", "artifact_version", "artifact_id"):
            with self.assertRaises(ValueError):
                seal("toy", {field: "replacement"})

    def test_json_rejects_duplicate_keys_and_nonfinite_constants(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for text in ('{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(path)

    def test_write_never_overwrites_and_serializes_before_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "output.json"
            write_json(path, {"synthetic": True})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_json(path, {"synthetic": False})
            self.assertEqual(path.read_bytes(), original)
            invalid = Path(folder) / "invalid.json"
            with self.assertRaises(ValueError):
                write_json(invalid, {"value": float("nan")})
            self.assertFalse(invalid.exists())

    def test_demo_is_self_contained_and_explicitly_synthetic(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["demo"])
        self.assertEqual(code, 0)
        report = json.loads(stdout.getvalue())
        self.assertTrue(report["synthetic"])
        self.assertTrue(report["paired_comparison"]["synthetic"])

    def test_cli_invalid_input_does_not_create_report(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.json"
            output = Path(folder) / "report.json"
            document = fixture()
            document["rows"].pop()
            write_json(source, document)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["summarize", "--input", str(source), "--output", str(output)])
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
            self.assertIn("Incomplete grid", stderr.getvalue())

    def test_existing_csv_prevents_partial_json_output(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / "existing.csv"
            json_path = Path(folder) / "report.json"
            csv_path.write_text("retain", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = main(["demo", "--output", str(json_path), "--csv", str(csv_path)])
            self.assertEqual(code, 2)
            self.assertFalse(json_path.exists())
            self.assertEqual(csv_path.read_text(encoding="utf-8"), "retain")


if __name__ == "__main__":
    unittest.main()
