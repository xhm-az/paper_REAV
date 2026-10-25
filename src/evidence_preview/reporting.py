"""CSV output for descriptive scores; unknown values remain explicit."""
from __future__ import annotations

import csv
import io

from .artifacts import verify


def descriptive_csv(report):
    verify(report, "evaluation-report")
    descriptive = verify(report["descriptive"], "score-summary")
    fields = ["synthetic", "run_pair_id", "method", "question_count",
              "resolved_count", "unresolved_count", "mean_score", "score_lower", "score_upper"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in descriptive["per_run"]:
        writer.writerow({"synthetic": report["synthetic"],
                         **{key: "TBD" if value is None else value for key, value in row.items()}})
    return stream.getvalue()
