"""
Agent 3 — Candidate Ranker
Uses ranker_tool for deterministic sorting and Ollama LLM for intelligent
reasoning about each candidate's ranking decision and shortlist justification.
"""

from typing import Any
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from tools.ranker_tool import ranker_tool

AGENT_NAME   = "CandidateRanker"
#OLLAMA_MODEL = "llama3:8b"
OLLAMA_MODEL = "phi3:latest"

# ---------------------------------------------------------------------------
# System prompt — persona and constraints for the LLM
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a senior HR analyst and talent acquisition specialist.
Your role is to provide clear, professional, and objective reasoning for candidate
ranking decisions based on their match scores against job requirements.

Rules you must follow:
- Be concise: 1-2 sentences per candidate reasoning.
- Be professional and unbiased — focus only on skills and experience fit.
- Never invent skills or qualifications not mentioned in the input.
- Never change the scores or rankings — those are already decided.
- Always justify WHY a candidate is Shortlisted or Rejected based on their score.
- Do not use bullet points — write in plain prose only.
"""


def _generate_candidate_reasoning(
    llm: ChatOllama,
    candidate: dict[str, Any],
    job_context: str,
) -> str:
    """
    Uses the LLM to generate a professional reasoning statement for a single
    candidate's ranking decision.

    Args:
        llm: The ChatOllama instance to use for generation.
        candidate: A ranked candidate dict with rank, name, score, status, reasoning.
        job_context: A brief description of what the job requires.

    Returns:
        A professional 1-2 sentence reasoning string from the LLM.
    """
    prompt = f"""A candidate has been evaluated for the following position:
{job_context}

Candidate details:
- Name: {candidate['name']}
- Match Score: {candidate['score']}/100
- Ranking Position: #{candidate['rank']}
- Decision: {candidate['status']}
- Initial assessment from job matcher: {candidate.get('reasoning', 'No initial assessment provided.')}

Write 1-2 professional sentences explaining why this candidate received this
decision. Focus on their score relative to the role requirements."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception:
        return candidate.get(
            "reasoning",
            f"Ranked #{candidate['rank']} with a score of {candidate['score']}/100."
        )


