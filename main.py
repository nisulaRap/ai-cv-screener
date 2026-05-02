"""
Main entry point — CV Screener MAS
Runs the full pipeline: Parser Agent → Report Generator Agent
"""
from langgraph.graph import StateGraph, END
from state.shared_state import MASState
#from agents.parser_agent import run_document_parser
from agents.report_generator import run_report_generator


def build_graph():
    """Build the LangGraph pipeline connecting the agents."""
    graph = StateGraph(MASState)

    graph.add_node("parser_agent", run_document_parser)
    graph.add_node("report_generator", run_report_generator)

    graph.set_entry_point("parser_agent")
    graph.add_edge("parser_agent", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


def main():
    initial_state: MASState = {
        "job_description_path": "data/job_description.json",
        "cv_folder_path": "data/cvs",
        "candidate_profiles": None,
        "scored_candidates": None,
        "ranked_candidates": None,
        "executive_summary": None,
        "report_path": None,
        "logs": [],
        "errors": [],
    }

    print("🚀 Starting CV Screener MAS...")
    app = build_graph()
    final_state = app.invoke(initial_state)

    print("\n✅ Pipeline Complete!")
    print(f"📄 Report: {final_state['report_path']}")

    if final_state.get("ranked_candidates"):
        print(f"👥 Candidates processed: {len(final_state['ranked_candidates'])}")

    print("\n📝 Agent Logs:")
    for log in final_state["logs"]:
        print(f"  • {log}")

    if final_state["errors"]:
        print("\n⚠️  Errors:")
        for err in final_state["errors"]:
            print(f"  • {err}")


if __name__ == "__main__":
    main()