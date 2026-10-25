"""Validate an explicitly declared, complete grid of already scored records."""
from __future__ import annotations

import math
import re

from .artifacts import identity, seal

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_FIELDS = {"format_version", "synthetic", "question_ids", "methods",
           "run_pair_ids", "clusters", "rows"}


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _ids(values, name):
    _check(isinstance(values, list) and bool(values), name + " must be a nonempty list")
    _check(all(isinstance(v, str) and _ID.fullmatch(v) for v in values),
           name + " must contain portable, nonempty identifiers")
    _check(len(set(values)) == len(values), "Duplicate " + name)


def validate_records(document):
    _check(isinstance(document, dict) and _FIELDS <= set(document)
           and set(document) <= _FIELDS | {"grading_protocol"},
           "Unexpected record document fields; see docs/input-format.md")
    _check(type(document["format_version"]) is int and document["format_version"] == 1,
           "Unsupported record format version")
    _check(type(document["synthetic"]) is bool, "Declare whether the records are synthetic")
    if "grading_protocol" in document:
        _check(document["grading_protocol"] == "normalized_exact_match_v1",
               "Unsupported local grading protocol")
    for field in ("question_ids", "methods", "run_pair_ids"):
        _ids(document[field], field)
    clusters = document["clusters"]
    _check(isinstance(clusters, list) and bool(clusters), "Declare nonempty question clusters")
    for cluster in clusters:
        _ids(cluster, "cluster members")
    flat = [question for cluster in clusters for question in cluster]
    _check(len(set(flat)) == len(flat) and set(flat) == set(document["question_ids"]),
           "Clusters must partition all declared questions exactly once")
    rows = document["rows"]
    _check(isinstance(rows, list) and bool(rows), "Records must be a nonempty list")
    questions = set(document["question_ids"])
    methods = set(document["methods"])
    pairs = set(document["run_pair_ids"])
    seen = set()
    unknown = 0
    for index, row in enumerate(rows):
        _check(isinstance(row, dict)
               and set(row) == {"question_id", "method", "run_pair_id", "score"},
               "Unexpected fields in record " + str(index))
        for field, allowed in (("question_id", questions), ("method", methods),
                               ("run_pair_id", pairs)):
            _check(isinstance(row[field], str) and row[field] in allowed,
                   "Undeclared identifier in record " + str(index))
        key = (row["run_pair_id"], row["method"], row["question_id"])
        _check(key not in seen, "Duplicate run/method/question record")
        seen.add(key)
        score = row["score"]
        if score is None:
            unknown += 1
        else:
            _check(type(score) in (int, float) and 0 <= score <= 1
                   and math.isfinite(score), "Scores must be finite numbers in [0, 1] or null")
    expected_size = len(questions) * len(methods) * len(pairs)
    _check(len(seen) == expected_size,
           "Incomplete grid: require every declared run, method, and question; use null for unresolved scores")
    return seal("record-validation", {
        "input_id": identity(document), "synthetic": document["synthetic"],
        "grading_protocol": document.get("grading_protocol", "caller_supplied_scores"),
        "question_count": len(questions), "method_count": len(methods),
        "run_pair_count": len(pairs), "cluster_count": len(clusters),
        "record_count": len(rows), "unresolved_count": unknown,
        "all_scores_resolved": unknown == 0,
    })
