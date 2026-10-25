# Offline answer scoring

`evidence-preview score` converts supplied answers into the scored-record format.
It performs normalized exact match locally. It does not call a model, use an
answer-extraction prompt, judge semantic equivalence, or certify official
benchmark scores.

The paper's external Web-QA evaluation uses a separate judging and
answer-extraction procedure. The scorer in this preview is an offline example
utility; its output must not be substituted for those formal grades or for a
dataset-specific official scorer. Final externally obtained scores can be
passed to the scored-record interface for validation and statistical analysis.

## Input

The bundled `src/evidence_preview/examples/synthetic_answers.json` is an
artificial illustration with generic shapes and colors, not research data.

An answer document contains the population fields from the scored-record
interface: `format_version`, `synthetic`, `question_ids`, `methods`,
`run_pair_ids`, and `clusters`. It also contains:

- `grading_protocol`: exactly `normalized_exact_match_v1`.
- `accepted_answers`: an object mapping every declared question identifier to
  a nonempty list of accepted answer strings.
- `rows`: exactly one row per declared question, system, and paired run. Each
  row has `question_id`, `method`, `run_pair_id`, and `answer`.

`answer` is either a string or `null`. A missing answer row is rejected. A null
answer is unresolved. An empty string is a supplied answer and scores zero
against the required nonempty aliases. Reference aliases that become empty
after normalization are rejected.

## Normalization convention

1. Normalize Unicode with NFKC.
2. Apply Unicode case folding.
3. Remove characters whose Unicode category begins with `P` (punctuation).
4. Collapse consecutive whitespace and trim leading/trailing whitespace.
5. Match exactly against at least one identically normalized accepted alias.

Articles are not removed; accents and non-punctuation symbols are retained.
Punctuation is removed rather than replaced with spaces. For example, `A-B`
normalizes to `ab`, whereas `A B` normalizes to `a b`. The convention must match
the task being evaluated; it is not a universal answer correctness rule.

## Output and scope

The output is a normal scored-record document, with a grading identifier.
Raw answer strings and reference aliases are not copied into that document.
It can be passed directly to `validate` and `summarize`.

Score files still carry identifiers and numerical scores supplied or derived
from the caller's input. Omitting answer text does not anonymize an arbitrary
real dataset. Generated files belong in the ignored `outputs/` directory;
they are not bundled research artifacts.

This local normalization routine is adapted from the project's general grader.
The surrounding input/output interface and synthetic fixture were added for
this preview. This does not imply that the preview reproduces any paper table
or replaces task-specific official evaluation.
