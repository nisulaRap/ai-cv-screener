# main.py

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.job_matcher_agent import run_job_matcher_agent
from shared_state import PipelineState, JobDescription, CandidateProfile


# ─────────────────────────────────────────────
# SAMPLE JOB DESCRIPTION
# (In the real pipeline, this comes from a JSON file)
# ─────────────────────────────────────────────

SAMPLE_JOB: JobDescription = {
    "job_id": "job_001",
    "title": "Senior Python Developer",
    "required_skills": [
        "Python", "REST APIs", "SQL", "Git"
    ],
    "preferred_skills": [
        "FastAPI", "Docker", "PostgreSQL", "Redis"
    ],
    "min_experience_years": 3.0,
    "education_requirement": "Bachelor's degree in Computer Science or related field",
    "description": (
        "We are looking for a Senior Python Developer to join our backend team. "
        "You will design and build scalable REST APIs, work with SQL databases, "
        "and collaborate with frontend teams. Experience with FastAPI and Docker "
        "is a strong advantage. You must be comfortable working in an agile environment."
    )
}


# ─────────────────────────────────────────────
# SAMPLE CANDIDATES
# (In the real pipeline, these come from Agent 1)
# ─────────────────────────────────────────────

SAMPLE_CANDIDATES = [
    CandidateProfile(
        candidate_id="candidate_001",
        name="Alice Fernando",
        email="alice@example.com",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs", "SQL"],
        experience_years=5.0,
        education="Bachelor's in Computer Science",
        raw_text="Alice Fernando - Senior Python Developer with 5 years experience..."
    ),
    CandidateProfile(
        candidate_id="candidate_002",
        name="Bob Perera",
        email="bob@example.com",
        skills=["Java", "Spring Boot", "MySQL", "Git"],
        experience_years=4.0,
        education="Bachelor's in Information Technology",
        raw_text="Bob Perera - Java developer with 4 years experience..."
    ),
    CandidateProfile(
        candidate_id="candidate_003",
        name="Chamari Silva",
        email="chamari@example.com",
        skills=["Python", "SQL", "Git", "REST APIs"],
        experience_years=2.0,
        education="Bachelor's in Computer Science",
        raw_text="Chamari Silva - Python developer with 2 years experience..."
    ),
    CandidateProfile(
        candidate_id="candidate_004",
        name="David Rajapaksa",
        email="david@example.com",
        skills=["Python", "FastAPI", "Docker", "Redis", "PostgreSQL", "SQL", "Git", "REST APIs"],
        experience_years=7.0,
        education="Master's in Software Engineering",
        raw_text="David Rajapaksa - Senior engineer with 7 years experience..."
    ),
    CandidateProfile(
        candidate_id="candidate_005",
        name="Emma Wickramasinghe",
        email="emma@example.com",
        skills=["HTML", "CSS", "JavaScript"],
        experience_years=1.0,
        education="Diploma in Web Design",
        raw_text="Emma Wickramasinghe - Frontend developer with 1 year experience..."
    )
]


# ─────────────────────────────────────────────
# BUILD INITIAL PIPELINE STATE
# ─────────────────────────────────────────────

def build_initial_state() -> PipelineState:
    """
    Builds the initial pipeline state with sample data.
    In the real pipeline, Agent 1 populates 'candidates'
    and the orchestrator loads the job description from a JSON file.

    Returns:
        PipelineState: Initial state ready to be passed to Job Matcher Agent.
    """
    return PipelineState(
        job_description=SAMPLE_JOB,
        candidates=SAMPLE_CANDIDATES,
        match_results=[],
        ranked_candidates=[],
        report_path=None,
        errors=[]
    )


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    """
    Main entry point for running the Job Matcher Agent in isolation.
    Builds a sample pipeline state, runs the agent, and prints results.

    Returns:
        None
    """
    print("\n🚀 Starting CV Screener Pipeline — Job Matcher Agent")
    print("=" * 60)

    # Build initial state
    state = build_initial_state()

    print(f"\n📋 Job Title     : {state['job_description']['title']}")
    print(f"👥 Candidates    : {len(state['candidates'])}")
    print("\nRunning Job Matcher Agent...\n")

    # Run your agent
    updated_state = run_job_matcher_agent(state)

    # ── Print Results ──
    print("\n" + "=" * 60)
    print("📊 MATCH RESULTS SUMMARY")
    print("=" * 60)

    if not updated_state["match_results"]:
        print("❌ No results were produced.")
    else:
        # Sort by score descending for display
        sorted_results = sorted(
            updated_state["match_results"],
            key=lambda x: x["score"],
            reverse=True
        )

        for i, result in enumerate(sorted_results, 1):
            print(f"\n#{i} {result['name']}")
            print(f"   Score         : {result['score']}/100")
            print(f"   Matched Skills: {', '.join(result['matched_skills'])}")
            print(f"   Missing Skills: {', '.join(result['missing_skills'])}")
            print(f"   Reasoning     : {result['reasoning']}")

    # ── Print Errors ──
    if updated_state["errors"]:
        print("\n⚠️  ERRORS DURING RUN:")
        for err in updated_state["errors"]:
            print(f"   - {err}")

    print("\n✅ Pipeline run complete. Check logs/job_matcher.log for full details.")
    print("=" * 60)


if __name__ == "__main__":
    main()