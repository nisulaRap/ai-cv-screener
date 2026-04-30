# shared_state.py
from typing import TypedDict, List, Optional


class CandidateProfile(TypedDict):
    """
    Output from Agent 1 (Document Parser).
    Represents a single parsed candidate CV.
    """
    candidate_id: str        # unique ID e.g. "candidate_001"
    name: str                # full name
    email: str               # email address
    skills: List[str]        # e.g. ["Python", "SQL", "Machine Learning"]
    experience_years: float  # total years of experience
    education: str           # highest qualification
    raw_text: str            # full CV text (fallback for LLM)


class MatchResult(TypedDict):
    """
    Output from Agent 2 (Job Matcher) — YOUR output.
    Represents the scoring result for one candidate.
    """
    candidate_id: str        # same ID from CandidateProfile
    name: str                # candidate name
    score: float             # match score 0-100
    reasoning: str           # why this score was given
    matched_skills: List[str]       # skills that matched the job
    missing_skills: List[str]       # skills the job needs but candidate lacks
    status: str              # "Shortlisted" or "Rejected" (set by Agent 3)


class JobDescription(TypedDict):
    """
    The job posting HR provides as input.
    Stored as a JSON file in data/job_descriptions/
    """
    job_id: str              # unique job ID
    title: str               # e.g. "Senior Python Developer"
    required_skills: List[str]      # must-have skills
    preferred_skills: List[str]     # nice-to-have skills
    min_experience_years: float     # minimum years required
    education_requirement: str      # e.g. "Bachelor's in Computer Science"
    description: str                # full job description text


class PipelineState(TypedDict):
    """
    The GLOBAL STATE passed between all agents in the pipeline.
    Each agent reads from this and writes back to it.
    """
    job_description: JobDescription             # set at the start
    candidates: List[CandidateProfile]          # set by Agent 1
    match_results: List[MatchResult]            # set by YOU (Agent 2)
    ranked_candidates: List[MatchResult]        # set by Agent 3
    report_path: Optional[str]                  # set by Agent 4
    errors: List[str]                           # any errors during pipeline