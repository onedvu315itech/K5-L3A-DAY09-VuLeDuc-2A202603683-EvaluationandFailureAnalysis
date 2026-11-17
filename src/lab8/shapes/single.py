"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    # TODO CP2 (student): thay stub này bằng shape single theo các bước ở docstring đầu file.
    # TODO CP3 (student): truyền crash_at vào durability.issue_refund, không bắt InjectedCrash.
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()

def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id("single", claim_id, seed)
    trace = Trace(run_id)
    budget.add_tool(tool_cost())
    claim_view = get_claim_view(conn, claim_id)
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )
    state: dict[str, Any] = {
        "step": 0,
        "order": None,
        "refund_history": None,
        "quote": None,
    }
    def decide(obs: dict[str, Any]) -> dict[str, Any]:
        state["step"] += 1
        last_tool = obs.get("last_tool")
        last_result = obs.get("last_result")
        complete(
            budget,
            seed=seed,
            purpose="react",
            prompt=f"claim={claim_id};step={state['step']};last_tool={last_tool};ticket={claim_view.get('ticket', '')}",
        )
        if last_tool == "lookup_order" and isinstance(last_result, dict):
            trace.add("tool", {"name": "lookup_order", "result": safe_dump(last_result)})
            if not last_result.get("visible"):
                return {
                    "final": {
                        "status": "escalated",
                        "proposal_amount": 0,
                        "error_reason": last_result.get("reason"),
                    }
                }
            state["order"] = last_result["order"]
        elif last_tool == "lookup_refund_history" and isinstance(last_result, dict):
            trace.add("tool", {"name": "lookup_refund_history", "result": safe_dump(last_result)})
            state["refund_history"] = last_result
        elif last_tool == "compute_compensation" and isinstance(last_result, dict):
            trace.add("quote", safe_dump(last_result))
            state["quote"] = last_result
            return {
                "final": {
                    "status": "quoted",
                    "proposal_amount": int(last_result["amount_vnd"]),
                    "error_reason": last_result.get("reason"),
                }
            }
        if not claim_view.get("order_id"):
            return {
                "final": {
                    "status": "needs_info",
                    "proposal_amount": 0,
                    "error_reason": "missing_order_id",
                }
            }
        if state["order"] is None:
            return {
                "tool": "lookup_order",
                "args": {
                    "order_id": claim_view["order_id"],
                    "principal_id": claim_view["principal_id"],
                },
            }
        if state["refund_history"] is None:
            return {
                "tool": "lookup_refund_history",
                "args": {
                    "order_id": claim_view["order_id"],
                    "principal_id": claim_view["principal_id"],
                },
            }
        return {
            "tool": "compute_compensation",
            "args": {"order": state["order"]},
        }
    loop_out = run_react(
        conn,
        budget,
        observation={"claim": claim_view},
        decide=decide,
        max_steps=8,
        worker=True,
    )
    if loop_out["stopped"] == "step_cap":
        trace.add("decision", {"status": "failed", "reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )
    final = loop_out["final"]
    if final["status"] in ("needs_info", "escalated"):
        complete(budget, seed=seed, purpose="draft", prompt=final["status"])
        trace.add("decision", {"status": final["status"], "reason": final.get("error_reason")})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=final["status"],
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason"),
        )
    proposal = int(final["proposal_amount"])
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    if proposal <= 0:
        trace.add("decision", {"status": "denied", "proposal_amount": 0, "reason": final.get("error_reason")})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason"),
        )
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        trace.add("host_outcome", {"status": status, "reason": outcome["reason"], "proposal_amount": proposal})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )
    trace.add("host_outcome", {"status": "resolved", "reason": outcome["reason"], "proposal_amount": proposal})
    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
