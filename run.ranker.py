"""
Debug runner — tests LLM connection then runs the full Candidate Ranker agent
using the same data format that Agent 2 (Job Matcher) produces.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


print("Step 1: Testing Ollama connection with llama3:8b...")
try:
    llm = ChatOllama(model="llama3:8b", temperature=0.4)
    response = llm.invoke([HumanMessage(content="Reply with exactly: LLM IS WORKING")])
    print(f" LLM response: {response.content}\n")
except Exception as e:
    print(f" LLM connection failed: {e}")
    print("Make sure 'ollama serve' is running in a separate terminal")
    exit(1)

print("Step 2: Running Candidate Ranker with Agent 2 real data format...\n")

from agents.ranker_agent import run_candidate_ranker

# This matches exactly what Agent 2 produces based on the job_matcher.log
state = {
    "job_description_path": "data/job.json",
    "cv_folder_path": "data/cvs",
    "candidate_profiles": [],
    "match_results": [
        {
            "name": "Alice Fernando",
            "score": 80.0,
            "reasoning": "The candidate has a strong match for required skills, with all of them being present. However, the experience and education do not fully align with the job description's requirements.",
            "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs", "SQL"],
            "missing_skills": [],
        },
        {
            "name": "Bob Perera",
            "score": 40.0,
            "reasoning": "The candidate has experience and education matching some of the required skills, but lacks Python and REST APIs expertise.",
            "matched_skills": ["Git"],
            "missing_skills": ["Python", "REST APIs"],
        },
        {
            "name": "Chamari Silva",
            "score": 50.0,
            "reasoning": "The candidate has a good match for required skills, but lacks experience and preferred skills. Chamari's experience is below the minimum requirement.",
            "matched_skills": ["Python", "SQL", "Git", "REST APIs"],
            "missing_skills": ["Docker", "PostgreSQL", "Redis"],
        },
        {
            "name": "David Rajapaksa",
            "score": 80.0,
            "reasoning": "The candidate has a strong match for required skills, with all of them being present. The education matches perfectly as it is a Master's degree.",
            "matched_skills": ["Python", "FastAPI", "Docker", "Redis", "PostgreSQL", "SQL", "Git", "REST APIs"],
            "missing_skills": [],
        },
        {
            "name": "Emma Wickramasinghe",
            "score": 0.0,
            "reasoning": "The candidate does not meet any of the required skills, experience, or education requirements.",
            "matched_skills": [],
            "missing_skills": ["Python", "REST APIs", "SQL", "Git"],
        },
    ],
    "scored_candidates": [],
    "ranked_candidates": [],
    "report_path": None,
    "logs": [],
    "errors": [],
}

result = run_candidate_ranker(state)

# Step 3 — Print results
print("\n========== RANKED CANDIDATES ==========")
for c in result["ranked_candidates"]:
    print(f"\n#{c['rank']} {c['name']} — Score: {c['score']} — {c['status']}")
    print(f"    LLM Reasoning: {c['reasoning']}")

print("\n========== EXECUTIVE SUMMARY ==========")
print(result.get("executive_summary", "No summary generated."))

print("\n========== LOGS ==========")
for log in result["logs"]:
    print(f"  {log}")

print("\n========== ERRORS ==========")
if result["errors"]:
    for e in result["errors"]:
        print(f"[ERROR] {e}")
else:
    print("[OK] No errors")