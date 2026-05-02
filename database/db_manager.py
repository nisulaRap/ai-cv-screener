# database/db_manager.py

import sqlite3
import json
import os
from typing import List, Optional
from datetime import datetime
from state.shared_state import MatchResult


# Path to the SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "cv_screener.db")


def get_connection() -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: Active database connection with row factory set.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like row access
    return conn


def initialize_database() -> None:
    """
    Creates the required tables if they don't already exist.
    Should be called once at the start of the pipeline.
    
    Tables created:
        - match_results: stores scoring results from Agent 2
        - job_descriptions: stores the job posting metadata
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_results (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id        TEXT NOT NULL,
            name                TEXT NOT NULL,
            score               REAL NOT NULL,
            reasoning           TEXT NOT NULL,
            matched_skills      TEXT NOT NULL,
            missing_skills      TEXT NOT NULL,
            status              TEXT DEFAULT 'Pending',
            job_id              TEXT NOT NULL,
            created_at          TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            job_id              TEXT PRIMARY KEY,
            title               TEXT NOT NULL,
            required_skills     TEXT NOT NULL,
            preferred_skills    TEXT NOT NULL,
            min_experience_years REAL NOT NULL,
            education_requirement TEXT NOT NULL,
            description         TEXT NOT NULL,
            created_at          TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


def save_match_result(result: MatchResult, job_id: str) -> None:
    """
    Saves a single candidate match result to the database.

    Args:
        result (MatchResult): The scoring result produced by the Job Matcher agent.
        job_id (str): The ID of the job description being matched against.

    Returns:
        None
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO match_results 
        (candidate_id, name, score, reasoning, matched_skills, missing_skills, status, job_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["candidate_id"],
        result["name"],
        result["score"],
        result["reasoning"],
        json.dumps(result["matched_skills"]),   # store list as JSON string
        json.dumps(result["missing_skills"]),   # store list as JSON string
        result.get("status", "Pending"),
        job_id,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_all_match_results(job_id: str) -> List[MatchResult]:
    """
    Retrieves all match results for a specific job from the database.
    Used by Agent 3 (Candidate Ranker) to fetch and rank candidates.

    Args:
        job_id (str): The job ID to filter results by.

    Returns:
        List[MatchResult]: List of all match results for that job, ordered by score descending.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM match_results
        WHERE job_id = ?
        ORDER BY score DESC
    """, (job_id,))

    rows = cursor.fetchall()
    conn.close()

    results: List[MatchResult] = []
    for row in rows:
        results.append(MatchResult(
            candidate_id=row["candidate_id"],
            name=row["name"],
            score=row["score"],
            reasoning=row["reasoning"],
            matched_skills=json.loads(row["matched_skills"]),
            missing_skills=json.loads(row["missing_skills"]),
            status=row["status"]
        ))

    return results


def clear_results_for_job(job_id: str) -> None:
    """
    Deletes all match results for a given job ID.
    Useful for re-running the pipeline without duplicate entries.

    Args:
        job_id (str): The job ID whose results should be cleared.

    Returns:
        None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM match_results WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()
    print(f"[DB] Cleared previous results for job: {job_id}")