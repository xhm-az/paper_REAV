"""Descriptive scores and paired question-cluster bootstrap intervals.

The interval conditions on the supplied trained run pairs. Training runs are
averaged before cluster resampling; they are not independent question replicas.
"""
from __future__ import annotations

import math

import numpy as np

from .artifacts import identity, seal
from .records import validate_records


def score_summaries(document):
    """Keep unresolved scores in the declared denominator and expose bounds."""
    validation = validate_records(document)
    per_run = []
    for run in sorted(document["run_pair_ids"]):
        for method in sorted(document["methods"]):
            rows = [r for r in document["rows"]
                    if r["run_pair_id"] == run and r["method"] == method]
            known = [float(r["score"]) for r in rows if r["score"] is not None]
            missing = len(rows) - len(known)
            total = math.fsum(known)
            per_run.append({
                "run_pair_id": run, "method": method, "question_count": len(rows),
                "resolved_count": len(known), "unresolved_count": missing,
                "mean_score": total / len(rows) if not missing else None,
                "score_lower": total / len(rows),
                "score_upper": (total + missing) / len(rows),
            })
    macro = []
    for method in sorted(document["methods"]):
        runs = [r for r in per_run if r["method"] == method]
        unresolved = sum(r["unresolved_count"] for r in runs)
        macro.append({
            "method": method, "run_pair_count": len(runs),
            "unresolved_count": unresolved,
            "mean_score": (math.fsum(r["mean_score"] for r in runs) / len(runs)
                           if not unresolved else None),
            "score_lower": math.fsum(r["score_lower"] for r in runs) / len(runs),
            "score_upper": math.fsum(r["score_upper"] for r in runs) / len(runs),
        })
    return seal("score-summary", {
        "input_id": validation["input_id"], "synthetic": document["synthetic"],
        "validation": validation, "per_run": per_run, "macro": macro,
        "interpretation": "Scores are supplied by the caller, not generated or graded here. "
                          "Bounds keep null scores in the denominator using the declared [0, 1] scale; "
                          "they are not confidence intervals.",
    })


def paired_comparison(document, *, treatment, control, resamples, seed):
    """Paired difference and percentile interval using shared cluster draws.

    Unequal clusters retain their question counts. Each draw resamples clusters
    with replacement and takes the mean over all questions in those clusters.
    """
    validation = validate_records(document)
    if (treatment == control or treatment not in document["methods"]
            or control not in document["methods"]):
        raise ValueError("Choose two distinct declared methods")
    if type(resamples) is not int or resamples <= 0:
        raise ValueError("A positive bootstrap resample count is required")
    if type(seed) is not int or seed < 0:
        raise ValueError("Declare a nonnegative bootstrap seed")
    if len(document["clusters"]) < 2:
        raise ValueError("At least two declared clusters are needed for a bootstrap interval")
    questions = sorted(document["question_ids"])
    runs = sorted(document["run_pair_ids"])
    scores = {(r["run_pair_id"], r["method"], r["question_id"]): r["score"]
              for r in document["rows"]}
    if any(scores[(run, method, question)] is None
           for run in runs for method in (treatment, control) for question in questions):
        raise ValueError("Resolve all scores for the paired contrast; unresolved records cannot be dropped")
    differences = np.asarray([
        [scores[(run, treatment, q)] - scores[(run, control, q)] for q in questions]
        for run in runs], dtype=np.float64)
    averaged_questions = differences.mean(axis=0)
    index = {q: i for i, q in enumerate(questions)}
    groups = [[index[q] for q in group] for group in document["clusters"]]
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(resamples):
        chosen = rng.integers(0, len(groups), len(groups))
        indices = [i for group in chosen for i in groups[group]]
        samples.append(float(averaged_questions[indices].mean()))
    effects = differences.mean(axis=1)
    return seal("paired-comparison", {
        "input_id": validation["input_id"], "synthetic": document["synthetic"],
        "treatment": treatment, "control": control,
        "question_count": len(questions), "source_cluster_count": len(groups),
        "largest_cluster": max(map(len, groups)), "trained_run_pairs": len(runs),
        "estimate": float(effects.mean()),
        "question_cluster_ci95": [float(x) for x in np.quantile(samples, [.025, .975])],
        "run_pair_effects": [{"run_pair_id": run, "effect": float(effect)}
                             for run, effect in zip(runs, effects)],
        "run_effect_std": float(effects.std(ddof=1)) if len(runs) >= 2 else None,
        "run_effect_range": [float(effects.min()), float(effects.max())],
        "resamples": resamples, "bootstrap_seed": seed,
        "interpretation": "95% percentile question/source-cluster bootstrap interval conditional on "
                          "the supplied trained checkpoints. Not a training-population interval; "
                          "run-times-question cells are not independent replicates. "
                          "Cluster definitions and grading are supplied by the caller.",
    })


def holm(p_values, registered_comparisons):
    """Adjust exactly the declared family; do not add or remove comparisons."""
    if (not isinstance(p_values, dict) or not isinstance(registered_comparisons, list)
            or not registered_comparisons
            or not all(isinstance(name, str) and name for name in registered_comparisons)
            or len(set(registered_comparisons)) != len(registered_comparisons)
            or set(p_values) != set(registered_comparisons)):
        raise ValueError("Supply exactly the declared comparison family")
    if not all(type(p) in (int, float) and 0 <= p <= 1 and math.isfinite(p)
               for p in p_values.values()):
        raise ValueError("P values must be finite numbers in [0, 1]")
    ordered = sorted(p_values, key=lambda name: (p_values[name], name))
    maximum = 0.0
    result = {}
    for index, name in enumerate(ordered):
        maximum = max(maximum, min(1.0, (len(ordered) - index) * p_values[name]))
        result[name] = {"raw_p": p_values[name], "holm_p": maximum}
    return result


def summarize(document, *, treatment=None, control=None, resamples=None, seed=None):
    descriptive = score_summaries(document)
    options = (treatment, control, resamples, seed)
    if any(option is not None for option in options) and not all(option is not None for option in options):
        raise ValueError("A paired contrast requires treatment, control, resamples, and seed together")
    comparison = None
    if treatment is not None:
        comparison = paired_comparison(document, treatment=treatment, control=control,
                                       resamples=resamples, seed=seed)
    return seal("evaluation-report", {
        "input_id": identity(document), "synthetic": document["synthetic"],
        "descriptive": descriptive, "paired_comparison": comparison,
    })
