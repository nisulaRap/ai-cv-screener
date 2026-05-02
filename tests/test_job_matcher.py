import sys
import os
import json
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.score_candidate_tool import (
    build_scoring_prompt,
    extract_json_from_response,
    validate_score_output,
    score_candidate
)
from database.db_manager import initialize_database, get_all_match_results, clear_results_for_job
from shared_state import CandidateProfile, JobDescription


# ─────────────────────────────────────────────
# SAMPLE DATA FOR TESTS
# ─────────────────────────────────────────────

SAMPLE_JOB: JobDescription = {
    "job_id": "test_job_001",
    "title": "Senior Python Developer",
    "required_skills": ["Python", "REST APIs", "SQL", "Git"],
    "preferred_skills": ["FastAPI", "Docker", "PostgreSQL", "Redis"],
    "min_experience_years": 3.0,
    "education_requirement": "Bachelor's degree in Computer Science or related field",
    "description": (
        "We are looking for a Senior Python Developer to join our backend team. "
        "You will design and build scalable REST APIs, work with SQL databases, "
        "and collaborate with frontend teams."
    )
}

STRONG_CANDIDATE: CandidateProfile = {
    "candidate_id": "test_candidate_001",
    "name": "Alice Fernando",
    "email": "alice@example.com",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs", "SQL"],
    "experience_years": 5.0,
    "education": "Bachelor's in Computer Science",
    "raw_text": "Alice Fernando - Senior Python Developer with 5 years experience."
}

WEAK_CANDIDATE: CandidateProfile = {
    "candidate_id": "test_candidate_002",
    "name": "Emma Wickramasinghe",
    "email": "emma@example.com",
    "skills": ["HTML", "CSS", "JavaScript"],
    "experience_years": 1.0,
    "education": "Diploma in Web Design",
    "raw_text": "Emma Wickramasinghe - Frontend developer with 1 year experience."
}

PARTIAL_CANDIDATE: CandidateProfile = {
    "candidate_id": "test_candidate_003",
    "name": "Chamari Silva",
    "email": "chamari@example.com",
    "skills": ["Python", "SQL", "Git", "REST APIs"],
    "experience_years": 2.0,
    "education": "Bachelor's in Computer Science",
    "raw_text": "Chamari Silva - Python developer with 2 years experience."
}

EMPTY_CANDIDATE: CandidateProfile = {
    "candidate_id": "test_candidate_004",
    "name": "Unknown Candidate",
    "email": "",
    "skills": [],
    "experience_years": 0.0,
    "education": "",
    "raw_text": ""
}


# ─────────────────────────────────────────────
# TEST SUITE 1 — UNIT TESTS
# Tests individual functions without calling Ollama
# ─────────────────────────────────────────────

class TestPromptBuilder(unittest.TestCase):
    """Unit tests for the build_scoring_prompt function."""

    def test_prompt_contains_job_title(self):
        """Prompt must include the job title."""
        prompt = build_scoring_prompt(STRONG_CANDIDATE, SAMPLE_JOB)
        self.assertIn("Senior Python Developer", prompt)

    def test_prompt_contains_candidate_name(self):
        """Prompt must include the candidate's name."""
        prompt = build_scoring_prompt(STRONG_CANDIDATE, SAMPLE_JOB)
        self.assertIn("Alice Fernando", prompt)

    def test_prompt_contains_required_skills(self):
        """Prompt must include all required skills."""
        prompt = build_scoring_prompt(STRONG_CANDIDATE, SAMPLE_JOB)
        for skill in SAMPLE_JOB["required_skills"]:
            self.assertIn(skill, prompt)

    def test_prompt_contains_json_instruction(self):
        """Prompt must instruct the LLM to return JSON only."""
        prompt = build_scoring_prompt(STRONG_CANDIDATE, SAMPLE_JOB)
        self.assertIn("valid JSON", prompt)

    def test_prompt_contains_scoring_rules(self):
        """Prompt must include scoring rules."""
        prompt = build_scoring_prompt(STRONG_CANDIDATE, SAMPLE_JOB)
        self.assertIn("SCORING RULES", prompt)


