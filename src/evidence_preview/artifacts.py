"""Content fingerprints and non-overwriting JSON I/O, without project services.

A fingerprint detects accidental changes relative to an available reference.
It is not a signature, proof of authorship, or proof an experiment took place.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def identity(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def seal(kind, body):
    if not isinstance(kind, str) or not kind or not isinstance(body, dict):
        raise ValueError("A nonempty artifact kind and object body are required")
    reserved = {"kind", "artifact_version", "artifact_id"}
    if reserved.intersection(body):
        raise ValueError("Artifact metadata cannot be supplied in the body")
    value = {"kind": kind, "artifact_version": 1, **body}
    return {**value, "artifact_id": identity(value)}


def verify(value, kind):
    if (not isinstance(value, dict) or value.get("kind") != kind
            or type(value.get("artifact_version")) is not int
            or value["artifact_version"] != 1):
        raise ValueError("Unexpected artifact kind or version")
    expected = identity({k: v for k, v in value.items() if k != "artifact_id"})
    if value.get("artifact_id") != expected:
        raise ValueError("Artifact content differs from its fingerprint")
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Non-finite JSON numbers are not supported")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=_unique_object,
                      parse_constant=_invalid_constant)


def encode_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def write_json(path, value):
    """Serialize before creating a file; never replace an existing output."""
    payload = encode_json(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
