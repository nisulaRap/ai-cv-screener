from typing import TypedDict, List, Optional, Any

# Data-contract TypedDicts (shared by all agents)

class CandidateProfile(TypedDict, total=False):
    """
    Output from Agent 1 (Document Parser).
    Represents a single parsed candidate CV.
    """
    candidate_id: str        
    name: str                
    email: str               
    skills: List[str]       
    experience_years: float  
    education: str           
    raw_text: str            


class MatchResult(TypedDict, total=False):
    """
    Output from Agent 2 (Job Matcher).
    Represents the scoring result for one candidate.
    """
    candidate_id: str         
    name: str                 
    email: str                
    score: float              
    reasoning: str            
    matched_skills: List[str] 
    missing_skills: List[str] 
    status: str               


class RankedCandidate(TypedDict, total=False):
    """
    Output from Agent 3 (Candidate Ranker).
    Extends MatchResult with rank and final status.
    """
    rank: int
    name: str
    email: str
    score: float
    status: str      # "Shortlisted" or "Rejected"
    reasoning: str


class JobDescription(TypedDict, total=False):
    """
    The job posting HR provides as input.
    Loaded from data/job_description.json at pipeline start.
    """
    job_id: str             
    title: str               
    required_skills: List[str]      
    preferred_skills: List[str]      
    min_experience_years: float     
    education_requirement: str       
    description: str                 


# Unified Pipeline State (passed between ALL agents)

class MASState(TypedDict, total=False):
    """
    The GLOBAL STATE passed between all agents in the LangGraph pipeline.

    Flow:
        Agent 1 (parser_agent)      → populates candidate_profiles
        Agent 2 (job_matcher_agent) → populates match_results
        Agent 3 (ranker_agent)      → populates ranked_candidates + executive_summary
        Agent 4 (report_generator)  → populates report_path

    Attributes:
        job_description_path:  Path to the job description JSON file (set at startup)
        cv_folder_path:        Path to the folder containing CV files (set at startup)
        job_description:       Loaded job description dict (set at startup or Agent 1)
        candidate_profiles:    List of parsed candidate profiles from Agent 1
        match_results:         List of scored candidates from Agent 2
        ranked_candidates:     Ranked + labelled list from Agent 3
        executive_summary:     HR executive summary text from Agent 3
        report_path:           Path to the generated HTML report from Agent 4
        logs:                  Shared list of log messages across all agents
        errors:                Shared list of error messages across all agents
    """
    job_description_path: str
    cv_folder_path: str
    job_description: JobDescription
    candidate_profiles: List[Any]
    match_results: List[Any]
    ranked_candidates: List[RankedCandidate]
    executive_summary: Optional[str]
    report_path: Optional[str]
    logs: List[str]
    errors: List[str]