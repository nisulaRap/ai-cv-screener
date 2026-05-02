import json
import re
import sys
import os
from typing import Dict, Any

# Make sure imports work from any working directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_ollama import OllamaLLM
from database.db_manager import save_match_result
from logs.agent_log import (
    log_tool_call,
    log_llm_prompt,
    log_llm_response,
    log_score_result,
    log_tool_error
)
from state.shared_state import CandidateProfile, JobDescription, MatchResult


# Initialize the Ollama LLM once (reused across all calls)
llm = OllamaLLM(model="llama3:8b", temperature=0.1)


def build_scoring_prompt(candidate: CandidateProfile, job: JobDescription) -> str:
    """
    Builds a structured prompt for the LLM to score a candidate against a job description.
    The prompt is carefully engineered to force valid JSON output from the local SLM.

    Args:
        candidate (CandidateProfile): The parsed candidate profile from Agent 1.
        job (JobDescription): The job description provided by HR.

    Returns:
        str: The fully formatted prompt string to send to Ollama.
    """
    return f"""You are an expert HR analyst. Your job is to evaluate how well a candidate matches a job description.

IMPORTANT: You MUST respond with ONLY a valid JSON object. No explanations, no extra text, no markdown, no code blocks. Just the raw JSON.

JOB DESCRIPTION:
- Title: {job['title']}
- Required Skills: {', '.join(job['required_skills'])}
- Preferred Skills: {', '.join(job['preferred_skills'])}
- Minimum Experience: {job['min_experience_years']} years
- Education Requirement: {job['education_requirement']}
- Description: {job['description']}

CANDIDATE PROFILE:
- Name: {candidate['name']}
- Skills: {', '.join(candidate['skills'])}
- Experience: {candidate['experience_years']} years
- Education: {candidate['education']}

SCORING RULES:
1. Score range is 0 to 100 (integer only)
2. Required skills match = up to 60 points
3. Experience match = up to 20 points
4. Education match = up to 10 points
5. Preferred skills match = up to 10 points

Respond ONLY with this exact JSON format:
{{
    "score": <integer 0-100>,
    "reasoning": "<2-3 sentences explaining the score>",
    "matched_skills": ["<skill1>", "<skill2>"],
    "missing_skills": ["<skill1>", "<skill2>"]
}}"""


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """
    Safely extracts and parses JSON from the LLM response.
    Handles cases where the LLM adds extra text around the JSON.

    Args:
        response (str): The raw string response from the Ollama LLM.

    Returns:
        Dict[str, Any]: Parsed JSON as a Python dictionary.

    Raises:
        ValueError: If no valid JSON could be extracted from the response.
    """
    # First try direct parse
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting JSON block using regex
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response: {response[:200]}")


def validate_score_output(data: Dict[str, Any]) -> None:
    """
    Validates that the LLM output contains all required fields with correct types.

    Args:
        data (Dict[str, Any]): The parsed JSON output from the LLM.

    Returns:
        None

    Raises:
        ValueError: If any required field is missing or has an invalid type/value.
    """
    required_fields = ["score", "reasoning", "matched_skills", "missing_skills"]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field in LLM output: '{field}'")

    if not isinstance(data["score"], (int, float)):
        raise ValueError(f"Score must be a number, got: {type(data['score'])}")

    if not (0 <= data["score"] <= 100):
        raise ValueError(f"Score must be between 0 and 100, got: {data['score']}")

    if not isinstance(data["reasoning"], str) or len(data["reasoning"].strip()) == 0:
        raise ValueError("Reasoning must be a non-empty string.")

    if not isinstance(data["matched_skills"], list):
        raise ValueError("matched_skills must be a list.")

    if not isinstance(data["missing_skills"], list):
        raise ValueError("missing_skills must be a list.")


def score_candidate(
    candidate: CandidateProfile,
    job: JobDescription
) -> MatchResult:
    """
    Main tool function. Scores a single candidate against a job description
    using the local Ollama LLM, validates the output, saves it to the database,
    and returns a structured MatchResult.

    This is the primary tool used by the Job Matcher Agent.

    Args:
        candidate (CandidateProfile): Structured candidate data from Agent 1.
        job (JobDescription): The job description provided by HR.

    Returns:
        MatchResult: A fully populated match result including score, reasoning,
                     matched/missing skills, and a default status of 'Pending'.

    Raises:
        RuntimeError: If the LLM fails to return valid output after all retries.
    """
    candidate_id = candidate["candidate_id"]
    candidate_name = candidate["name"]

    # Log the tool being called
    log_tool_call(candidate_id, candidate_name)

    # Early return for empty candidate — no skills, no experience, no education
    if not candidate.get("skills") and not candidate.get("education") and candidate.get("experience_years", 0) == 0:
        empty_result: MatchResult = {
            "candidate_id": candidate_id,
            "name": candidate_name,
            "score": 0.0,
            "reasoning": "Candidate profile is empty. No skills, experience, or education provided.",
            "matched_skills": [],
            "missing_skills": [],
            "status": "Pending"
        }
        save_match_result(empty_result, job["job_id"])
        log_score_result(candidate_id, candidate_name, 0.0, [])
        return empty_result

    # Build the prompt
    prompt = build_scoring_prompt(candidate, job)
    log_llm_prompt(candidate_id, prompt)

    # Retry logic — local SLMs can occasionally produce bad output
    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            # Call Ollama
            raw_response = llm.invoke(prompt)
            log_llm_response(candidate_id, raw_response)

            # Parse and validate
            parsed = extract_json_from_response(raw_response)
            validate_score_output(parsed)

            # Build MatchResult
            result: MatchResult = {
                "candidate_id": candidate_id,
                "name": candidate_name,
                "score": float(parsed["score"]),
                "reasoning": parsed["reasoning"].strip(),
                "matched_skills": parsed["matched_skills"],
                "missing_skills": parsed["missing_skills"],
                "status": "Pending"  # Agent 3 will set this to Shortlisted/Rejected
            }

            # Save to database
            save_match_result(result, job["job_id"])

            # Log the result
            log_score_result(candidate_id, candidate_name, result["score"], result["matched_skills"])


            # Add confidence flag based on score clarity
            if parsed["score"] >= 75:
                result["status"] = "Pending"   # high confidence match
            elif parsed["score"] >= 40:
                result["status"] = "Pending"   # borderline
            else:
                result["status"] = "Pending"   # clear rejection
            
            # Add confidence metadata to reasoning
            confidence = "HIGH" if len(parsed["matched_skills"]) >= 3 else "LOW"
            result["reasoning"] = f"[Confidence: {confidence}] {result['reasoning']}"

            return result

        except Exception as e:
            last_error = str(e)
            log_tool_error(candidate_id, f"Attempt {attempt} failed: {last_error}")

    # All retries failed
    raise RuntimeError(
        f"Failed to score candidate '{candidate_name}' after {max_retries} attempts. "
        f"Last error: {last_error}"
    )