# Partial Code Preview

This repository provides the offline evaluation portion of our research code:
answer scoring, record validation, paired statistical comparisons, and report
export. It includes a complete runnable workflow with synthetic examples.

The current preview excludes the core training implementation, study
hyperparameters and private configurations, model weights, research datasets,
and real experimental outputs. It supports inspection of the included
evaluation utilities, not end-to-end reproduction of the paper's experiments.

## Quickstart

Requires Python 3.10 or newer and NumPy. Use a virtual environment if preferred.
No model framework, GPU, API credential, or runtime service is needed.

Run these commands from the repository root:

```bash
python -m pip install .
evidence-preview demo
python -m unittest discover -s tests -v
```

If the console command is unavailable, use `python -m evidence_preview demo`.
The demo performs local scoring and paired analysis in memory; it prints a JSON
report. It does not create files unless output paths are provided.

**All bundled answers, reference aliases, scores, and demo outputs are
synthetic. They are examples of software behavior, not paper results.**

## Included implementation

| Component | Source | What can be inspected |
| --- | --- | --- |
| Local answer scoring | [scoring.py](src/evidence_preview/scoring.py) | Unicode normalization, accepted aliases, unresolved answers. |
| Record validation | [records.py](src/evidence_preview/records.py) | Complete question/system/run grids, duplicate and missing records. |
| Paired statistics | [statistics.py](src/evidence_preview/statistics.py) | Score bounds, shared cluster bootstrap, per-run differences, Holm correction. |
| JSON artifacts | [artifacts.py](src/evidence_preview/artifacts.py) | Content fingerprints, strict JSON parsing, exclusive file creation. |
| CSV export | [reporting.py](src/evidence_preview/reporting.py) | Descriptive scores with explicit unresolved values. |
| Command interface | [cli.py](src/evidence_preview/cli.py) | `score`, `validate`, `summarize`, and `demo`. |
| CPU tests | [tests/](tests/) | Synthetic behavior checks and the full offline workflow. |

The normalization routine and paired statistical calculation are adapted from
the project's general local grader and statistics implementation. Internal
experiment-specific record classes and method identifiers have been replaced
with a standalone interface. The preview adds input validation and synthetic
fixtures around these utilities.

## Offline evaluation workflow

```text
supplied answers + accepted aliases -> local scoring -> record validation
                                   -> paired analysis -> JSON / CSV
```

The following commands use only the bundled synthetic answers:

```bash
evidence-preview score --input src/evidence_preview/examples/synthetic_answers.json --output outputs/synthetic-scored.json
evidence-preview validate --input outputs/synthetic-scored.json
evidence-preview summarize --input outputs/synthetic-scored.json --treatment system_a --control system_b --resamples 2000 --seed 0 --output outputs/synthetic-comparison.json --csv outputs/synthetic-scores.csv
```

The bootstrap options shown here are illustrative analysis settings, not study
or training parameters. Outputs are never overwritten; choose new filenames
when repeating the commands. Generated files belong in the ignored `outputs/`
directory.

For detailed inspection, see:

- [Reviewer walkthrough](docs/reviewer-guide.md): commands and source-reading guide.
- [Answer-scoring contract](docs/answer-scoring.md): exact normalization and alias rules.
- [Scored-record format](docs/input-format.md): declared populations and statistical interpretation.
- [Release file manifest](RELEASE-MANIFEST.json): hashes of the distributed files.

### Evaluation conventions

- The local scorer uses NFKC normalization, case folding, Unicode punctuation
  removal, and whitespace normalization followed by exact alias matching. It
  is not a semantic judge or an official benchmark grader.
- Already-scored inputs can be processed directly with `validate` and
  `summarize`; scoring conventions and source clusters come from the caller.
- A `null` score is unresolved. Summaries retain its denominator and report
  bounds; those bounds are not confidence intervals. Paired analysis requires
  resolved scores for both selected systems on every declared question and run.
- Bootstrap draws are shared across paired systems and runs. The interval
  conditions on the supplied trained checkpoints and does not estimate
  variability over future training runs.
- Fingerprints detect content changes relative to a reference. They are not
  signatures or independent evidence that experiments ran.

## Full code release upon acceptance

**Upon acceptance of the paper, we will publicly release the complete source
code of the proposed method, including the core training implementation,
evaluation code, and supporting scripts.**

This commitment covers implementation code. Experimental hyperparameter values
and private configuration files, model weights, datasets, and raw experimental
outputs are excluded from the code-release commitment.

## Review access and licensing

Reviewers may download, inspect, and run the included files to evaluate the
associated submission under [the limited review-use permission](NOTICE.md).
The current preview is not released under a general open-source license.
Third-party dependencies retain their own licenses. The complete implementation
and its release licensing will be provided after paper acceptance.
