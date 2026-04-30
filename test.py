"""
Test suite for Agent 3 — Candidate Ranker.

Tests both the ranker_tool (unit tests) and the run_candidate_ranker
agent node (integration tests), covering happy paths, edge cases,
and error handling as required by the assignment rubric.

Run with:
    pytest test_ranker.py -v
"""

import pytest
from ranker_tool import ranker_tool
from ranker_agent import run_candidate_ranker


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_candidates() -> list[dict]:
    """Five candidates with distinct scores for standard ranking tests."""
    return [
        {"name": "Alice",   "email": "alice@example.com",   "score": 87.5, "reasoning": "Strong Python and ML skills."},
        {"name": "Bob",     "email": "bob@example.com",     "score": 62.0, "reasoning": "Some relevant experience."},
        {"name": "Carol",   "email": "carol@example.com",   "score": 91.0, "reasoning": "Excellent overall match."},
        {"name": "David",   "email": "david@example.com",   "score": 45.0, "reasoning": "Junior level, lacks experience."},
        {"name": "Eve",     "email": "eve@example.com",     "score": 78.0, "reasoning": "Good skills, missing key tool."},
    ]


@pytest.fixture
def base_state(sample_candidates) -> dict:
    """Minimal MASState for agent node tests."""
    return {
        "job_description_path": "job.json",
        "cv_folder_path":       "cvs/",
        "candidate_profiles":   [],
        "scored_candidates":    sample_candidates,
        "ranked_candidates":    [],
        "report_path":          None,
        "logs":                 [],
        "errors":               [],
    }


# ===========================================================================
# UNIT TESTS — ranker_tool
# ===========================================================================

