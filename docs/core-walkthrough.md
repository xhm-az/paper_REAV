# Explained core example: dependent evidence projection

This example exercises the released projection code using the bundled
[artificial records](../src/evidence_preview/examples/synthetic_evidence.json).
The question, source handles, content, and dependency annotations were written
for this preview. The example checks software behavior and reports no research
performance, learned credit, or training outcome.

## 1. Read the input structure

The fixed prefix contains one initial context record and four acquisition units:

| Unit | Calls and returned records | Required predecessor |
| --- | --- | --- |
| `toy-unit-locate` | `toy-call-locate` returns `toy-record-locate`. | None. |
| `toy-unit-content-a` | `toy-call-a1` returns `toy-record-a1`; `toy-call-a2` returns `toy-record-a2`. | Locator record; the second call also requires the first call's record. |
| `toy-unit-content-b` | `toy-call-b` returns `toy-record-b`. | Locator record. |
| `toy-unit-check` | `toy-call-check` returns `toy-record-check`. | Locator record. |

```text
toy-unit-locate
    +--> toy-unit-content-a: toy-call-a1 --> toy-call-a2
    +--> toy-unit-content-b: toy-call-b
    +--> toy-unit-check:     toy-call-check
```

The initial context is outside the acquisition units. Content A is a supplied
two-call serial unit; its intermediate record is marked as a locator without
independent utility. The shared locator remains a separate unit. The code
checks these supplied structural annotations; it does not infer their semantic
truth. No evidence-support label is assigned in this walkthrough.

## 2. Run all four cases

From the repository root, after installation:

```bash
evidence-preview core-demo --output outputs/core-walkthrough.json
```

Use a fresh filename on repeat runs. The report contains `cases`, where each
case has an explanation, `expected` and `observed` summaries, and
`matches_expected`. It also includes the full projected payloads as `full`,
`reduced`, and `shared_locator_removed`. All four comparisons must match;
the command exits with an error if the artificial example behaves differently.

### Case A: full prefix

All four units and all six records remain, in original order. Each retained
call sees only records available before that call. For example, the full
`toy-call-a2` input can contain `toy-record-a1` but not its own return
`toy-record-a2` or the later records from B and the checking call.

### Case B: remove the content A chain

`delete_unit_and_dependents("toy-unit-content-a")` removes both calls of A
and both of their returns. The locator, B, and the checking unit remain.
The later checking call's history contains no A calls or A records. Raw retained
text and source identifiers stay unchanged; removing a unit does not rewrite
the remaining text.

### Case C: remove the shared locator

`delete_unit_and_dependents("toy-unit-locate")` also removes A, B, and the
checking unit because their supplied prerequisites are no longer available.
The resulting view contains only `toy-record-initial` and no retained calls.
Its `support_status` remains `not_assessed`; this output is not a certified
insufficient-evidence training example.

### Case D: request a view with a missing prerequisite

`project(["toy-unit-content-a"])` requests A without its locator. The code
rejects this exact selection rather than silently inserting a source or
pretending that A's inputs are available. The demo catches this expected
`ValueError` and records its message. `core-demo` succeeds because rejection
is the expected behavior; the same invalid `project` CLI request exits with
status 2 and creates no output file.

## 3. Compare the compact expected output

This is the expected compact summary of the four cases. Unit and record
suffixes below refer to the `toy-unit-` and `toy-record-` identifiers above.
The JSON report uses the complete identifiers.

| Case | Retained unit suffixes, in order | Retained record suffixes, in order | Outcome |
| --- | --- | --- | --- |
| `full_prefix` | locate, content-a, content-b, check | initial, locate, a1, a2, b, check | Valid projection; support not assessed. |
| `remove_content_chain` | locate, content-b, check | initial, locate, b, check | Valid projection; support not assessed. |
| `remove_shared_locator` | None | initial | Valid projection; support not assessed. |
| `missing_predecessor` | No view emitted | No view emitted | Request rejected. |

The following excerpt is checked against the generated report by a CPU test:

```json
{
  "synthetic": true,
  "cases": [
    {"case": "full_prefix", "matches_expected": true},
    {"case": "remove_content_chain", "matches_expected": true},
    {"case": "remove_shared_locator", "matches_expected": true},
    {"case": "missing_predecessor", "matches_expected": true}
  ]
}
```

Expected rejection message:

```text
Missing dependencies: a projection cannot silently add evidence
```

## 4. Inspect the implementation and tests

- [Paper-code-test mapping](paper-code-tests.md) identifies the relevant paper
  concepts, class methods, and tests by name.
- [Core-design scope](core-design.md) states the input assumptions and released
  operations.
- Run the focused checks from the repository root:

```bash
python -m unittest discover -s tests -p test_evidence_views.py -v
```

The walkthrough calls the existing released component. Acquisition credit,
relation supervision, semantic support certification, and policy training
remain outside the preview, under the [release policy](../README.md#full-code-release-upon-acceptance).
