from agents.ranker_agent import run_candidate_ranker

# Fake state simulating what Agent 2 would pass
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

# Run your agent
result = run_candidate_ranker(state)

# Print results
print("\n========== RANKED CANDIDATES ==========")
for c in result["ranked_candidates"]:
    print(f"#{c['rank']} {c['name']} — Score: {c['score']} — {c['status']}")

print("\n========== LOGS ==========")
for log in result["logs"]:
    print(log)

print("\n========== ERRORS ==========")
print(result["errors"] if result["errors"] else "None")