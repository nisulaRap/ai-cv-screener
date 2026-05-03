# Agent 1 — Document Parser
# Reads every CV file from the folder, extracts structured data,
# and writes candidate_profiles into MASState.

import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.parser_tool import read_all_cvs
from state.shared_state import MASState, CandidateProfile


# Text extraction helpers

def extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s-]{7,}\d)", text)
    return match.group(0).strip() if match else ""


def extract_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        lower = line.lower()
        if not any(word in lower for word in ["email", "phone", "location", "skills", "education"]):
            return line
    return ""


def extract_skills(text: str) -> List[str]:
    common_skills = [
        "Python", "Java", "JavaScript", "React", "Node.js", "Express.js",
        "MongoDB", "MySQL", "SQL", "HTML", "CSS", "Git", "GitHub",
        "Machine Learning", "Data Analysis", "Django", "Flask", "MERN",
        "FastAPI", "Docker", "PostgreSQL", "Redis", "REST APIs",
        "Spring Boot", "TypeScript", "AWS", "Azure", "Kubernetes"
    ]
    found = []
    lower_text = text.lower()
    for skill in common_skills:
        if skill.lower() in lower_text:
            found.append(skill)
    return found


def extract_section(text: str, section_name: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_headers = [
        "skills", "education", "experience", "projects",
        "certifications", "professional summary", "profile",
        "summary", "work experience", "employment history"
    ]
    result = []
    capture = False
    for line in lines:
        clean_line = line.lower().replace(":", "").strip()
        if clean_line == section_name.lower():
            capture = True
            continue
        if capture and clean_line in section_headers:
            break
        if capture:
            result.append(line)
    return result


def extract_job_titles(text: str) -> List[str]:
    role_keywords = ["intern", "developer", "engineer", "analyst", "trainee", "designer", "tester", "consultant"]
    wrong_keywords = ["bsc", "degree", "university", "school", "institute", "summary", "profile", "skills",
                      "education", "project", "certification", "passion", "motivated", "graduation"]
    titles = []
    experience_lines = extract_section(text, "experience")
    for line in experience_lines:
        clean_line = line.strip()
        lower = clean_line.lower()
        if len(clean_line.split()) > 6:
            continue
        if any(wrong in lower for wrong in wrong_keywords):
            continue
        if any(role in lower for role in role_keywords):
            titles.append(clean_line)
    return list(dict.fromkeys(titles))


def extract_years_of_experience(text: str) -> float:
    """Returns a float number of years (0.0 if not found)."""
    lower_text = text.lower()

    # Case 1: "2 years", "3+ years"
    match = re.search(r"(\d+)\+?\s+years?", lower_text)
    if match:
        return float(match.group(1))

    # Case 2: year ranges including "Present"
    matches = re.findall(r"(20\d{2})\s*-\s*(20\d{2}|present)", lower_text)
    total_years = 0
    current_year = datetime.now().year
    for start, end in matches:
        start_yr = int(start)
        end_yr = current_year if end == "present" else int(end)
        if end_yr > start_yr:
            total_years += end_yr - start_yr

    return float(total_years) if total_years > 0 else 0.0


def extract_education(text: str) -> str:
    lines = extract_section(text, "education")
    return lines[0] if lines else "Not specified"


def extract_location(text: str) -> str:
    for line in text.splitlines()[:8]:
        clean_line = line.strip()
        lower = clean_line.lower()
        if lower.startswith("location"):
            return clean_line.replace("Location:", "").strip()
        if "colombo" in lower or "kandy" in lower or "galle" in lower or "matara" in lower:
            return clean_line.replace("Location:", "").strip()
    return ""



# Optional Ollama enrichment (falls back gracefully)

def parse_with_ollama(text: str, model: str = "llama3:8b") -> Dict[str, Any]:
    import requests
    prompt = f"""
You are a CV Document Parser Agent.

Extract candidate details from the CV text below.

Return ONLY valid JSON with this exact structure:
{{
  "full_name": "",
  "email": "",
  "phone": "",
  "skills": [],
  "education": [],
  "experience": [],
  "projects": [],
  "certifications": [],
  "job_titles": [],
  "years_of_experience": "",
  "location": ""
}}

CV Text:
{text}
"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError("Ollama request failed")

    result = response.json()["response"].strip()

    if "```json" in result:
        result = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
        result = result.split("```")[1].split("```")[0].strip()
    elif "{" in result and "}" in result:
        result = result[result.find("{"):result.rfind("}") + 1]

    # Remove JS-style comments
    result = re.sub(r"//.*", "", result)

    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"error": "Ollama did not return valid JSON", "raw_output": result}


# Parse a single CV file dict into a CandidateProfile

def parse_single_cv(cv: Dict[str, Any], index: int) -> CandidateProfile:
    """
    Parse one CV dict (with 'file_name' and 'text') into a CandidateProfile.
    Tries Ollama first; falls back to rule-based extraction on any failure.
    """
    text = cv["text"]

    # Always build the rule-based result as a safe fallback
    rule_based: CandidateProfile = {
        "candidate_id": f"candidate_{str(index + 1).zfill(3)}",
        "name": extract_name(text) or f"Candidate {index + 1}",
        "email": extract_email(text),
        "skills": extract_skills(text),
        "experience_years": extract_years_of_experience(text),
        "education": extract_education(text),
        "raw_text": text,
    }

    try:
        ai_result = parse_with_ollama(text)

        if "error" in ai_result:
            return rule_based

        # Map Ollama output → CandidateProfile
        experience_str = ai_result.get("years_of_experience", "")
        experience_years = rule_based["experience_years"]
        if experience_str:
            m = re.search(r"(\d+(?:\.\d+)?)", str(experience_str))
            if m:
                experience_years = float(m.group(1))

        education_list = ai_result.get("education", [])
        education_str = education_list[0] if education_list else rule_based["education"]

        return {
            "candidate_id": rule_based["candidate_id"],
            "name": ai_result.get("full_name") or rule_based["name"],
            "email": ai_result.get("email") or rule_based["email"],
            "skills": ai_result.get("skills") or rule_based["skills"],
            "experience_years": experience_years,
            "education": education_str,
            "raw_text": text,
        }

    except Exception:
        # Ollama not running or timed out — rule-based is perfectly fine
        return rule_based


# Standalone runner (used by the LangGraph node below)

def run_parser_agent(
    cv_folder: str = "data/cvs",
    output_path: str = "outputs/parsed.json"
) -> List[CandidateProfile]:
    """
    Reads all CV files from cv_folder, parses each one into a CandidateProfile,
    saves a JSON snapshot to output_path, and returns the list of profiles.
    """
    cvs = read_all_cvs(cv_folder)
    profiles: List[CandidateProfile] = []

    for index, cv in enumerate(cvs):
        profile = parse_single_cv(cv, index)
        profiles.append(profile)
        print(f"  ✔ Parsed: {cv['file_name']} → {profile['name']}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4)

    print(f"\n[Parser] Saved {len(profiles)} profiles to {output_path}")
    return profiles


# LangGraph node entry point

def run_document_parser(state: MASState) -> MASState:
    """
    Agent 1 LangGraph node — Document Parser.

    Reads cv_folder_path from state, parses every CV file,
    and writes the resulting CandidateProfile list to state["candidate_profiles"].

    Args:
        state (MASState): The global pipeline state.

    Returns:
        MASState: Updated state with candidate_profiles populated.
    """
    print("\n" + "=" * 60)
    print(" Agent 1 — Document Parser starting...")
    print("=" * 60)

    cv_folder = state.get("cv_folder_path", "data/cvs")

    try:
        profiles = run_parser_agent(
            cv_folder=cv_folder,
            output_path="outputs/parsed.json"
        )
        state["candidate_profiles"] = profiles
        state.setdefault("logs", []).append(
            f"DocumentParser: Parsed {len(profiles)} CV(s) from '{cv_folder}'"
        )
        print(f"\n Agent 1 complete — {len(profiles)} candidate(s) parsed.")

    except (FileNotFoundError, ValueError) as e:
        error_msg = f"DocumentParser failed: {e}"
        state.setdefault("errors", []).append(error_msg)
        state["candidate_profiles"] = []
        print(f"\n {error_msg}")

    return state


# Standalone test

if __name__ == "__main__":
    results = run_parser_agent()
    print(json.dumps(results, indent=4))