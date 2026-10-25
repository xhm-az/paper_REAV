# Paper-code-test correspondence

This table maps the released evidence-projection slice to the paper's
**Joint Support and History Projection** subsection and the appendix's
**Record Verification and History Projection** discussion. Subsection titles
are used so the mapping does not depend on final section numbering. The
preview implements structural operations on caller-supplied annotations.

All methods below belong to
[`EvidenceProjector`](../src/evidence_preview/evidence_views.py). All named
tests belong to
[`EvidenceViewChecks`](../tests/test_evidence_views.py).

| Paper concept within the released slice | Code method(s) | Test(s) to inspect | What the check establishes |
| --- | --- | --- | --- |
| Fixed acquisition units; whole serial chains | `_index_units`, `_validate_chains` | `test_units_partition_calls_without_overlap_or_omission`; `test_deleting_a_unit_removes_its_entire_serial_chain` | Supplied units partition the calls and chain deletion removes all member calls. |
| Shared locators stay separate; useful intermediate records remain separate | `_validate_chains` | `test_shared_locator_cannot_be_merged_into_one_child`; `test_independently_useful_intermediate_cannot_be_hidden_in_chain`; `test_disconnected_chain_is_rejected` | Invalid supplied grouping is rejected; semantic utility itself remains an external annotation. |
| Required predecessor units | `dependency_closure` | `test_dependency_closure_includes_shared_locator` | Closure includes the locator required by a selected child unit. |
| Dependency-respecting projected conditions | `project` | `test_missing_predecessors_are_rejected_not_added` | A requested selection missing a prerequisite is rejected without adding records. |
| Deleting units with unavailable dependencies | `delete_unit_and_dependents` | `test_deleting_the_shared_locator_removes_all_dependents` | Removing the shared locator removes its dependent acquisition units. |
| Original records, source identifiers, and order | `_available_records`, `_record_payload`, `project` | `test_full_projection_preserves_all_records_in_original_order`; `test_a_call_with_multiple_returns_is_not_split` | Visible returns are preserved in order; returns from one call are retained or removed together. |
| Histories use only retained information preceding the recorded call | `_validate_timing`, `_available_records`, `project` | `test_call_histories_have_no_future_records`; `test_reduced_call_histories_exclude_removed_records_and_actions` | Future records and removed actions/records do not enter a retained call's input. |
| Fixed-prefix boundary and available call arguments | `_validate_timing`, `project` | `test_out_of_prefix_evidence_is_rejected`; `test_unknown_and_late_prerequisites_are_rejected`; `test_false_provenance_blocks_retained_calls` | Out-of-prefix, unavailable, or explicitly unresolved inputs are rejected; true semantic provenance is not certified here. |
| Internal annotation separation | `_record_payload`, `project` | `test_model_payload_excludes_internal_annotations` | Internal grouping/provenance fields are absent from the emitted model-input payloads. |

## Reproduce the explained example

The [explained core example](core-walkthrough.md) connects these operations in
four cases. The CLI's `_core_demo` function orchestrates the released component
on artificial input; `test_core_demo_explains_four_expected_cases` checks its
report, and `test_documented_walkthrough_matches_generated_summary` checks the
documented JSON excerpt against actual output.

```bash
evidence-preview core-demo
python -m unittest discover -s tests -p test_evidence_views.py -v
```

## Scope of this correspondence

The table covers structural grouping checks and raw-record history construction.
The caller fixes the prefix, unit assignments, and dependency annotations.
Hidden-state recomputation, recorded-call probabilities, support-family discovery
and certification, acquisition-credit calculations, relation supervision, and
joint optimization remain outside the preview. A valid projected view always
reports `support_status: "not_assessed"`; it does not certify a training label.

Tests establish behavior of the distributed component on artificial inputs.
They do not reproduce paper performance or validate the full learning pipeline.
See the [README](../README.md#full-code-release-upon-acceptance) for the release
commitment.