def _generate_executive_summary(
    llm: ChatOllama,
    ranked_candidates: list[dict[str, Any]],
    job_context: str,
) -> str:
    """
    Uses the LLM to generate an executive summary of the entire shortlisting
    decision for the HR manager.

    Args:
        llm: The ChatOllama instance to use for generation.
        ranked_candidates: The full list of ranked candidates.
        job_context: A brief description of what the job requires.

    Returns:
        A professional executive summary string (3-4 sentences).
    """
    shortlisted = [c for c in ranked_candidates if c["status"] == "Shortlisted"]
    rejected    = [c for c in ranked_candidates if c["status"] == "Rejected"]

    shortlisted_summary = ", ".join(
        f"{c['name']} (score: {c['score']})" for c in shortlisted
    )
    rejected_summary = ", ".join(
        f"{c['name']} (score: {c['score']})" for c in rejected
    )

    prompt = f"""You are writing an executive summary for an HR manager reviewing
a CV screening result for the following position:
{job_context}

Screening results:
- Total candidates evaluated: {len(ranked_candidates)}
- Shortlisted ({len(shortlisted)}): {shortlisted_summary}
- Rejected ({len(rejected)}): {rejected_summary}

Write a 3-4 sentence professional executive summary explaining the overall
screening outcome, the quality of the shortlisted candidates, and a brief
note on why the rejected candidates did not make the cut."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception:
        return (
            f"Screening complete. {len(shortlisted)} of {len(ranked_candidates)} "
            f"candidates were shortlisted based on their match scores."
        )


def run_candidate_ranker(state: dict[str, Any]) -> dict[str, Any]:
    """
    Agent 3 — Candidate Ranker node for LangGraph.

    Uses a two-step approach:
      1. ranker_tool (pure Python) — deterministically sorts and labels candidates.
      2. Ollama LLM (llama3:8b)   — generates professional reasoning for each
                                     candidate and an executive summary.

    Steps:
        1. Read scored_candidates from shared state.
        2. Call ranker_tool to sort by score and assign Shortlisted/Rejected labels.
        3. Use LLM to generate per-candidate reasoning statements.
        4. Use LLM to generate an executive summary for the HR manager.
        5. Write ranked_candidates and executive_summary back to state.

    Args:
        state: The shared MAS state dict containing:
            - scored_candidates (list): Candidates with scores from Agent 2.
            - job_description_path (str): Path to job description (for context).
            - logs (list): Shared log list.
            - errors (list): Shared error list.

    Returns:
        Updated state with ranked_candidates and executive_summary populated.
    """
    from observability.logger import log_event

    log_event(
        AGENT_NAME, "agent_start",
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

    # ------------------------------------------------------------------
    # Step 1 — Deterministic ranking via ranker_tool
    # ------------------------------------------------------------------
    log_event(
        AGENT_NAME, "tool_call",
        tool_name="ranker_tool",
        inputs={"candidate_count": len(scored_candidates), "top_n": 3},
        message=f"Calling ranker_tool with {len(scored_candidates)} candidates",
    )

    try:
        ranked_candidates = ranker_tool(scored_candidates, top_n=3)
        log_event(
            AGENT_NAME, "tool_result",
            tool_name="ranker_tool",
            outputs={
                "ranked_count": len(ranked_candidates),
                "shortlisted":  [c["name"] for c in ranked_candidates if c["status"] == "Shortlisted"],
                "rejected":     [c["name"] for c in ranked_candidates if c["status"] == "Rejected"],
            },
            message="ranker_tool completed successfully",
        )
    except (ValueError, KeyError, TypeError) as e:
        error_msg = f"CandidateRanker: ranker_tool failed — {e}"
        state["errors"].append(error_msg)
        state["ranked_candidates"] = []
        log_event(AGENT_NAME, "error", message=error_msg)
        return state

    # ------------------------------------------------------------------
    # Step 2 — LLM reasoning via Ollama
    # ------------------------------------------------------------------
    log_event(
        AGENT_NAME, "llm_start",
        message=f"Initialising Ollama LLM ({OLLAMA_MODEL}) for reasoning generation",
    )

    # Build job context from state
    job_description_path = state.get("job_description_path", "")
    job_context = "Software Engineer role requiring strong technical skills and relevant experience."

    # Try to read actual job description if available
    try:
        import json, os
        if job_description_path and os.path.exists(job_description_path):
            with open(job_description_path, "r") as f:
                job_data = json.load(f)
                job_context = (
                    f"{job_data.get('title', 'Software Engineer')} — "
                    f"{job_data.get('description', '')} "
                    f"Required skills: {', '.join(job_data.get('required_skills', []))}"
                )
    except Exception:
        pass  # Use default job context if file can't be read

    try:
        llm = ChatOllama(model=OLLAMA_MODEL, temperature=0.3)

        # Generate per-candidate reasoning
        log_event(
            AGENT_NAME, "llm_call",
            message=f"Generating LLM reasoning for {len(ranked_candidates)} candidates",
        )

        for candidate in ranked_candidates:
            reasoning = _generate_candidate_reasoning(llm, candidate, job_context)
            candidate["reasoning"] = reasoning
            log_event(
                AGENT_NAME, "llm_result",
                outputs={"candidate": candidate["name"], "reasoning": reasoning},
                message=f"Reasoning generated for {candidate['name']}",
            )

        # Generate executive summary
        log_event(AGENT_NAME, "llm_call", message="Generating executive summary")
        executive_summary = _generate_executive_summary(llm, ranked_candidates, job_context)
        state["executive_summary"] = executive_summary
        log_event(
            AGENT_NAME, "llm_result",
            outputs={"executive_summary": executive_summary},
            message="Executive summary generated successfully",
        )

    except Exception as e:
        error_msg = f"CandidateRanker: LLM reasoning failed — {e}"
        state["errors"].append(error_msg)
        log_event(AGENT_NAME, "error", message=error_msg)
        # Don't return early — ranking still succeeded, just no LLM reasoning

    # ------------------------------------------------------------------
    # Step 3 — Write results back to shared state
    # ------------------------------------------------------------------
    state["ranked_candidates"] = ranked_candidates

    shortlisted_count = sum(1 for c in ranked_candidates if c["status"] == "Shortlisted")
    summary = (
        f"CandidateRanker: Ranked {len(ranked_candidates)} candidates — "
        f"{shortlisted_count} Shortlisted, "
        f"{len(ranked_candidates) - shortlisted_count} Rejected."
    )
    state["logs"].append(summary)

    log_event(
        AGENT_NAME, "agent_end",
        outputs={
            "ranked_candidates":  ranked_candidates,
            "shortlisted_count":  shortlisted_count,
            "executive_summary":  state.get("executive_summary", ""),
        },
        message=summary,
    )

    return state