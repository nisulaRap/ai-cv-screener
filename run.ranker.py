from agents.ranker_agent import run_candidate_ranker

state = {
    "job_description_path": "data/job.json",
    "cv_folder_path": "data/cvs",
    "candidate_profiles": [],
    "scored_candidates": [
        {"name": "Alice",  "email": "alice@gmail.com",  "score": 91.0, "reasoning": "Strong Python and ML skills."},
        {"name": "Bob",    "email": "bob@gmail.com",    "score": 78.5, "reasoning": "Good experience, missing some tools."},
        {"name": "Carol",  "email": "carol@gmail.com",  "score": 85.0, "reasoning": "Excellent communication and backend skills."},
        {"name": "David",  "email": "david@gmail.com",  "score": 60.0, "reasoning": "Junior level, lacks required experience."},
        {"name": "Eve",    "email": "eve@gmail.com",    "score": 45.0, "reasoning": "Not enough relevant skills."},
    ],
    "ranked_candidates": [],
    "report_path": None,
    "logs": [],
    "errors": [],
}

result = run_candidate_ranker(state)

print("\n========== RANKED CANDIDATES ==========")
for c in result["ranked_candidates"]:
    print(f"\n#{c['rank']} {c['name']} — Score: {c['score']} — {c['status']}")
    print(f"    Reasoning: {c['reasoning']}")

print("\n========== EXECUTIVE SUMMARY ==========")
print(result.get("executive_summary", "No summary generated."))

print("\n========== ERRORS ==========")
print(result["errors"] if result["errors"] else "None")