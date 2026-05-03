# main.py
# Entry point for the AI CV Screener Multi-Agent System.
#
# Pipeline (sequential LangGraph nodes):
#   Agent 1: Document Parser    — reads CVs → candidate_profiles
#   Agent 2: Job Matcher        — scores profiles → match_results (+ DB)
#   Agent 3: Candidate Ranker   — sorts & labels → ranked_candidates
#   Agent 4: Report Generator   — grammar-checks & writes HTML report

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langgraph.graph import StateGraph, END

from state.shared_state import MASState
from agents.parser_agent      import run_document_parser
from agents.job_matcher_agent import run_job_matcher_agent
from agents.ranker_agent      import run_candidate_ranker
from agents.report_generator  import run_report_generator

# Build the 4-node LangGraph pipeline
def build_pipeline() -> StateGraph:
    """
    Assembles and compiles the full MAS pipeline as a LangGraph StateGraph.

    Nodes (in order):
        parser_agent      → Agent 1: Document Parser
        job_matcher       → Agent 2: Job Matcher
        candidate_ranker  → Agent 3: Candidate Ranker
        report_generator  → Agent 4: Report Generator

    Returns:
        Compiled LangGraph app ready to invoke.
    """
    graph = StateGraph(MASState)

    # Register all four agents as nodes
    graph.add_node("parser_agent",     run_document_parser)
    graph.add_node("job_matcher",      run_job_matcher_agent)
    graph.add_node("candidate_ranker", run_candidate_ranker)
    graph.add_node("report_generator", run_report_generator)

    # Wire them sequentially
    graph.set_entry_point("parser_agent")
    graph.add_edge("parser_agent", "job_matcher")
    graph.add_edge("job_matcher", "candidate_ranker")
    graph.add_edge("candidate_ranker", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


# Load job description from JSON
def load_job_description(path: str) -> dict:
    """
    Loads the job description from a JSON file.

    Args:
        path: Path to job_description.json

    Returns:
        Parsed job description dict.

    Raises:
        SystemExit: If the file is missing or malformed.
    """
    abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(abs_path):
        print(f" Job description file not found: {abs_path}")
        print(" Create data/job_description.json before running the pipeline.")
        sys.exit(1)

    with open(abs_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f" Malformed JSON in {abs_path}: {e}")
            sys.exit(1)


# Run the pipeline
def run_pipeline(
    job_description_path: str = "data/job_description.json",
    cv_folder_path: str = "data/cvs",
) -> MASState:
    """
    Runs the full 4-agent CV screener pipeline end-to-end.

    Steps:
        1. Load job description from JSON.
        2. Build the LangGraph pipeline.
        3. Invoke with initial MASState.
        4. Print summary of results.

    Args:
        job_description_path: Relative path to the job description JSON.
        cv_folder_path:        Relative path to the folder containing CV files.

    Returns:
        The final MASState after all agents have run.
    """
    print("\n" + "=" * 60)
    print("AI CV Screener — Multi-Agent System")
    print("=" * 60)

    job_description = load_job_description(job_description_path)
    print(f"\n Job Title   : {job_description.get('title', 'N/A')}")
    print(f" CV Folder   : {cv_folder_path}")
    print(f" Job ID      : {job_description.get('job_id', 'N/A')}")

    initial_state: MASState = {
        "job_description_path": job_description_path,
        "cv_folder_path":       cv_folder_path,
        "job_description":      job_description,
        "candidate_profiles":   [],
        "match_results":        [],
        "ranked_candidates":    [],
        "executive_summary":    None,
        "report_path":          None,
        "logs":                 [],
        "errors":               [],
    }

    print("\n Building pipeline...")
    app = build_pipeline()

    print(" Running agents...\n")
    final_state: MASState = app.invoke(initial_state)

    # Summary
    print("\n" + "=" * 60)
    print(" Pipeline Complete!")
    print("=" * 60)

    n_parsed  = len(final_state.get("candidate_profiles", []))
    n_scored  = len(final_state.get("match_results", []))
    n_ranked  = len(final_state.get("ranked_candidates", []))
    n_short   = sum(
        1 for c in final_state.get("ranked_candidates", [])
        if c.get("status") == "Shortlisted"
    )
    report    = final_state.get("report_path")

    print(f"\n CVs parsed        : {n_parsed}")
    print(f" Candidates scored : {n_scored}")
    print(f" Candidates ranked : {n_ranked}")
    print(f" Shortlisted       : {n_short}")
    print(f" Rejected          : {n_ranked - n_short}")

    if report:
        abs_report = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), report)
        )
        print(f"\n Report saved to   : {abs_report}")
    else:
        print("\n Report was NOT generated — check errors below.")

    if final_state.get("executive_summary"):
        print(f"\n Executive Summary:\n  {final_state['executive_summary']}")

    if final_state.get("logs"):
        print("\n Agent Logs:")
        for log in final_state["logs"]:
            print(f"        • {log}")

    if final_state.get("errors"):
        print("\n Errors encountered:")
        for err in final_state["errors"]:
            print(f"        • {err}")

    print("\n" + "=" * 60 + "\n")
    return final_state

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AI CV Screener — 4-agent MAS pipeline"
    )
    parser.add_argument(
        "--job",
        default="data/job_description.json",
        help="Path to the job description JSON file (default: data/job_description.json)",
    )
    parser.add_argument(
        "--cvs",
        default="data/cvs",
        help="Path to the folder containing CV files (default: data/cvs)",
    )
    args = parser.parse_args()

    run_pipeline(
        job_description_path=args.job,
        cv_folder_path=args.cvs,
    )


if __name__ == "__main__":
    main()
