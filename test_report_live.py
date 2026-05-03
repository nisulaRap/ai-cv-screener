from agents.report_generator import run_report_generator

# simulates what Agent 3 would pass
fake_state = {
    "job_description_path": "",
    "cv_folder_path": "",
    "candidate_profiles": [],
    "scored_candidates": [],
    "ranked_candidates": [
        {
            "rank": 1,
            "name": "Alice Perera",
            "email": "alice@gmail.com",
            "score": 88,
            "status": "Shortlisted",
            "reasoning": "Alice have strong Python and SQL skill.",
        },
        {
            "rank": 2,
            "name": "Bob Fernando",
            "email": "bob@gmail.com",
            "score": 72,
            "status": "Shortlisted",
            "reasoning": "Good experience with REST APIs and Git.",
        },
        {
            "rank": 3,
            "name": "Chamara Silva",
            "email": "chamara@gmail.com",
            "score": 35,
            "status": "Rejected",
            "reasoning": "Missing most of the required skills.",
        },
    ],
    "report_path": None,
    "logs": [],
    "errors": [],
}

result = run_report_generator(fake_state)

print(f"\n Report generated: {result['report_path']}")
print(f" Logs: {result['logs']}")
if result['errors']:
    print(f" Errors: {result['errors']}")