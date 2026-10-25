# Released core component: dependency-safe evidence views

This release includes a selected part of the method's core implementation:
fixed acquisition-unit representation and projection of cached record-only
histories. It follows the paper's **Joint Support and History Projection**
section and the history-projection rules in **Record Verification and History
Projection**. The implementation is in
[evidence_views.py](../src/evidence_preview/evidence_views.py).

The component is adapted from the project's projection implementation, with a
standalone record-only interface for dependency and history operations.

## Included operations

| Operation | Included behavior |
| --- | --- |
| Unit representation | Keep preassigned calls together, including valid serial chains. |
| Structural grouping checks | Reject overlapping groups, disconnected chains, shared intermediate locators, and independently useful intermediate records hidden in a chain. |
| Dependency closure | Find prerequisite units from the supplied call-to-record dependencies. |
| Deletion | Remove a whole unit and recursively remove units lacking a required predecessor. |
| Projection | Preserve original raw records, source identifiers, arguments, and chronological order. |
| Per-call histories | Include only retained calls and records available before the target call. |
| Input boundary | Keep internal unit identifiers and provenance annotations outside the emitted model-input payloads. |

## Deliberately unreleased components

The release does not include the main acquisition-credit calculation, its
learned weighting and objective, relation-instance construction and learning,
support certification, label generation, automatic prefix/unit selection, or
the joint training and model-scoring pipeline. It contains no model parameters,
study hyperparameters, private configuration, or research data.

The caller supplies the already fixed prefix, unit assignments, and dependency
annotations. Structural validation does not certify their semantic truth.
For example, `provenance_complete: true` is a supplied annotation, not a result
of parsing or checking arbitrary tool arguments. Semantic unit-grouping rules
and support-family consistency must be established outside this component.

A projected view always has `support_status: "not_assessed"`. Retaining a view
does not imply sufficient evidence, a valid acquisition-training condition, or
a verified relation label. Those decisions are outside the released slice.

## Run the released component

```bash
evidence-preview core-demo
```

This runs the component on artificial records. The full prefix includes a
shared locator, one two-call content chain, another content unit, and a checking
unit. Removing the content chain keeps the other units and removes both calls
of that chain from subsequent histories. Removing the shared locator removes
all dependent units. No model, network, or training is invoked.

The [explained core example](core-walkthrough.md) shows the four cases and
expected outputs. The [paper-code-test mapping](paper-code-tests.md) links
each released operation to its implementation and named tests.

To project an explicitly selected view:

```bash
evidence-preview project --input src/evidence_preview/examples/synthetic_evidence.json --drop-unit toy-unit-content-a --output outputs/synthetic-projection.json
```

Alternatively, `--retain` lists exactly the units to keep. Missing dependencies
are rejected rather than silently added. For example, keeping only
`toy-unit-content-a` is invalid because its locator is missing.

## Input contract

The artificial example is
[synthetic_evidence.json](../src/evidence_preview/examples/synthetic_evidence.json).
Its input has exactly these fields:

| Field | Meaning |
| --- | --- |
| `format_version` | Integer `1`. |
| `synthetic` | Boolean describing the caller's input. All bundled examples use `true`. |
| `question` | The input question text. |
| `prefix_event` | A fixed positive event boundary; it is supplied, not discovered here. |
| `calls` | Chronological cached search/read calls with identifiers, event indices, arguments, required-record identifiers, and explicit provenance status. |
| `records` | Chronological raw returns with producing-call identifiers, source identifiers, text, events, and supplied independent-utility flags. |
| `units` | Fixed unit identifiers, ordered call memberships, and terminal record identifiers. |

Every supplied call belongs to one unit. A single call's multiple return
records are retained or removed together. Initial records have no producing
call and event zero. All calls and returns must lie within the fixed prefix.
Calls are synchronous; asynchronous returns, stateful navigation, free
deliberations, and cached model hidden states are outside this interface.

The JSON report separates bookkeeping from `record_view` and the `input`
inside each `call_inputs` entry. These payloads contain the question and raw
visible records/actions without internal annotations. Model-specific prompt
serialization, target-token scoring, hidden-state recomputation, and policy
updates are not implemented in this release.

## Checks reviewers can inspect

The tests verify whole-chain deletion, shared-locator dependencies, preservation
of all returns from one call, no future or removed records in per-call inputs,
rejection of unresolved provenance, annotation separation, and independent
copies of emitted payloads. They use artificial records only and are not
measurements of research performance.

The complete method implementation will be released upon paper acceptance,
under the code-release scope stated in the [README](../README.md).
