# agents/job_matcher_agent.py

import sys
import os
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import initialize_database, clear_results_for_job
from tools.score_candidate_tool import score_candidate
from logs.agent_log import (
    log_agent_start,
    log_agent_complete,
    log_tool_error,
    log_state_update
)
from shared_state import PipelineState, MatchResult


# ─────────────────────────────────────────────
# AGENT PERSONA & SYSTEM PROMPT
# ─────────────────────────────────────────────

AGENT_PERSONA = """
You are the Job Matcher Agent, a highly specialized HR evaluation engine.

Your sole responsibility is to fairly and objectively evaluate how well 
each candidate's profile matches the given job description.

Your principles:
- You are strictly objective. You do not favour any candidate.
- You base every score purely on skills, experience, and education.
- You always explain your reasoning clearly and concisely.
- You never skip a candidate, even if their profile is incomplete.
- You flag missing or incomplete data instead of guessing.
- You always return structured, validated JSON output.
- You are meticulous — every score must be justifiable.

You work as part of a multi-agent pipeline:
- You receive structured candidate profiles from the Document Parser Agent.
- You pass your scored results to the Candidate Ranker Agent via the database.
- You do not rank or shortlist — that is the Ranker's job.
"""


# ─────────────────────────────────────────────
# AGENT CONSTRAINTS
# ─────────────────────────────────────────────

AGENT_CONSTRAINTS = {
    "min_score": 0.0,
    "max_score": 100.0,
    "max_retries_per_candidate": 3,
    "required_profile_fields": [
        "candidate_id",
        "name",
        "skills",
        "experience_years",
        "education"
    ]
}


def validate_candidate_profile(candidate: Dict[str, Any]) -> bool:
    """
    Validates that a candidate profile has all required fields
    before passing it to the scoring tool.

    Args:
        candidate (Dict[str, Any]): The candidate profile to validate.

    Returns:
        bool: True if valid, False if any required field is missing.
    """
    for field in AGENT_CONSTRAINTS["required_profile_fields"]:
        if field not in candidate or candidate[field] is None:
            return False
    return True


def validate_job_description(job: Dict[str, Any]) -> bool:
    """
    Validates that the job description has all required fields
    before the agent begins processing.

    Args:
        job (Dict[str, Any]): The job description to validate.

    Returns:
        bool: True if valid, False if any required field is missing.
    """
    required = ["job_id", "title", "required_skills", "min_experience_years", "description"]
    for field in required:
        if field not in job or job[field] is None:
            return False
    return True


def run_job_matcher_agent(state: PipelineState) -> PipelineState:
    """
    Main entry point for the Job Matcher Agent.

    Reads candidate profiles and the job description from the pipeline state,
    scores each candidate using the score_candidate tool, and writes results
    back into the pipeline state for Agent 3 (Candidate Ranker) to consume.

    This function also initializes the database, clears any previous results
    for the same job, and handles errors gracefully without stopping the pipeline.

    Args:
        state (PipelineState): The global pipeline state containing the job
                               description and list of candidate profiles
                               populated by Agent 1.

    Returns:
        PipelineState: Updated pipeline state with match_results populated,
                       ready to be passed to the Candidate Ranker Agent.
    """
    print("\n" + "=" * 60)
    print(AGENT_PERSONA)
    print("=" * 60 + "\n")

    # ── Step 1: Extract data from state ──
    job = state["job_description"]
    candidates = state["candidates"]

    # ── Step 2: Validate job description ──
    if not validate_job_description(job):
        error_msg = "Job description is missing required fields. Agent cannot proceed."
        state["errors"].append(error_msg)
        log_tool_error("N/A", error_msg)
        return state

    # ── Step 3: Initialize database ──
    initialize_database()
    clear_results_for_job(job["job_id"])

    # ── Step 4: Log agent start ──
    log_agent_start(job["job_id"], len(candidates))

    # ── Step 5: Score each candidate ──
    match_results = []
    skipped = []

    for candidate in candidates:

        # Validate profile before scoring
        if not validate_candidate_profile(candidate):
            warning = f"Skipping candidate '{candidate.get('name', 'Unknown')}' — incomplete profile."
            state["errors"].append(warning)
            log_tool_error(candidate.get("candidate_id", "N/A"), warning)
            skipped.append(candidate.get("name", "Unknown"))
            continue

        try:
            result: MatchResult = score_candidate(candidate, job)
            match_results.append(result)

        except RuntimeError as e:
            error_msg = str(e)
            state["errors"].append(error_msg)
            log_tool_error(candidate["candidate_id"], error_msg)
            skipped.append(candidate["name"])

    # ── Step 6: Update pipeline state ──
    state["match_results"] = match_results

    # ── Step 7: Log state update ──
    log_state_update(
        stage="Job Matcher → Candidate Ranker",
        data={
            "job_id": job["job_id"],
            "total_candidates": len(candidates),
            "total_scored": len(match_results),
            "skipped": skipped,
            "scores": [
                {"name": r["name"], "score": r["score"]}
                for r in match_results
            ]
        }
    )

    # ── Step 8: Log agent completion ──
    log_agent_complete(job["job_id"], len(match_results))

    if skipped:
        print(f"\n⚠️  Skipped {len(skipped)} candidate(s): {skipped}")

    print(f"\n Job Matcher Agent finished. Scored {len(match_results)}/{len(candidates)} candidates.")

    return state

# ─────────────────────────────────────────────
# LANGGRAPH NODE WRAPPER
# ─────────────────────────────────────────────

from langgraph.graph import StateGraph, END
from typing import Literal


def job_matcher_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node wrapper for the Job Matcher Agent.
    This function is registered as a node in the LangGraph pipeline.

    Args:
        state (PipelineState): The current global pipeline state.

    Returns:
        PipelineState: Updated state after job matching is complete.
    """
    return run_job_matcher_agent(state)


def should_continue(state: PipelineState) -> Literal["continue", "stop"]:
    """
    LangGraph conditional edge function.
    Determines whether the pipeline should continue to Agent 3
    or stop due to errors.

    Args:
        state (PipelineState): The current pipeline state.

    Returns:
        Literal["continue", "stop"]: Routing decision.
    """
    if not state["match_results"]:
        return "stop"
    return "continue"


def build_job_matcher_graph() -> StateGraph:
    """
    Builds and returns the LangGraph StateGraph for the Job Matcher Agent.
    Can be used standalone for testing or merged into the full pipeline graph.

    Returns:
        StateGraph: Compiled LangGraph graph with job matcher node.
    """
    graph = StateGraph(PipelineState)

    # Add the job matcher as a node
    graph.add_node("job_matcher", job_matcher_node)

    # Set entry point
    graph.set_entry_point("job_matcher")

    # Add conditional edge
    graph.add_conditional_edges(
        "job_matcher",
        should_continue,
        {
            "continue": END,
            "stop": END
        }
    )

    return graph.compile()