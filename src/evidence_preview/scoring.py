"""Offline normalized exact match, adapted from the project's local grader.

No semantic judge, benchmark-specific answer extraction, or model calls are
provided. Accepted answer aliases must be supplied by the caller.
"""
from __future__ import annotations

import re
import unicodedata

from .records import validate_records

GRADING_PROTOCOL = "normalized_exact_match_v1"
_FIELDS = {"format_version", "synthetic", "question_ids", "methods", "run_pair_ids",
           "clusters", "grading_protocol", "accepted_answers", "rows"}


def normalize_answer(answer):
    """NFKC, casefold, remove Unicode punctuation, then collapse whitespace.

    Punctuation is removed, not replaced with spaces. Articles, accents,
    symbols, and word order are not otherwise changed.
    """
    if not isinstance(answer, str):
        raise ValueError("An answer must be a string")
    answer = unicodedata.normalize("NFKC", answer).casefold()
    answer = "".join(c for c in answer if not unicodedata.category(c).startswith("P"))
    return re.sub(r"\s+", " ", answer).strip()


def score_answers(document):
    """Return scored records without copying raw answers or reference text."""
    if not isinstance(document, dict) or set(document) != _FIELDS:
        raise ValueError("Unexpected answer document fields; see docs/answer-scoring.md")
    if document["grading_protocol"] != GRADING_PROTOCOL:
        raise ValueError("The local scorer requires an explicit normalized_exact_match_v1 protocol")
    if not isinstance(document["rows"], list) or not document["rows"]:
        raise ValueError("Answer rows must be a nonempty list")
    # Validate identifiers, declared populations, and complete paired grids
    # before accessing references or assigning any score.
    rows = []
    for row in document["rows"]:
        if (not isinstance(row, dict)
                or set(row) != {"question_id", "method", "run_pair_id", "answer"}):
            raise ValueError("Each answer row must contain only identifiers and answer")
        if row["answer"] is not None and not isinstance(row["answer"], str):
            raise ValueError("An answer must be a string or null")
        rows.append({key: row[key] for key in ("question_id", "method", "run_pair_id")})
        rows[-1]["score"] = None
    scored = {field: document[field] for field in
              ("format_version", "synthetic", "question_ids", "methods", "run_pair_ids", "clusters")}
    scored = {**scored, "grading_protocol": GRADING_PROTOCOL, "rows": rows}
    validate_records(scored)
    references = document["accepted_answers"]
    if not isinstance(references, dict) or set(references) != set(document["question_ids"]):
        raise ValueError("Accepted answers must cover exactly the declared questions")
    normalized = {}
    for question, aliases in references.items():
        if (not isinstance(aliases, list) or not aliases
                or not all(isinstance(alias, str) and alias.strip() for alias in aliases)):
            raise ValueError("Each question needs a nonempty list of answer aliases")
        values = {normalize_answer(alias) for alias in aliases}
        if "" in values:
            raise ValueError("An answer alias becomes empty after normalization")
        normalized[question] = values
    for source, target in zip(document["rows"], scored["rows"]):
        answer = source["answer"]
        target["score"] = (None if answer is None else
                           float(normalize_answer(answer) in normalized[source["question_id"]]))
    validate_records(scored)
    return scored