class TestRankerToolHappyPath:

    def test_returns_correct_number_of_candidates(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        assert len(result) == len(sample_candidates)

    def test_sorted_by_score_descending(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        scores = [c["score"] for c in result]
        assert scores == sorted(scores, reverse=True)

    def test_top_3_are_shortlisted_by_default(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        shortlisted = [c for c in result if c["status"] == "Shortlisted"]
        assert len(shortlisted) == 3

    def test_rest_are_rejected(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        rejected = [c for c in result if c["status"] == "Rejected"]
        assert len(rejected) == len(sample_candidates) - 3

    def test_rank_starts_at_1(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        assert result[0]["rank"] == 1

    def test_ranks_are_sequential(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        ranks = [c["rank"] for c in result]
        assert ranks == list(range(1, len(sample_candidates) + 1))

    def test_highest_score_is_rank_1(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        assert result[0]["name"] == "Carol"   # score 91.0

    def test_correct_candidate_names_preserved(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        names = {c["name"] for c in result}
        expected = {c["name"] for c in sample_candidates}
        assert names == expected

    def test_reasoning_carried_over(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        for candidate in result:
            assert "reasoning" in candidate
            assert isinstance(candidate["reasoning"], str)

    def test_output_fields_complete(self, sample_candidates):
        result = ranker_tool(sample_candidates)
        required_fields = {"rank", "name", "email", "score", "status", "reasoning"}
        for candidate in result:
            assert required_fields == set(candidate.keys())

    def test_custom_top_n(self, sample_candidates):
        result = ranker_tool(sample_candidates, top_n=1)
        shortlisted = [c for c in result if c["status"] == "Shortlisted"]
        assert len(shortlisted) == 1
        assert result[0]["status"] == "Shortlisted"

    def test_status_values_are_correctly_capitalised(self, sample_candidates):
        """Status must be 'Shortlisted'/'Rejected' — not uppercase — for Agent 4."""
        result = ranker_tool(sample_candidates)
        for c in result:
            assert c["status"] in ("Shortlisted", "Rejected"), (
                f"Unexpected status value: {c['status']!r}"
            )

    def test_single_candidate_is_shortlisted(self):
        candidates = [
            {"name": "Solo", "email": "solo@example.com", "score": 55.0, "reasoning": "Only one."}
        ]
        result = ranker_tool(candidates, top_n=3)
        assert result[0]["status"] == "Shortlisted"

    def test_integer_scores_accepted(self):
        candidates = [
            {"name": "A", "email": "a@a.com", "score": 80, "reasoning": "Good"},
            {"name": "B", "email": "b@b.com", "score": 60, "reasoning": "Okay"},
        ]
        result = ranker_tool(candidates)
        assert result[0]["name"] == "A"


class TestRankerToolEdgeCases:

    def test_tie_scores_both_can_be_shortlisted(self):
        """When scores are equal, both tied candidates within top_n get Shortlisted."""
        candidates = [
            {"name": "A", "email": "a@a.com", "score": 90.0, "reasoning": "Tied"},
            {"name": "B", "email": "b@b.com", "score": 90.0, "reasoning": "Tied"},
            {"name": "C", "email": "c@c.com", "score": 70.0, "reasoning": "Lower"},
            {"name": "D", "email": "d@d.com", "score": 50.0, "reasoning": "Lowest"},
        ]
        result = ranker_tool(candidates, top_n=2)
        shortlisted = [c for c in result if c["status"] == "Shortlisted"]
        assert len(shortlisted) == 2

    def test_top_n_equals_total_candidates(self, sample_candidates):
        """If top_n >= total, all candidates are Shortlisted."""
        result = ranker_tool(sample_candidates, top_n=len(sample_candidates))
        assert all(c["status"] == "Shortlisted" for c in result)

    def test_top_n_greater_than_total(self, sample_candidates):
        """top_n larger than list should not crash — all are Shortlisted."""
        result = ranker_tool(sample_candidates, top_n=100)
        assert all(c["status"] == "Shortlisted" for c in result)

    def test_zero_score_candidate_ranked_last(self):
        candidates = [
            {"name": "Good", "email": "g@g.com", "score": 75.0, "reasoning": "Fine"},
            {"name": "Zero", "email": "z@z.com", "score": 0.0,  "reasoning": "None"},
        ]
        result = ranker_tool(candidates, top_n=1)
        assert result[-1]["name"] == "Zero"
        assert result[-1]["status"] == "Rejected"

    def test_empty_reasoning_handled_gracefully(self):
        candidates = [
            {"name": "A", "email": "a@a.com", "score": 80.0, "reasoning": ""},
            {"name": "B", "email": "b@b.com", "score": 60.0, "reasoning": ""},
        ]
        result = ranker_tool(candidates)
        assert result[0]["reasoning"] == ""


class TestRankerToolErrorHandling:

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            ranker_tool([])

    def test_top_n_zero_raises_value_error(self, sample_candidates):
        with pytest.raises(ValueError, match="top_n"):
            ranker_tool(sample_candidates, top_n=0)

    def test_top_n_negative_raises_value_error(self, sample_candidates):
        with pytest.raises(ValueError, match="top_n"):
            ranker_tool(sample_candidates, top_n=-1)

    def test_missing_score_field_raises_key_error(self):
        candidates = [{"name": "A", "email": "a@a.com", "reasoning": "No score"}]
        with pytest.raises(KeyError):
            ranker_tool(candidates)

    def test_missing_name_field_raises_key_error(self):
        candidates = [{"email": "a@a.com", "score": 80.0, "reasoning": "No name"}]
        with pytest.raises(KeyError):
            ranker_tool(candidates)

    def test_non_numeric_score_raises_type_error(self):
        candidates = [
            {"name": "A", "email": "a@a.com", "score": "high", "reasoning": "Bad score"}
        ]
        with pytest.raises(TypeError):
            ranker_tool(candidates)

    def test_none_score_raises_type_error(self):
        candidates = [
            {"name": "A", "email": "a@a.com", "score": None, "reasoning": "Null score"}
        ]
        with pytest.raises(TypeError):
            ranker_tool(candidates)


# ===========================================================================
# INTEGRATION TESTS — run_candidate_ranker agent node
# ===========================================================================

class TestRankerAgentNode:

    def test_agent_populates_ranked_candidates(self, base_state):
        result_state = run_candidate_ranker(base_state)
        assert len(result_state["ranked_candidates"]) == 5

    def test_agent_logs_are_appended(self, base_state):
        result_state = run_candidate_ranker(base_state)
        assert len(result_state["logs"]) > 0

    def test_agent_no_errors_on_valid_input(self, base_state):
        result_state = run_candidate_ranker(base_state)
        assert result_state["errors"] == []

    def test_agent_handles_empty_scored_candidates(self, base_state):
        base_state["scored_candidates"] = []
        result_state = run_candidate_ranker(base_state)
        assert result_state["ranked_candidates"] == []
        assert len(result_state["errors"]) > 0

    def test_agent_output_compatible_with_agent4(self, base_state):
        """ranked_candidates must satisfy RankedCandidate TypedDict for Agent 4."""
        result_state = run_candidate_ranker(base_state)
        required = {"rank", "name", "email", "score", "status", "reasoning"}
        for candidate in result_state["ranked_candidates"]:
            assert required.issubset(candidate.keys())

    def test_agent_status_capitalisation_for_agent4(self, base_state):
        """Agent 4 checks status == 'Shortlisted' — must match exactly."""
        result_state = run_candidate_ranker(base_state)
        for c in result_state["ranked_candidates"]:
            assert c["status"] in ("Shortlisted", "Rejected")

    def test_agent_preserves_other_state_fields(self, base_state):
        result_state = run_candidate_ranker(base_state)
        assert result_state["job_description_path"] == "job.json"
        assert result_state["cv_folder_path"] == "cvs/"

    def test_agent_does_not_modify_scored_candidates(self, base_state):
        """Original scored_candidates in state should be unchanged."""
        original = [c.copy() for c in base_state["scored_candidates"]]
        run_candidate_ranker(base_state)
        assert base_state["scored_candidates"] == original