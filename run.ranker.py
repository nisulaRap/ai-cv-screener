"""
Debug runner — tests LLM connection before running the full agent.
Run this first to confirm Ollama is responding properly.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

print("Step 1: Testing Ollama connection...")
try:
    llm = ChatOllama(model="phi3:latest", temperature=0.4)
    response = llm.invoke([HumanMessage(content="Say exactly: LLM IS WORKING")])
    print(f"✅ LLM response: {response.content}")
except Exception as e:
    print(f"❌ LLM connection failed: {e}")
    print("Make sure 'ollama serve' is running in another terminal")
    exit(1)

print("\nStep 2: Running full Candidate Ranker agent...")
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
if result["errors"]:
    for e in result["errors"]:
        print(f"  ❌ {e}")
else:
    print("  None")