class TestJsonExtractor(unittest.TestCase):
    """Unit tests for the extract_json_from_response function."""

    def test_clean_json_parses_correctly(self):
        """Should parse a clean JSON string directly."""
        raw = '{"score": 85, "reasoning": "Good match", "matched_skills": ["Python"], "missing_skills": []}'
        result = extract_json_from_response(raw)
        self.assertEqual(result["score"], 85)

    def test_json_with_surrounding_text(self):
        """Should extract JSON even when surrounded by extra text."""
        raw = 'Here is my response: {"score": 70, "reasoning": "Decent", "matched_skills": ["Python"], "missing_skills": ["Docker"]} Hope this helps!'
        result = extract_json_from_response(raw)
        self.assertEqual(result["score"], 70)

    def test_invalid_json_raises_error(self):
        """Should raise ValueError when no valid JSON is found."""
        raw = "I cannot provide a score for this candidate."
        with self.assertRaises(ValueError):
            extract_json_from_response(raw)

    def test_empty_response_raises_error(self):
        """Should raise ValueError on empty response."""
        with self.assertRaises(ValueError):
            extract_json_from_response("")


class TestScoreValidator(unittest.TestCase):
    """Unit tests for the validate_score_output function."""

    def test_valid_output_passes(self):
        """A fully valid output should not raise any errors."""
        data = {
            "score": 75,
            "reasoning": "Good candidate with relevant skills.",
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["Docker"]
        }
        try:
            validate_score_output(data)
        except ValueError:
            self.fail("validate_score_output raised ValueError on valid data.")

    def test_missing_score_raises_error(self):
        """Missing score field should raise ValueError."""
        data = {
            "reasoning": "Some reasoning",
            "matched_skills": [],
            "missing_skills": []
        }
        with self.assertRaises(ValueError):
            validate_score_output(data)

    def test_score_above_100_raises_error(self):
        """Score above 100 should raise ValueError."""
        data = {
            "score": 150,
            "reasoning": "Too high",
            "matched_skills": [],
            "missing_skills": []
        }
        with self.assertRaises(ValueError):
            validate_score_output(data)

    def test_score_below_0_raises_error(self):
        """Score below 0 should raise ValueError."""
        data = {
            "score": -10,
            "reasoning": "Negative score",
            "matched_skills": [],
            "missing_skills": []
        }
        with self.assertRaises(ValueError):
            validate_score_output(data)

    def test_empty_reasoning_raises_error(self):
        """Empty reasoning string should raise ValueError."""
        data = {
            "score": 50,
            "reasoning": "",
            "matched_skills": [],
            "missing_skills": []
        }
        with self.assertRaises(ValueError):
            validate_score_output(data)

    def test_missing_skills_fields_raise_error(self):
        """Missing matched_skills or missing_skills should raise ValueError."""
        data = {
            "score": 50,
            "reasoning": "Some reasoning"
        }
        with self.assertRaises(ValueError):
            validate_score_output(data)


# ─────────────────────────────────────────────
# TEST SUITE 2 — INTEGRATION TESTS
# Tests the full scoring pipeline with Ollama
# ─────────────────────────────────────────────

class TestScoringIntegration(unittest.TestCase):
    """
    Integration tests that call the actual score_candidate tool with Ollama.
    These tests validate real end-to-end behavior.
    """

    def setUp(self):
        """Initialize database before each test."""
        initialize_database()
        clear_results_for_job("test_job_001")

    def test_strong_candidate_scores_high(self):
        """A highly qualified candidate should score above 70."""
        result = score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)
        self.assertGreaterEqual(result["score"], 70,
            f"Strong candidate scored too low: {result['score']}")

    def test_weak_candidate_scores_low(self):
        """A completely unqualified candidate should score below 30."""
        result = score_candidate(WEAK_CANDIDATE, SAMPLE_JOB)
        self.assertLessEqual(result["score"], 30,
            f"Weak candidate scored too high: {result['score']}")

    def test_strong_beats_weak(self):
        """Strong candidate must always score higher than weak candidate."""
        strong_result = score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)
        weak_result = score_candidate(WEAK_CANDIDATE, SAMPLE_JOB)
        self.assertGreater(strong_result["score"], weak_result["score"],
            "Strong candidate should always outscore weak candidate.")

    def test_result_has_all_required_fields(self):
        """Result must contain all required MatchResult fields."""
        result = score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)
        required_fields = ["candidate_id", "name", "score", "reasoning",
                          "matched_skills", "missing_skills", "status"]
        for field in required_fields:
            self.assertIn(field, result, f"Missing field in result: {field}")

    def test_score_is_within_valid_range(self):
        """Score must always be between 0 and 100."""
        result = score_candidate(PARTIAL_CANDIDATE, SAMPLE_JOB)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_result_saved_to_database(self):
        """Result must be saved to the database after scoring."""
        score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)
        db_results = get_all_match_results("test_job_001")
        self.assertGreater(len(db_results), 0,
            "Result was not saved to the database.")

    def test_matched_skills_are_relevant(self):
        """Matched skills must only contain skills from the job description."""
        result = score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)
        all_job_skills = (
            SAMPLE_JOB["required_skills"] +
            SAMPLE_JOB["preferred_skills"]
        )
        for skill in result["matched_skills"]:
            self.assertIn(skill, all_job_skills,
                f"Matched skill '{skill}' is not in the job description.")

    def test_empty_candidate_does_not_crash(self):
        """An empty candidate profile should return score of 0 without crashing."""
        result = score_candidate(EMPTY_CANDIDATE, SAMPLE_JOB)
        self.assertLessEqual(result["score"], 10,
            f"Empty candidate should score 0, got: {result['score']}")
        self.assertIsInstance(result, dict,
            "Result should be a dict even for empty candidate.")


