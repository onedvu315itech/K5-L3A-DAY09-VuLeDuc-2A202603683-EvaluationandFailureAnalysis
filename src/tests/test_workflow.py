"""Additional checks scoped to Shape A: unknown input and all crash windows."""

import json

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash
from lab8.shapes.workflow import run_claim


def test_workflow_unknown_claim_returns_safe_trace(public_db):
    result = run_claim("unknown", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
    with open(result.trace_path, encoding="utf-8") as handle:
        trace = json.load(handle)
    assert trace["run_id"] == result.run_id
    assert trace["events"]


@pytest.mark.parametrize("crash_at", [
    "before_effect", "after_effect_before_checkpoint", "after_checkpoint",
])
def test_workflow_resume_all_crash_windows(public_db, crash_at):
    with pytest.raises(InjectedCrash):
        run_claim("C-012", seed=11, store_path=str(public_db), crash_at=crash_at)
    result = run_claim("C-012", seed=11, store_path=str(public_db))
    assert result.status == "resolved"
    assert len(result.refund_effects) == 1
    assert result.committed_audit_count == 1
    conn = connect(public_db)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM refund_ledger WHERE claim_id = ?", ("C-012",)
        ).fetchone()[0] == 1
    finally:
        conn.close()
