"""CPU-only offline answer scoring and evaluation; no model or service calls."""
from __future__ import annotations

import argparse
from importlib import resources
from pathlib import Path
import sys

from . import __version__
from .artifacts import encode_json, read_json, write_json
from .records import validate_records
from .reporting import descriptive_csv
from .scoring import score_answers
from .statistics import summarize


def _parser():
    parser = argparse.ArgumentParser(description="Partial evaluation code preview")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run a synthetic example, not a paper experiment")
    demo.add_argument("--output", type=Path, help="Write a new JSON report instead of stdout")
    demo.add_argument("--csv", type=Path, help="Write a new descriptive CSV (synthetic)")
    validate = commands.add_parser("validate", help="Check a declared scored-record grid")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output", type=Path)
    score = commands.add_parser("score", help="Locally score supplied answers against supplied aliases")
    score.add_argument("--input", type=Path, required=True)
    score.add_argument("--output", type=Path)
    summary = commands.add_parser("summarize", help="Summarize supplied scores; optionally compare two methods")
    summary.add_argument("--input", type=Path, required=True)
    summary.add_argument("--output", type=Path)
    summary.add_argument("--csv", type=Path, help="Write a new descriptive CSV")
    summary.add_argument("--treatment")
    summary.add_argument("--control")
    summary.add_argument("--resamples", type=int, help="Bootstrap draws; specify explicitly for paired statistics")
    summary.add_argument("--seed", type=int, help="Bootstrap RNG seed, not a model-training seed")
    return parser


def _emit(report, output, csv_path=None):
    paths = [path.resolve() for path in (output, csv_path) if path is not None]
    if len(set(paths)) != len(paths):
        raise ValueError("JSON and CSV outputs must be different files")
    if any(path.exists() for path in paths):
        raise ValueError("Output already exists; choose a new file")
    # Render both payloads before creating outputs, so invalid content cannot
    # leave a partially serialized report.
    json_payload = encode_json(report)
    csv_payload = descriptive_csv(report) if csv_path is not None else None
    if output is not None:
        write_json(output, report)
    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(csv_payload)
    if output is None:
        sys.stdout.write(json_payload)


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "demo":
            example = resources.files("evidence_preview").joinpath("examples/synthetic_answers.json")
            with resources.as_file(example) as path:
                document = score_answers(read_json(path))
            # These are illustrative bootstrap settings, not study settings.
            report = summarize(document, treatment="system_a", control="system_b",
                               resamples=512, seed=0)
        else:
            document = read_json(args.input)
            if args.command == "validate":
                report = validate_records(document)
            elif args.command == "score":
                report = score_answers(document)
            else:
                report = summarize(document, treatment=args.treatment, control=args.control,
                                   resamples=args.resamples, seed=args.seed)
        _emit(report, args.output, getattr(args, "csv", None))
    except (ValueError, OSError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 2
    return 0
