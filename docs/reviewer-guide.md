# Reviewer walkthrough: a complete synthetic offline workflow

This walkthrough runs software checks on artificial inputs. It supplies no
research results and does not reproduce the paper's training runs.

Reviewers may download, inspect, and run this preview for evaluating the
associated submission under [the review-use permission](../NOTICE.md).

Install the package as described in the README, then run these commands from
the repository root. Use fresh output filenames; outputs are never replaced.

## 1. Score synthetic answers

```bash
evidence-preview score --input src/evidence_preview/examples/synthetic_answers.json --output outputs/synthetic-scored.json
```

Inspect [scoring.py](../src/evidence_preview/scoring.py) to check Unicode normalization, alias matching, and the
distinction between an unresolved answer and a supplied incorrect answer.
The fixture is a deliberately artificial shape/color example with generic
system labels. No question text or website content is included.

## 2. Validate the full declared grid

```bash
evidence-preview validate --input outputs/synthetic-scored.json
```

Inspect [records.py](../src/evidence_preview/records.py) to check that every declared question, system, and paired
run appears exactly once. Removing a row fails validation. Setting a score to
`null` preserves it as unresolved.

## 3. Summarize and compare

```bash
evidence-preview summarize --input outputs/synthetic-scored.json --treatment system_a --control system_b --resamples 2000 --seed 0 --output outputs/synthetic-comparison.json --csv outputs/synthetic-scores.csv
```

The options here are illustrative bootstrap settings, not study parameters.
Inspect [statistics.py](../src/evidence_preview/statistics.py) to check shared cluster resampling, run averaging, and
the conditional interpretation of the interval. CSV export contains
descriptive scores; the paired interval is in the JSON report.

## 4. Inspect report consistency and tests

To check the content fingerprint in Python:

```python
from evidence_preview.artifacts import read_json, verify

report = read_json("outputs/synthetic-comparison.json")
verify(report, "evaluation-report")
assert report["synthetic"] is True
```

Run the CPU tests:

```bash
python -m unittest discover -s tests -v
```

The tests check normalization behavior, complete paired populations, unknown
scores, positive and negative synthetic differences, unequal cluster sizes,
non-overwriting outputs, and fingerprint tampering. They test software behavior;
they do not authenticate experiments or establish research performance.

## What can be inspected in this preview

| Component | Inspectable behavior |
| --- | --- |
| Local scorer | Exact answer normalization and treatment of missing answers. |
| Record validation | Population alignment and duplicate/missing-record handling. |
| Statistics | Paired difference, shared cluster draws, and stated uncertainty scope. |
| Export and artifacts | Explicit unresolved values, output schemas, and consistency checks. |

Core learning mechanisms, trained models, research data, study configurations,
and real results are outside this preview. The release policy is stated in the
[README](../README.md#full-code-release-upon-acceptance).
