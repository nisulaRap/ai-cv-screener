# utils/parser_adapter.py

import json
import os
import re
from typing import List
from state.shared_state import CandidateProfile


def parse_experience_years(experience_str: str) -> float:
    """
    Converts Agent 1's experience string into a float number of years.
    Handles formats like '1 year', '2 years', '3+ years', or empty string.

    Args:
        experience_str (str): Raw experience string from Agent 1's output.

    Returns:
        float: Estimated years of experience as a number.
    """
    if not experience_str or experience_str.strip() == "":
        return 0.0

    # Extract first number found in string
    match = re.search(r'(\d+(?:\.\d+)?)', experience_str)
    if match:
        return float(match.group(1))

    return 0.0


def parse_education(education_list: list) -> str:
    """
    Converts Agent 1's education list into a single string.
    Takes the first item as the primary qualification.

    Args:
        education_list (list): List of education strings from Agent 1.

    Returns:
        str: Single education string for the candidate profile.
    """
    if not education_list:
        return "Not specified"

    # First item is usually the degree
    return education_list[0] if education_list else "Not specified"


def load_candidates_from_parsed_json(json_path: str) -> List[CandidateProfile]:
    """
    Reads Agent 1's parsed.json output file and converts each entry
    into a CandidateProfile object compatible with the Job Matcher Agent.

    This is the integration bridge between Agent 1 and Agent 2.

    Args:
        json_path (str): Path to the parsed.json file produced by Agent 1.

    Returns:
        List[CandidateProfile]: List of candidate profiles ready for scoring.

    Raises:
        FileNotFoundError: If the parsed.json file does not exist.
        ValueError: If the JSON file is empty or malformed.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"parsed.json not found at: {json_path}\n"
            "Make sure Agent 1 has run successfully before Agent 2."
        )

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not raw_data:
        raise ValueError("parsed.json is empty. Agent 1 may not have parsed any CVs.")

    candidates: List[CandidateProfile] = []

    for index, entry in enumerate(raw_data):
        candidate: CandidateProfile = {
            # Generate a unique ID from file name
            "candidate_id": f"candidate_{str(index + 1).zfill(3)}",

            # Map full_name → name
            "name": entry.get("full_name", "Unknown Candidate"),

            # Map email directly
            "email": entry.get("email", ""),

            # Skills list maps directly
            "skills": entry.get("skills", []),

            # Convert experience string → float
            "experience_years": parse_experience_years(
                entry.get("years_of_experience", "")
            ),

            # Convert education list → string
            "education": parse_education(
                entry.get("education", [])
            ),

            # Use raw_text as fallback context for LLM
            "raw_text": entry.get("raw_text", "")
        }
        candidates.append(candidate)

    print(f"[Adapter] Loaded {len(candidates)} candidates from {json_path}")
    return candidates