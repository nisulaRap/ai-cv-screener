import pytest
from pathlib import Path
from unittest.mock import patch, call
from agents.report_generator import run_report_generator
from state.shared_state import MASState

def make_state(candidates: list = None) -> MASState:
    return {
        "job_description_path": "",
        "cv_folder_path": "",
        "candidate_profiles": [],
        "scored_candidates": [],
        "ranked_candidates": candidates or [
            {
                "rank": 1, "name": "Alice Perera",
                "email": "alice@test.com",
                "score": 80.0,
                "status": "Shortlisted",
                "reasoning": "Strong Python and SQL skills.",
            },
            {
                "rank": 2, "name": "Bob Fernando",
                "email": "bob@test.com",
                "score": 45.0,
                "status": "Rejected",
                "reasoning": "Missing key required skills.",
            },
        ],
        "executive_summary": "2 of 3 candidates shortlisted. Top candidate shows strong technical alignment.",  # ← NEW
        "report_path": None,
        "logs": [],
        "errors": [],
    }


# Report file must be created

@patch("agents.report_generator.grammar_check")
def test_report_file_is_created(mock_grammar):
    """Agent 4 must write the HTML file to the output directory."""
    mock_grammar.return_value = {
        "corrected_text": "Strong Python and SQL skills.",
        "issues_found": 0,
        "matches": [],
    }
    result = run_report_generator(make_state())

    assert result["report_path"] is not None, "report_path must be set in state"
    assert Path(result["report_path"]).exists(), "HTML file must exist on disk"


# Report must contain all candidate names

@patch("agents.report_generator.grammar_check")
def test_report_contains_all_candidate_names(mock_grammar):
    """Every candidate's name must appear in the generated HTML."""
    mock_grammar.return_value = {"corrected_text": "", "issues_found": 0, "matches": []}
    result = run_report_generator(make_state())

    html = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Alice Perera" in html
    assert "Bob Fernando" in html


# Shortlisted/Rejected labels must be correct

@patch("agents.report_generator.grammar_check")
def test_report_has_correct_status_labels(mock_grammar):
    """HTML must contain 'Shortlisted' and 'Rejected' CSS classes for correct candidates."""
    mock_grammar.return_value = {"corrected_text": "", "issues_found": 0, "matches": []}
    result = run_report_generator(make_state())

    html = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "pill-shortlisted" in html
    assert "pill-rejected" in html


# Grammar check tool must always be called 

@patch("agents.report_generator.grammar_check")
def test_grammar_check_tool_is_called(mock_grammar):
    """Agent 4 must invoke the grammar_check tool at least once per run."""
    mock_grammar.return_value = {"corrected_text": "", "issues_found": 0, "matches": []}
    run_report_generator(make_state())

    assert mock_grammar.called, "grammar_check must be called by the agent"


# Graceful fallback when grammar API fails

@patch("agents.report_generator.grammar_check", side_effect=RuntimeError("API timeout"))
def test_report_generated_even_if_grammar_api_fails(mock_grammar):
    """Report must still be created if LanguageTool API is unavailable."""
    result = run_report_generator(make_state())

    assert result["report_path"] is not None
    assert Path(result["report_path"]).exists()
    assert any("Grammar check skipped" in e for e in result["errors"])


# Scores must appear in the HTML

@patch("agents.report_generator.grammar_check")
def test_report_contains_scores(mock_grammar):
    """Candidate scores (e.g. 88, 45) must appear in the HTML output."""
    mock_grammar.return_value = {"corrected_text": "", "issues_found": 0, "matches": []}
    result = run_report_generator(make_state())

    html = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "88" in html
    assert "45" in html


# Empty candidate list edge case

@patch("agents.report_generator.grammar_check")
def test_report_handles_empty_candidate_list(mock_grammar):
    """Agent 4 must not crash when there are zero ranked candidates."""
    mock_grammar.return_value = {"corrected_text": "", "issues_found": 0, "matches": []}
    result = run_report_generator(make_state(candidates=[]))

    assert result["report_path"] is not None
    assert Path(result["report_path"]).exists()

# Test for executive summary

@patch("agents.report_generator.grammar_check")
def test_report_contains_executive_summary(mock_grammar):
    """Executive summary from Agent 3 must appear in the HTML report."""
    mock_grammar.return_value = {"corrected_text": "", "issues_found": 0, "matches": []}
    result = run_report_generator(make_state())

    html = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Executive Summary" in html
    assert "2 of 3 candidates shortlisted" in html