# ─────────────────────────────────────────────
# TEST SUITE 3 — LLM-AS-A-JUDGE TESTS
# Uses Ollama itself to evaluate output quality
# ─────────────────────────────────────────────

class TestLLMAsJudge(unittest.TestCase):
    """
    LLM-as-a-Judge evaluation tests.
    Uses Ollama to verify the quality and consistency of scoring reasoning.
    This satisfies the assignment's requirement for LLM-based evaluation.
    """

    def setUp(self):
        """Set up LLM judge and generate result to evaluate."""
        from langchain_ollama import OllamaLLM
        self.judge_llm = OllamaLLM(model="llama3:8b", temperature=0.0)
        initialize_database()
        clear_results_for_job("test_job_001")

    def _ask_judge(self, question: str) -> str:
        """
        Helper method to ask the LLM judge a yes/no question.

        Args:
            question (str): The evaluation question to ask the judge.

        Returns:
            str: The judge's response in lowercase.
        """
        prompt = f"""You are an evaluation judge. Answer ONLY with 'yes' or 'no'.

{question}

Answer (yes/no):"""
        response = self.judge_llm.invoke(prompt)
        return response.strip().lower()

    def test_reasoning_is_relevant(self):
        """Judge must confirm reasoning is relevant to the job and candidate."""
        result = score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)

        question = f"""
A candidate named '{STRONG_CANDIDATE['name']}' was evaluated for the role of '{SAMPLE_JOB['title']}'.
Their score was {result['score']}/100.
The reasoning given was: "{result['reasoning']}"

Is this reasoning relevant to evaluating a software developer candidate?
"""
        answer = self._ask_judge(question)
        self.assertIn("yes", answer,
            f"Judge found reasoning irrelevant: {result['reasoning']}")

    def test_high_score_reasoning_is_positive(self):
        """Judge must confirm high-scoring candidate has positive reasoning."""
        result = score_candidate(STRONG_CANDIDATE, SAMPLE_JOB)

        question = f"""
A candidate scored {result['score']}/100 for a Python developer role.
The reasoning was: "{result['reasoning']}"

Does this reasoning mention positive qualities or matching skills?
"""
        answer = self._ask_judge(question)
        self.assertIn("yes", answer,
            f"High score reasoning is not positive: {result['reasoning']}")

    def test_low_score_reasoning_mentions_gaps(self):
        """Judge must confirm low-scoring candidate reasoning mentions skill gaps."""
        result = score_candidate(WEAK_CANDIDATE, SAMPLE_JOB)

        question = f"""
A candidate scored {result['score']}/100 for a Python developer role.
The reasoning was: "{result['reasoning']}"

Does this reasoning mention missing skills or gaps?
"""
        answer = self._ask_judge(question)
        self.assertIn("yes", answer,
            f"Low score reasoning does not mention gaps: {result['reasoning']}")


# ─────────────────────────────────────────────
# RUN ALL TESTS
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 RUNNING JOB MATCHER AGENT TEST SUITE")
    print("=" * 60)

    # Run unit tests first (fast, no Ollama needed)
    print("\n📦 SUITE 1: Unit Tests (no Ollama required)")
    unit_suite = unittest.TestLoader().loadTestsFromTestCase(TestPromptBuilder)
    unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestJsonExtractor))
    unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestScoreValidator))

    print("\n🔗 SUITE 2: Integration Tests (requires Ollama)")
    integration_suite = unittest.TestLoader().loadTestsFromTestCase(TestScoringIntegration)

    print("\n⚖️  SUITE 3: LLM-as-a-Judge Tests (requires Ollama)")
    judge_suite = unittest.TestLoader().loadTestsFromTestCase(TestLLMAsJudge)

    # Run everything
    unittest.main(verbosity=2)