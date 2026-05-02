from typing import TypedDict, List, Optional, Any


class RankedCandidate(TypedDict, total=False):
    """Represents a ranked candidate with all possible fields."""
    rank: int
    name: str
    email: str
    score: float
    status: str
    reasoning: str
 

class MASState(TypedDict):
    """
    Shared state for the MAS pipeline.
    
    Attributes:
        job_description_path: Path to the job description file
        cv_folder_path: Path to the CV folder
        candidate_profiles: List of parsed candidate profiles
        scored_candidates: List of candidates with scores
        ranked_candidates: List of ranked candidates with status
        report_path: Path to the generated report
        logs: List of log messages
        errors: List of error messages
    """
    job_description_path: str
    cv_folder_path: str
    candidate_profiles: List[Any]
    scored_candidates: List[Any]
    ranked_candidates: List[RankedCandidate]
    report_path: Optional[str]
    logs: List[str]
    errors: List[str]