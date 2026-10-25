# Reviewer walkthrough: partial core implementation and evaluation utilities

This walkthrough runs software checks on artificial inputs. It supplies no
research results and does not reproduce the paper's training runs.

Reviewers may download, inspect, and run this preview for evaluating the
associated submission under [the review-use permission](../NOTICE.md).

Install the package as described in the README, then run these commands from
the repository root. Use fresh output filenames; outputs are never replaced.

## 1. Inspect the released core projection component

```bash
evidence-preview core-demo
```

Follow the [explained core example](core-walkthrough.md) for the dependency
structure, retained/removed records, and expected rejection. The output's
four `cases` compare expected and observed behavior. The
[paper-code-test mapping](paper-code-tests.md) names the method and test for
each released operation.

Inspect [evidence_views.py](../src/evidence_preview/evidence_views.py) alongside
the paper's Joint Support and History Projection section. The released slice
represents fixed acquisition units, checks structural dependencies, removes a
whole unit and its dependents, and reconstructs raw record-only histories.
Read [core-design.md](core-design.md) for its assumptions and public boundary.

It does not compute acquisition credit, construct relation supervision, assign
semantic labels, score a policy, or run training. All records in this example
were written as artificial inputs for the preview.

## 2. Score synthetic answers

```bash
evidence-preview score --input src/evidence_preview/examples/synthetic_answers.json --output outputs/synthetic-scored.json
```

Inspect [scoring.py](../src/evidence_preview/scoring.py) to check Unicode normalization, alias matching, and the
distinction between an unresolved answer and a supplied incorrect answer.
The fixture is a deliberately artificial shape/color example with generic
system labels. No question text or website content is included. This local
example scorer is separate from the paper's formal external Web-QA judging
and answer-extraction procedure; inspect it as an offline utility.

## 3. Validate the full declared grid

```bash
evidence-preview validate --input outputs/synthetic-scored.json
```

Inspect [records.py](../src/evidence_preview/records.py) to check that every declared question, system, and paired
run appears exactly once. Removing a row fails validation. Setting a score to
`null` preserves it as unresolved.

## 4. Summarize and compare

```bash
evidence-preview summarize --input outputs/synthetic-scored.json --treatment system_a --control system_b --resamples 2000 --seed 0 --output outputs/synthetic-comparison.json --csv outputs/synthetic-scores.csv
```

The options here are illustrative bootstrap settings, not study parameters.
Inspect [statistics.py](../src/evidence_preview/statistics.py) to check shared cluster resampling, run averaging, and
the conditional interpretation of the interval. CSV export contains
descriptive scores; the paired interval is in the JSON report.

## 5. Inspect report consistency and tests

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
| Released core projection | Whole-unit retention, dependency legality, source-preserving histories, and annotation separation. |
| Local scorer | Exact answer normalization and treatment of missing answers. |
| Record validation | Population alignment and duplicate/missing-record handling. |
| Statistics | Paired difference, shared cluster draws, and stated uncertainty scope. |
| Export and artifacts | Explicit unresolved values, output schemas, and consistency checks. |

The main learning mechanisms, trained models, research data, study configurations,
and real results are outside this preview. The release policy is stated in the
[README](../README.md#full-code-release-upon-acceptance).
