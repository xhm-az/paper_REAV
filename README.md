# Partial Core Implementation Preview

This repository releases a selected part of our method's core implementation:
acquisition-unit representation and dependency-safe evidence-view projection.
It also includes local example scoring, record validation, paired statistical
comparisons, and report export. All bundled examples are synthetic.

The current preview excludes the remaining core mechanisms, full training
implementation, study hyperparameters and private configurations, model weights,
research datasets, and real experimental outputs. It supports inspection of the
included core component and evaluation utilities, not end-to-end reproduction
of the paper's experiments.

## Quickstart

Requires Python 3.10 or newer and NumPy. Use a virtual environment if preferred.
No model framework, GPU, API credential, or runtime service is needed.

Run these commands from the repository root:

```bash
python -m pip install .
evidence-preview core-demo
evidence-preview demo
python -m unittest discover -s tests -v
```

If the console command is unavailable, use `python -m evidence_preview demo`.
`core-demo` explains four projection cases with expected and observed outputs;
`demo` runs local scoring and paired analysis. Both print JSON and do not
create files unless output paths are provided.

Start with the [explained core example](docs/core-walkthrough.md), then use the
[paper-code-test mapping](docs/paper-code-tests.md) to locate each operation
and its checks.

**All bundled answers, reference aliases, scores, and demo outputs are
synthetic. They are examples of software behavior, not paper results.**

## Included implementation

| Component | Source | What can be inspected |
| --- | --- | --- |
| Released core: evidence projection | [evidence_views.py](src/evidence_preview/evidence_views.py) | Whole units, dependency closure, dependent deletion, chronological record views, annotation separation. |
| Local answer scoring | [scoring.py](src/evidence_preview/scoring.py) | Unicode normalization, accepted aliases, unresolved answers. |
| Record validation | [records.py](src/evidence_preview/records.py) | Complete question/system/run grids, duplicate and missing records. |
| Paired statistics | [statistics.py](src/evidence_preview/statistics.py) | Score bounds, shared cluster bootstrap, per-run differences, Holm correction. |
| JSON artifacts | [artifacts.py](src/evidence_preview/artifacts.py) | Content fingerprints, strict JSON parsing, exclusive file creation. |
| CSV export | [reporting.py](src/evidence_preview/reporting.py) | Descriptive scores with explicit unresolved values. |
| Command interface | [cli.py](src/evidence_preview/cli.py) | `core-demo`, `project`, `score`, `validate`, `summarize`, and `demo`. |
| CPU tests | [tests/](tests/) | Synthetic behavior checks and the full offline workflow. |

The released core component is adapted from the project's evidence-projection
implementation, with fixed units and dependency annotations supplied by the
caller. See [the core-design scope](docs/core-design.md) for included operations,
input assumptions, and the mechanisms that remain unreleased.

The normalization routine and paired statistical calculation are adapted from
the project's general local grader and statistics implementation. Internal
experiment-specific record classes and method identifiers have been replaced
with a standalone interface. The preview adds input validation and synthetic
fixtures around these utilities.

### Relationship to the paper

| Included utility | Role and boundary |
| --- | --- |
| Evidence-view projection | Implements a selected part of Joint Support and History Projection: fixed units, dependency checks, whole-unit deletion, and visible record histories. It does not assign semantic support labels or training eligibility. |
| Local exact-match example | Demonstrates offline alias matching. It does not implement the paper's external Web-QA judging and answer-extraction procedure or dataset-specific official scoring. |
| Scored-record interface | Accepts final scores supplied by the appropriate evaluation procedure; validates the declared question/system/run population. It does not establish that the supplied grades are correct. |
| Summaries and paired statistics | Analyze supplied final scores. The synthetic walkthrough does not reconstruct a reported paper table. |
| Remaining core mechanisms and full training | Scheduled for release upon acceptance; not included in this preview. |

## Released core component

```bash
evidence-preview project --input src/evidence_preview/examples/synthetic_evidence.json --drop-unit toy-unit-content-a --output outputs/synthetic-projection.json
```

This preserves the retained records and source identifiers and removes both
calls of the selected serial chain from later histories. Only preassigned
units and supplied dependency annotations are used. The component does not
discover certified supports, calculate acquisition credit, construct relation
supervision, or update a policy. See [core-design.md](docs/core-design.md).

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
- [Explained core example](docs/core-walkthrough.md): dependencies, four cases, and expected outputs.
- [Paper-code-test mapping](docs/paper-code-tests.md): paper concepts, exact methods, and named tests.
- [Released core design](docs/core-design.md): evidence units, dependencies, projection, and release boundary.
- [Answer-scoring contract](docs/answer-scoring.md): exact normalization and alias rules.
- [Scored-record format](docs/input-format.md): declared populations and statistical interpretation.
- [Release file manifest](RELEASE-MANIFEST.json): hashes of the distributed files.

### Evaluation conventions

- The local scorer uses NFKC normalization, case folding, Unicode punctuation
  removal, and whitespace normalization followed by exact alias matching.
  Formal benchmark scores must come from the corresponding evaluation procedure.
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

**This preview releases only a selected part of the method's core implementation.**

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
