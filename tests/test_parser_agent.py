import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.parser_agent import (
    extract_email,
    extract_phone,
    extract_skills,
    extract_years_of_experience,
    extract_location,
    parse_single_cv
)


class TestParserAgent(unittest.TestCase):

    def test_extract_email(self):
        text = "Email: nimali.perera@gmail.com"
        self.assertEqual(extract_email(text), "nimali.perera@gmail.com")

    def test_extract_phone(self):
        text = "Phone: +94 71 234 5678"
        self.assertEqual(extract_phone(text), "+94 71 234 5678")

    def test_extract_skills(self):
        text = "Skills: Python, Java, React, SQL"
        skills = extract_skills(text)

        self.assertIn("Python", skills)
        self.assertIn("Java", skills)
        self.assertIn("React", skills)
        self.assertIn("SQL", skills)

    def test_extract_years_from_date_range(self):
        text = "Experience: Trainee Software Engineer (2023 - 2024)"
        self.assertEqual(extract_years_of_experience(text), 1.0)

    def test_extract_location(self):
        text = "Name: Kasun\nLocation: Kandy, Sri Lanka\nEmail: test@gmail.com"
        self.assertEqual(extract_location(text), "Kandy, Sri Lanka")

    def test_parse_single_cv_has_required_fields(self):
        sample_cv = {
            "file_name": "test_cv.txt",
            "text": """
            John Silva
            Email: johnsilva@gmail.com
            Phone: +94 77 123 4567
            Location: Colombo, Sri Lanka

            Skills:
            Python, Java, SQL

            Education:
            BSc in Software Engineering

            Experience:
            Intern at ABC Company
            """
        }

        result = parse_single_cv(sample_cv, 0)

        # CandidateProfile fields as defined in state/shared_state.py
        required_fields = [
            "candidate_id",
            "name",
            "email",
            "skills",
            "experience_years",
            "education",
            "raw_text"
        ]

        for field in required_fields:
            self.assertIn(field, result)

    def test_parse_single_cv_basic_values(self):
        sample_cv = {
            "file_name": "test_cv.txt",
            "text": """
            John Silva
            Email: johnsilva@gmail.com
            Phone: +94 77 123 4567

            Skills:
            Python, Java, SQL

            Experience:
            Intern at ABC Company
            """
        }

        result = parse_single_cv(sample_cv, 0)

        self.assertEqual(result["name"], "John Silva")
        self.assertEqual(result["email"], "johnsilva@gmail.com")
        self.assertIn("Python", result["skills"])

    def test_empty_cv_does_not_crash(self):
        sample_cv = {
            "file_name": "empty.txt",
            "text": ""
        }

        result = parse_single_cv(sample_cv, 0)

        self.assertIsInstance(result, dict)
        self.assertIn("file_name", sample_cv)
        self.assertIn("candidate_id", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)