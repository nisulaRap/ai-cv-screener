# agents/job_matcher_agent.py
# Agent 2 — Job Matcher
# Reads candidate_profiles from MASState, scores each one, writes match_results back.

import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import initialize_database, clear_results_for_job
from tools.score_candidate_tool import score_candidate
from logs.agent_log import (
    log_agent_start,
    log_agent_complete,
    log_tool_error,
    log_state_update
)
from state.shared_state import MASState, MatchResult


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
    """
    for field in AGENT_CONSTRAINTS["required_profile_fields"]:
        if field not in candidate or candidate[field] is None:
            return False
    return True


def validate_job_description(job: Dict[str, Any]) -> bool:
    """
    Validates that the job description has all required fields
    before the agent begins processing.
    """
    required = ["job_id", "title", "required_skills", "min_experience_years", "description"]
    for field in required:
        if field not in job or job[field] is None:
            return False
    return True


def run_job_matcher_agent(state: MASState) -> MASState:
    """
    Agent 2 LangGraph node — Job Matcher.

    Reads candidate_profiles and job_description from MASState,
    scores each candidate using the score_candidate tool, and writes
    match_results back into the state for Agent 3 (Candidate Ranker).

    Args:
        state (MASState): The global pipeline state populated by Agent 1.

    Returns:
        MASState: Updated state with match_results populated.
    """
    print("\n" + "=" * 60)
    print(AGENT_PERSONA)
    print("=" * 60 + "\n")

    # ── Step 1: Extract data from state ──
    job = state.get("job_description", {})
    # Agent 1 writes to "candidate_profiles"; use it
    candidates = state.get("candidate_profiles") or []

    if not candidates:
        error_msg = "Job Matcher: No candidate profiles found in state. Did Agent 1 run?"
        state.setdefault("errors", []).append(error_msg)
        state.setdefault("match_results", [])
        log_tool_error("N/A", error_msg)
        return state

    # ── Step 2: Validate job description ──
    if not validate_job_description(job):
        error_msg = "Job description is missing required fields. Agent cannot proceed."
        state.setdefault("errors", []).append(error_msg)
        state.setdefault("match_results", [])
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
            state.setdefault("errors", []).append(warning)
            log_tool_error(candidate.get("candidate_id", "N/A"), warning)
            skipped.append(candidate.get("name", "Unknown"))
            continue

        try:
            result: MatchResult = score_candidate(candidate, job)
            # Carry email forward from the profile (score_candidate doesn't set it)
            result.setdefault("email", candidate.get("email", ""))
            match_results.append(result)

        except RuntimeError as e:
            error_msg = str(e)
            state.setdefault("errors", []).append(error_msg)
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

    print(f"\n✅ Job Matcher Agent finished. Scored {len(match_results)}/{len(candidates)} candidates.")

    return state