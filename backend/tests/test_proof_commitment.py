"""Commitments must be deterministic, tamper evident, and keep internal data private."""

from uuid import uuid4

from dogeapi.proof.service import make_digest, opaque_id


def test_commitment_changes_when_snapshot_changes() -> None:
    salt = "9a" * 32
    original = {"event_type": "stored", "evidence": [{"sha256": "a" * 64}]}
    reordered = {"evidence": [{"sha256": "a" * 64}], "event_type": "stored"}
    tampered = {"event_type": "stored", "evidence": [{"sha256": "b" * 64}]}
    assert make_digest(original, salt) == make_digest(reordered, salt)
    assert make_digest(original, salt) != make_digest(tampered, salt)
    assert make_digest(original, salt) != make_digest(original, "8b" * 32)


def test_opaque_reference_is_tenant_bound() -> None:
    event_id = uuid4()
    org_id = uuid4()
    result = opaque_id(org_id, event_id, "test-secret" * 4)
    assert result.startswith("0x") and len(result) == 66
    assert str(event_id) not in result
    assert opaque_id(org_id, event_id, "test-secret" * 4) == result
    assert opaque_id(uuid4(), event_id, "test-secret" * 4) != result
