"""Selected core implementation: dependency-safe, record-only evidence views.

The caller supplies a fixed prefix, unit assignments, and argument-provenance
annotations. This component projects that prefix; it does not discover supports,
assign support labels, score a policy, or construct a training objective.
"""
from __future__ import annotations

import copy
import json

from .artifacts import identity, seal
from .records import _ids


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, expected, name):
    _require(isinstance(value, dict) and set(value) == set(expected),
             "Unexpected fields in " + name)


class EvidenceProjector:
    """Project preassigned units without changing record contents or arguments.

    Supported inputs are cached, synchronous search/read records without free
    deliberation messages. Unit assignment and semantic provenance certification
    remain caller responsibilities. Returned dictionaries are independent copies.
    """

    def __init__(self, document):
        _keys(document, {"format_version", "synthetic", "question", "prefix_event",
                         "calls", "records", "units"}, "evidence prefix")
        try:
            encoded = json.dumps(document, ensure_ascii=False, allow_nan=False, sort_keys=True)
            frozen = json.loads(encoded)
        except (TypeError, ValueError):
            raise ValueError("The evidence prefix must contain finite, ordinary JSON values") from None
        _require(frozen == document, "Use JSON arrays and string object keys")
        self._document = frozen
        self.input_id = identity(frozen)
        _require(type(frozen["format_version"]) is int and frozen["format_version"] == 1,
                 "Unsupported evidence format version")
        _require(type(frozen["synthetic"]) is bool, "Declare the evidence source as synthetic or recorded")
        _require(isinstance(frozen["question"], str) and bool(frozen["question"].strip()),
                 "A question is required")
        _require(type(frozen["prefix_event"]) is int and frozen["prefix_event"] > 0,
                 "Declare a positive fixed prefix boundary")
        for name in ("calls", "records", "units"):
            _require(isinstance(frozen[name], list) and bool(frozen[name]),
                     "Nonempty " + name + " required")
        self._calls = self._index_calls(frozen["calls"])
        self._records = self._index_records(frozen["records"])
        self._units, self._owner = self._index_units(frozen["units"])
        self._validate_timing()
        self._validate_chains()
        self._parents = {unit: set() for unit in self._units}
        for unit_id, unit in self._units.items():
            for call_id in unit["call_ids"]:
                for record_id in self._calls[call_id]["requires_records"]:
                    parent_call = self._records[record_id]["call_id"]
                    if parent_call is not None:
                        parent = self._owner[parent_call]
                        if parent != unit_id:
                            self._parents[unit_id].add(parent)
        self.unit_ids = tuple(sorted(self._units,
                              key=lambda unit: self._calls[self._units[unit]["call_ids"][0]]["event_index"]))

    def _index_calls(self, calls):
        for call in calls:
            _keys(call, {"call_id", "event_index", "tool", "arguments",
                         "requires_records", "provenance_complete"}, "call")
            _require(type(call["event_index"]) is int and call["event_index"] > 0,
                     "Call events must be positive integers")
            _require(isinstance(call["tool"], str) and call["tool"] in {"search", "read"},
                     "This component accepts cached search/read calls only")
            _require(isinstance(call["arguments"], dict), "Call arguments must be a JSON object")
            _require(type(call["provenance_complete"]) is bool, "Explicit provenance status required")
            prerequisites = call["requires_records"]
            _require(isinstance(prerequisites, list), "Required records must be a list")
            if prerequisites:
                _ids(prerequisites, "required records")
        _ids([call["call_id"] for call in calls], "call identifiers")
        events = [call["event_index"] for call in calls]
        _require(events == sorted(set(events)), "Calls must have distinct chronological events")
        return {call["call_id"]: call for call in calls}

    def _index_records(self, records):
        for record in records:
            _keys(record, {"record_id", "call_id", "event_index", "text",
                           "source_id", "independently_useful"}, "record")
            _require(type(record["event_index"]) is int and record["event_index"] >= 0,
                     "Record events must be nonnegative integers")
            _require(isinstance(record["text"], str) and isinstance(record["source_id"], str)
                     and bool(record["source_id"]), "Raw text and source identifier required")
            _require(type(record["independently_useful"]) is bool, "Explicit record utility annotation required")
            _require(record["call_id"] is None or isinstance(record["call_id"], str),
                     "A record's producing call must be an identifier or null")
        _ids([record["record_id"] for record in records], "record identifiers")
        events = [record["event_index"] for record in records]
        _require(events == sorted(events), "Records must preserve return order")
        return {record["record_id"]: record for record in records}

    def _index_units(self, units):
        owners = {}
        for unit in units:
            _keys(unit, {"unit_id", "call_ids", "terminal_record_id"}, "unit")
            _ids(unit["call_ids"], "unit call members")
            for call_id in unit["call_ids"]:
                _require(call_id in self._calls and call_id not in owners,
                         "Unknown or overlapping unit call")
                owners[call_id] = unit["unit_id"]
            events = [self._calls[call]["event_index"] for call in unit["call_ids"]]
            _require(events == sorted(events), "A unit must preserve call order")
            terminal = unit["terminal_record_id"]
            _require(isinstance(terminal, str) and terminal in self._records
                     and self._records[terminal]["call_id"] == unit["call_ids"][-1],
                     "Unit terminal record must be returned by its last call")
        _ids([unit["unit_id"] for unit in units], "unit identifiers")
        _require(set(owners) == set(self._calls), "Every supplied call must belong to one fixed unit")
        return {unit["unit_id"]: unit for unit in units}, owners

    def _validate_timing(self):
        boundary = self._document["prefix_event"]
        call_events = {call["event_index"] for call in self._calls.values()}
        _require(max(call_events) <= boundary, "A call is outside the fixed prefix")
        return_owners = {}
        for record in self._records.values():
            event, call_id = record["event_index"], record["call_id"]
            _require(event <= boundary and event not in call_events,
                     "A return is outside the prefix or collides with a call")
            if call_id is None:
                _require(event == 0, "Initial records must have event zero")
            else:
                _require(call_id in self._calls and event > self._calls[call_id]["event_index"],
                         "A record must follow its producing call")
            owners = return_owners.setdefault(event, set())
            owners.add(call_id)
            _require(len(owners) == 1, "One return event cannot combine different calls")
        calls = list(self._calls.values())
        for index, call in enumerate(calls):
            outputs = [r for r in self._records.values() if r["call_id"] == call["call_id"]]
            _require(bool(outputs), "Each supplied acquisition call must have a returned record")
            if index + 1 < len(calls):
                _require(max(r["event_index"] for r in outputs) < calls[index + 1]["event_index"],
                         "Asynchronous returns are outside this projection component")
            for record_id in call["requires_records"]:
                _require(record_id in self._records
                         and self._records[record_id]["event_index"] < call["event_index"],
                         "Required records must exist before the original call")

    def _validate_chains(self):
        for unit in self._units.values():
            for before, after in zip(unit["call_ids"], unit["call_ids"][1:]):
                outputs = {record_id for record_id, record in self._records.items()
                           if record["call_id"] == before}
                _require(bool(outputs & set(self._calls[after]["requires_records"])),
                         "A multi-call unit must be a connected serial chain")
                _require(not any(self._records[record]["independently_useful"] for record in outputs),
                         "An independently useful intermediate record must remain a separate unit")
                consumers = {call_id for call_id, call in self._calls.items()
                             if outputs & set(call["requires_records"])}
                _require(consumers == {after}, "A shared or branching locator must remain separate")

    def _selection(self, retained):
        if retained is None:
            return frozenset(self._units)
        _require(isinstance(retained, (list, tuple, set, frozenset)),
                 "Retained units must be a collection of identifiers")
        values = list(retained)
        if values:
            _ids(values, "retained units")
        _require(set(values) <= set(self._units), "Unknown retained unit")
        return frozenset(values)

    def dependency_closure(self, retained):
        result = set(self._selection(retained))
        pending = list(result)
        while pending:
            for parent in self._parents[pending.pop()]:
                if parent not in result:
                    result.add(parent)
                    pending.append(parent)
        return frozenset(result)

    def delete_unit_and_dependents(self, removed, retained=None):
        """Delete a whole unit, then remove units missing a required predecessor."""
        result = set(self._selection(retained))
        _require(isinstance(removed, str) and removed in result, "Delete a retained unit identifier")
        result.remove(removed)
        while True:
            invalid = {unit for unit in result if not self._parents[unit] <= result}
            if not invalid:
                return frozenset(result)
            result -= invalid

    def _available_records(self, retained, boundary):
        return [record for record in self._records.values()
                if record["event_index"] <= boundary and
                (record["call_id"] is None or self._owner[record["call_id"]] in retained)]

    @staticmethod
    def _record_payload(record):
        return {"source_id": record["source_id"], "text": record["text"]}

    def project(self, retained=None):
        """Build structural views; do not infer support or training eligibility."""
        selected = self._selection(retained)
        _require(self.dependency_closure(selected) <= selected,
                 "Missing dependencies: a projection cannot silently add evidence")
        call_inputs = []
        for call_id, call in self._calls.items():
            if self._owner[call_id] not in selected:
                continue
            _require(call["provenance_complete"], "Unresolved argument provenance in a retained call")
            available = self._available_records(selected, call["event_index"] - 1)
            _require(set(call["requires_records"]) <= {record["record_id"] for record in available},
                     "Retained call inputs are unavailable before that call")
            messages = []
            for previous in self._calls.values():
                if previous["event_index"] < call["event_index"] and self._owner[previous["call_id"]] in selected:
                    messages.append((previous["event_index"], {"kind": "call", "tool": previous["tool"],
                                     "arguments": copy.deepcopy(previous["arguments"])}))
            messages.extend((record["event_index"], {"kind": "record", **self._record_payload(record)})
                            for record in available)
            messages.sort(key=lambda item: item[0])
            call_inputs.append({"call_id": call_id, "input": {
                "question": self._document["question"], "messages": [message for _, message in messages]}})
        visible = self._available_records(selected, self._document["prefix_event"])
        payload = {"question": self._document["question"],
                   "records": [self._record_payload(record) for record in visible]}
        return seal("evidence-projection", {
            "synthetic": self._document["synthetic"], "input_id": self.input_id,
            "retained_unit_ids": [unit for unit in self.unit_ids if unit in selected],
            "retained_record_ids": [record["record_id"] for record in visible],
            "record_view": payload, "view_id": identity(payload), "call_inputs": call_inputs,
            "support_status": "not_assessed",
        })
