from typing import Any
from tools.ranker_tool import ranker_tool
from observability.logger import log_event
from state.shared_state import MASState

AGENT_NAME = "CandidateRanker"


def run_candidate_ranker(state: dict[str, Any]) -> dict[str, Any]:
    """
    Agent 3 — Candidate Ranker node for LangGraph.

    Reads scored candidates from the shared MAS state, uses the ranker_tool
    to sort and label them, then writes the ranked list back to state for
    Agent 4 (Report Generator) to consume.

    Steps:
        1. Reads scored_candidates from shared state.
        2. Validates that scored candidates exist.
        3. Calls ranker_tool to sort by score and assign Shortlisted/Rejected labels.
        4. Logs all actions using the shared observability logger.
        5. Writes ranked_candidates back to state.

    Args:
        state: The shared MAS state dict containing at minimum:
            - scored_candidates (list): Candidates with scores from Agent 2.
            - logs (list): Shared log list to append messages to.
            - errors (list): Shared error list to append errors to.

    Returns:
        Updated state with ranked_candidates populated.
    """
    from observability.logger import log_event

    log_event(
        AGENT_NAME,
        "agent_start",
        message="Candidate Ranker starting — reading scored candidates from state",
    )

    scored_candidates: list[dict[str, Any]] = state.get("scored_candidates", [])

    # Guard: nothing to rank
    if not scored_candidates:
        error_msg = "CandidateRanker: No scored candidates found in state."
        state["errors"].append(error_msg)
        state["ranked_candidates"] = []
        log_event(AGENT_NAME, "error", message=error_msg)
        return state

    log_event(
        AGENT_NAME,
        "tool_call",
        tool_name="ranker_tool",
        inputs={
            "candidate_count": len(scored_candidates),
            "top_n": 3,
        },
        message=f"Calling ranker_tool with {len(scored_candidates)} candidates",
    )

    try:
        ranked_candidates = ranker_tool(scored_candidates, top_n=3)

        log_event(
            AGENT_NAME,
            "tool_result",
            tool_name="ranker_tool",
            outputs={
                "ranked_count": len(ranked_candidates),
                "shortlisted": [c["name"] for c in ranked_candidates if c["status"] == "Shortlisted"],
                "rejected":    [c["name"] for c in ranked_candidates if c["status"] == "Rejected"],
            },
            message="ranker_tool completed successfully",
        )

    except (ValueError, KeyError, TypeError) as e:
        error_msg = f"CandidateRanker: ranker_tool failed — {e}"
        state["errors"].append(error_msg)
        state["ranked_candidates"] = []
        log_event(AGENT_NAME, "error", message=error_msg)
        return state

    # Write results to shared state
    state["ranked_candidates"] = ranked_candidates

    shortlisted_count = sum(1 for c in ranked_candidates if c["status"] == "Shortlisted")
    summary = (
        f"CandidateRanker: Ranked {len(ranked_candidates)} candidates — "
        f"{shortlisted_count} Shortlisted, "
        f"{len(ranked_candidates) - shortlisted_count} Rejected."
    )
    state["logs"].append(summary)

    log_event(
        AGENT_NAME,
        "agent_end",
        outputs={
            "ranked_candidates": ranked_candidates,
            "shortlisted_count": shortlisted_count,
        },
        message=summary,
    )

    return state