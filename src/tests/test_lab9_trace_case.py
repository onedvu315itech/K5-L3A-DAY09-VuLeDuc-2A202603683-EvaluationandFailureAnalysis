"""Regression test for the trace case documented in docs/trace_case.md (C-002@11, FM-03)."""

import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9.graders import DbFactKept, RefundAmountCorrect
from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def _ctx(case: dict) -> EvaluatorContext:
    return EvaluatorContext(
        name="C-002@11",
        inputs={"claim_id": "C-002", "seed": 11},
        metadata=None,
        expected_output=case["label"],
        output=case["trial"],
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )


def test_trace_case_c002_s11_fixed_passes_and_seeded_regression_fails():
    fixed = investigate("fixed", "C-002", 11)
    assert fixed["trial"]["lab8_pass"] is True
    assert DbFactKept().evaluate(_ctx(fixed)).value is True
    assert RefundAmountCorrect().evaluate(_ctx(fixed)).value is True

    bad = investigate("seeded_regression", "C-002", 11)
    assert bad["trial"]["lab8_pass"] is False
    assert DbFactKept().evaluate(_ctx(bad)).value is False
    assert RefundAmountCorrect().evaluate(_ctx(bad)).value is False
