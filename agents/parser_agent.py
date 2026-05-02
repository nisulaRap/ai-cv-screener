import requests
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from tools.parser_tool import read_all_cvs


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
        "Machine Learning", "Data Analysis", "Django", "Flask", "MERN"
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
    role_keywords = [
        "intern", "developer", "engineer", "analyst",
        "trainee", "designer", "tester", "consultant"
    ]

    wrong_keywords = [
        "bsc", "degree", "university", "school", "institute",
        "summary", "profile", "skills", "education", "project",
        "certification", "passion", "motivated", "graduation"
    ]

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


def extract_years_of_experience(text: str) -> str:
    lower_text = text.lower()

    # Case 1: "2 years", "3+ years"
    match = re.search(r"(\d+)\+?\s+years?", lower_text)
    if match:
        years = int(match.group(1))
        return f"{years} year" if years == 1 else f"{years} years"

    # Case 2: year ranges including "Present"
    matches = re.findall(r"(20\d{2})\s*-\s*(20\d{2}|present)", lower_text)

    total_years = 0
    current_year = datetime.now().year

    for start, end in matches:
        start = int(start)
        end = current_year if end == "present" else int(end)

        if end > start:
            total_years += end - start

    if total_years > 0:
        return f"{total_years} year" if total_years == 1 else f"{total_years} years"

    return ""


def extract_location(text: str) -> str:
    for line in text.splitlines()[:8]:
        clean_line = line.strip()
        lower = clean_line.lower()

        if lower.startswith("location"):
            return clean_line.replace("Location:", "").strip()

        if "colombo" in lower or "kandy" in lower or "galle" in lower or "matara" in lower:
            return clean_line.replace("Location:", "").strip()

    return ""


def parse_with_ollama(text: str, model: str = "llama3") -> Dict[str, Any]:
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
    json={
        "model": model,
        "prompt": prompt,
        "stream": False
    },
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

    try:
        import re

        # remove comments like // ...
        result = re.sub(r"//.*", "", result)

        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "error": "Ollama did not return valid JSON",
            "raw_output": result
        }


def parse_single_cv(cv: Dict[str, Any]) -> Dict[str, Any]:
    text = cv["text"]

    rule_based_result = {
        "file_name": cv["file_name"],
        "full_name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "education": extract_section(text, "education"),
        "experience": extract_section(text, "experience"),
        "projects": extract_section(text, "projects"),
        "certifications": extract_section(text, "certifications"),
        "job_titles": extract_job_titles(text),
        "years_of_experience": extract_years_of_experience(text),
        "location": extract_location(text),
        "raw_text": text
    }

    try:
        ai_result = parse_with_ollama(text)

        if "error" in ai_result:
            rule_based_result["parser_type"] = "rule_based_fallback"
            rule_based_result["ai_error"] = ai_result["raw_output"]
            return rule_based_result

        ai_result["file_name"] = cv["file_name"]
        ai_result["raw_text"] = text
        ai_result["parser_type"] = "ollama_ai"
        if not ai_result.get("years_of_experience"):
            ai_result["years_of_experience"] = extract_years_of_experience(text)
        return ai_result

    except Exception as e:
        rule_based_result["parser_type"] = "rule_based_fallback"
        rule_based_result["ai_error"] = str(e)
        return rule_based_result


def run_parser_agent(
    cv_folder: str = "data/cvs",
    output_path: str = "outputs/parsed.json"
) -> List[Dict[str, Any]]:
    cvs = read_all_cvs(cv_folder)

    parsed_results = []

    for cv in cvs:
        parsed_results.append(parse_single_cv(cv))

    Path("outputs").mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(parsed_results, file, indent=4)

    return parsed_results


if __name__ == "__main__":
    results = run_parser_agent()
    print(json.dumps(results, indent=4))