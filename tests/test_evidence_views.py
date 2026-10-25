"""Artificial records exercise the released core projection component."""
from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
from importlib import resources
import io
import json
from pathlib import Path
import tempfile
import unittest

from evidence_preview.artifacts import verify
from evidence_preview.cli import main
from evidence_preview.evidence_views import EvidenceProjector


def evidence():
    text = resources.files("evidence_preview").joinpath("examples/synthetic_evidence.json").read_text(encoding="utf-8")
    return json.loads(text)


class EvidenceViewChecks(unittest.TestCase):
    def test_full_projection_preserves_all_records_in_original_order(self):
        document = evidence()
        result = EvidenceProjector(document).project()
        verify(result, "evidence-projection")
        self.assertEqual(result["retained_record_ids"], [r["record_id"] for r in document["records"]])
        self.assertEqual(result["record_view"]["records"],
                         [{"source_id": r["source_id"], "text": r["text"]} for r in document["records"]])
        self.assertEqual(len(result["call_inputs"]), len(document["calls"]))

    def test_dependency_closure_includes_shared_locator(self):
        projector = EvidenceProjector(evidence())
        self.assertEqual(projector.dependency_closure(["toy-unit-content-a"]),
                         frozenset({"toy-unit-content-a", "toy-unit-locate"}))

    def test_missing_predecessors_are_rejected_not_added(self):
        projector = EvidenceProjector(evidence())
        with self.assertRaisesRegex(ValueError, "Missing dependencies"):
            projector.project(["toy-unit-content-a"])

    def test_deleting_a_unit_removes_its_entire_serial_chain(self):
        projector = EvidenceProjector(evidence())
        retained = projector.delete_unit_and_dependents("toy-unit-content-a")
        result = projector.project(retained)
        self.assertNotIn("toy-record-a1", result["retained_record_ids"])
        self.assertNotIn("toy-record-a2", result["retained_record_ids"])
        self.assertNotIn("toy-call-a1", [c["call_id"] for c in result["call_inputs"]])
        self.assertNotIn("toy-call-a2", [c["call_id"] for c in result["call_inputs"]])
        self.assertIn("toy-unit-content-b", retained)
        self.assertIn("toy-unit-check", retained)

    def test_deleting_the_shared_locator_removes_all_dependents(self):
        projector = EvidenceProjector(evidence())
        retained = projector.delete_unit_and_dependents("toy-unit-locate")
        self.assertEqual(retained, frozenset())
        result = projector.project(retained)
        self.assertEqual(result["retained_record_ids"], ["toy-record-initial"])
        self.assertEqual(result["support_status"], "not_assessed")

    def test_call_histories_have_no_future_records(self):
        document = evidence()
        result = EvidenceProjector(document).project()
        events = {c["call_id"]: c["event_index"] for c in document["calls"]}
        for row in result["call_inputs"]:
            expected = [r["source_id"] for r in document["records"] if r["event_index"] < events[row["call_id"]]]
            actual = [m["source_id"] for m in row["input"]["messages"] if m["kind"] == "record"]
            self.assertEqual(actual, expected)

    def test_reduced_call_histories_exclude_removed_records_and_actions(self):
        projector = EvidenceProjector(evidence())
        report = projector.project(projector.delete_unit_and_dependents("toy-unit-content-a"))
        check = next(row for row in report["call_inputs"] if row["call_id"] == "toy-call-check")
        sources = [m["source_id"] for m in check["input"]["messages"] if m["kind"] == "record"]
        self.assertNotIn("toy-source-a1", sources)
        self.assertNotIn("toy-source-a2", sources)
        actions = [m["arguments"] for m in check["input"]["messages"] if m["kind"] == "call"]
        self.assertNotIn({"handle": "toy-alpha"}, actions)
        self.assertNotIn({"handle": "toy-alpha-detail"}, actions)

    def test_model_payload_excludes_internal_annotations(self):
        report = EvidenceProjector(evidence()).project()
        payloads = [report["record_view"]] + [row["input"] for row in report["call_inputs"]]
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        excluded = {"unit_id", "call_id", "record_id", "event_index", "provenance_complete",
                    "requires_records", "independently_useful", "synthetic", "support_status", "label"}
        for payload in payloads:
            self.assertFalse(keys(payload) & excluded)

    def test_returned_payloads_and_caller_input_do_not_mutate_the_frozen_prefix(self):
        document = evidence()
        projector = EvidenceProjector(document)
        original = projector.project()
        document["records"][0]["text"] = "changed caller data"
        document["calls"][0]["arguments"]["query"] = "changed caller action"
        changed_output = projector.project()
        changed_output["record_view"]["records"][0]["text"] = "changed output"
        changed_output["call_inputs"][-1]["input"]["messages"][1]["arguments"]["query"] = "changed output action"
        self.assertEqual(projector.project(), original)

    def test_false_provenance_blocks_retained_calls(self):
        document = evidence()
        document["calls"][1]["provenance_complete"] = False
        projector = EvidenceProjector(document)
        with self.assertRaisesRegex(ValueError, "Unresolved argument provenance"):
            projector.project()
        result = projector.project(projector.delete_unit_and_dependents("toy-unit-content-a"))
        self.assertNotIn("toy-record-a1", result["retained_record_ids"])

    def test_a_call_with_multiple_returns_is_not_split(self):
        document = evidence()
        extra = copy.deepcopy(document["records"][1])
        extra["record_id"] = "toy-record-second-return"
        extra["source_id"] = "toy-source-second-return"
        extra["text"] = "Artificial additional return from the same call."
        document["records"].insert(2, extra)
        projector = EvidenceProjector(document)
        full = projector.project()
        self.assertIn(extra["record_id"], full["retained_record_ids"])
        empty = projector.project(projector.delete_unit_and_dependents("toy-unit-locate"))
        self.assertNotIn(extra["record_id"], empty["retained_record_ids"])

    def test_shared_locator_cannot_be_merged_into_one_child(self):
        document = evidence()
        document["units"][0]["call_ids"] = ["toy-call-locate", "toy-call-a1"]
        document["units"][0]["terminal_record_id"] = "toy-record-a1"
        document["units"][1]["call_ids"] = ["toy-call-a2"]
        with self.assertRaisesRegex(ValueError, "shared or branching"):
            EvidenceProjector(document)

    def test_independently_useful_intermediate_cannot_be_hidden_in_chain(self):
        document = evidence()
        document["records"][2]["independently_useful"] = True
        with self.assertRaisesRegex(ValueError, "independently useful"):
            EvidenceProjector(document)

    def test_disconnected_chain_is_rejected(self):
        document = evidence()
        document["calls"][2]["requires_records"] = []
        with self.assertRaisesRegex(ValueError, "connected serial"):
            EvidenceProjector(document)

    def test_unknown_and_late_prerequisites_are_rejected(self):
        for required in ("missing-record", "toy-record-check"):
            document = evidence()
            document["calls"][1]["requires_records"] = [required]
            with self.subTest(required=required):
                with self.assertRaisesRegex(ValueError, "Required records"):
                    EvidenceProjector(document)

    def test_out_of_prefix_evidence_is_rejected(self):
        document = evidence()
        document["prefix_event"] = 8
        with self.assertRaises(ValueError):
            EvidenceProjector(document)

    def test_async_return_is_outside_the_released_scope(self):
        document = evidence()
        document["records"][2]["event_index"] = 12
        document["records"].sort(key=lambda record: record["event_index"])
        document["prefix_event"] = 12
        with self.assertRaisesRegex(ValueError, "Asynchronous"):
            EvidenceProjector(document)

    def test_units_partition_calls_without_overlap_or_omission(self):
        for change in ("overlap", "omission"):
            document = evidence()
            if change == "overlap":
                document["units"][1]["call_ids"].insert(0, "toy-call-locate")
            else:
                document["units"].pop()
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    EvidenceProjector(document)

    def test_unknown_metadata_and_deliberation_fields_are_rejected(self):
        for field in ("labels", "deliberations", "private_training_setting"):
            document = evidence()
            document[field] = []
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "Unexpected fields"):
                    EvidenceProjector(document)

    def test_malformed_protocol_values_are_rejected(self):
        for field, value in (("format_version", True), ("synthetic", "true"), ("prefix_event", False)):
            document = evidence()
            document[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    EvidenceProjector(document)
        document = evidence()
        document["calls"][0]["tool"] = []
        with self.assertRaises(ValueError):
            EvidenceProjector(document)

    def test_invalid_selections_fail_explicitly(self):
        projector = EvidenceProjector(evidence())
        for selection in ("toy-unit-locate", 1, ["missing-unit"], ["toy-unit-locate", "toy-unit-locate"]):
            with self.subTest(selection=selection):
                with self.assertRaises(ValueError):
                    projector.project(selection)
        with self.assertRaises(ValueError):
            projector.delete_unit_and_dependents("missing-unit")

    def test_core_demo_explains_four_expected_cases(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["core-demo"]), 0)
        report = json.loads(output.getvalue())
        verify(report, "core-design-demo")
        cases = {case["case"]: case for case in report["cases"]}
        self.assertEqual(list(cases), ["full_prefix", "remove_content_chain",
                                      "remove_shared_locator", "missing_predecessor"])
        for case in cases.values():
            self.assertTrue(case["explanation"])
            self.assertEqual(case["observed"], case["expected"])
            self.assertIs(case["matches_expected"], True)
        for name, key in (("full_prefix", "full"), ("remove_content_chain", "reduced"),
                          ("remove_shared_locator", "shared_locator_removed")):
            view = report[key]
            verify(view, "evidence-projection")
            observed = cases[name]["observed"]
            self.assertEqual(observed, {field: view[field] for field in observed})
        self.assertEqual(report["shared_locator_removed"]["call_inputs"], [])
        self.assertTrue(cases["missing_predecessor"]["observed"]["rejected"])
        self.assertIn("Missing dependencies", cases["missing_predecessor"]["observed"]["error"])

    def test_documented_walkthrough_matches_generated_summary(self):
        document = (Path(__file__).resolve().parents[1] / "docs/core-walkthrough.md").read_text(encoding="utf-8")
        excerpt = json.loads(document.split("```json\n", 1)[1].split("```", 1)[0])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["core-demo"]), 0)
        report = json.loads(output.getvalue())
        compact = {"synthetic": report["synthetic"],
                   "cases": [{field: case[field] for field in ("case", "matches_expected")}
                             for case in report["cases"]]}
        self.assertEqual(excerpt, compact)

    def test_core_demo_and_project_cli(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["core-demo"]), 0)
        demo = json.loads(output.getvalue())
        self.assertTrue(demo["synthetic"])
        self.assertNotIn("toy-record-a1", demo["reduced"]["retained_record_ids"])
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "prefix.json"
            target = Path(folder) / "projection.json"
            source.write_text(json.dumps(evidence()), encoding="utf-8")
            self.assertEqual(main(["project", "--input", str(source), "--drop-unit", "toy-unit-content-a",
                                   "--output", str(target)]), 0)
            self.assertTrue(target.exists())
            invalid = Path(folder) / "invalid.json"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["project", "--input", str(source), "--retain", "toy-unit-content-a",
                                       "--output", str(invalid)]), 2)
            self.assertFalse(invalid.exists())


if __name__ == "__main__":
    unittest.main()
