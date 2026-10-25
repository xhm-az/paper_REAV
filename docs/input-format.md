# Scored-record input format

This is a standalone evaluation interface, not a training-data format. The
bundled example is synthetic. To process your own records, supply a JSON object
with these required fields (no other fields except the optional grading
identifier described below):

| Field | Meaning |
| --- | --- |
| `format_version` | Integer `1`. |
| `synthetic` | Boolean declaring whether the supplied records are artificial. |
| `question_ids` | Nonempty, distinct, predeclared question identifiers. |
| `methods` | Nonempty, distinct system labels. |
| `run_pair_ids` | Nonempty, distinct paired-run identifiers. |
| `clusters` | Nonempty groups partitioning every declared question exactly once. |
| `rows` | Exactly one scored row for every question, method, and paired run. |

Each row contains exactly `question_id`, `method`, `run_pair_id`, and `score`.
The `score` command additionally writes `grading_protocol` with the fixed value
`normalized_exact_match_v1`; the identifier is preserved in validation reports.
Manually supplied scores omit this field. Adding this identifier to arbitrary
scores does not establish that they were graded correctly.
Identifiers must start with an ASCII letter or digit and contain only letters,
digits, underscores, hyphens, and periods; maximum length is 128 characters.
They are labels, not raw question text, source text, URLs, or paths.

Scores are finite numbers between `0` and `1`, inclusive. Booleans are not
scores. A JSON `null` preserves an unresolved score. Removing a row is a
structural error; resolving its score is a separate operation.

All declared run pairs must have the same question population and method set.
Declaring the population explicitly catches missing rows; it does not establish
whether the population was selected fairly. That remains part of the caller's
experimental protocol. Changing declarations to omit inconvenient observations
changes the population being summarized.

## Source clusters and repeated observations

Questions sharing an appropriate source or dependence unit should be grouped
according to the caller's declared analysis. If independent questions are the
analysis unit, each question may form its own cluster. The utility does not
infer independence. A bootstrap interval needs at least two clusters; even
then, very few clusters can give an unstable interval.

Unequal clusters retain their question counts. A bootstrap draw samples
clusters with replacement, then averages all questions in the sampled clusters.
The same sampled indices apply to all paired systems and trained runs. This is
a question-weighted statistic, not an equal-weight average of cluster means.
Its use presupposes an appropriate, declared cluster-sampling interpretation.

Within-question repetitions must be aggregated under a fixed scoring convention
before using this interface. `run_pair_id` identifies an independent paired
training or evaluation run according to that convention; it is not a way to
treat repeated answers as extra independent questions.

## Outputs

`validate` emits a fingerprinted structural report, including unresolved counts.
A valid document can still contain unresolved scores. Validation is not a claim
that answers, labels, sources, or experimental provenance are correct.

`summarize` emits descriptive scores. A mean is `null` if that system/run has
unresolved values. The lower and upper endpoints replace unresolved scores by
`0` and `1`, respectively, without excluding them from the denominator.

With all paired options supplied, the report also includes treatment-minus-
control differences and a percentile cluster-bootstrap interval conditional
on the supplied trained runs. Partial paired options are rejected.

CSV export contains descriptive per-run summaries only, with the `synthetic`
flag and `TBD` for unresolved means. It does not export the paired interval.
JSON reports and CSV files are created exclusively, never overwritten.
