# logs/agent_log.py

import logging
import os
import json
from datetime import datetime
from typing import Any, Dict


# Path to the log file
LOG_DIR = os.path.join(os.path.dirname(__file__))
LOG_FILE = os.path.join(LOG_DIR, "job_matcher.log")


def setup_logger() -> logging.Logger:
    """
    Sets up and returns the logger for the Job Matcher agent.
    Logs to both a file and the console simultaneously.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger("JobMatcherAgent")

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── File Handler (saves everything to job_matcher.log) ──
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # ── Console Handler (prints to terminal) ──
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # ── Formatter ──
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Single shared logger instance used across all files
logger = setup_logger()


def log_agent_start(job_id: str, candidate_count: int) -> None:
    """
    Logs the start of the Job Matcher agent run.

    Args:
        job_id (str): The job ID being processed.
        candidate_count (int): Number of candidates to be scored.

    Returns:
        None
    """
    logger.info("=" * 60)
    logger.info("JOB MATCHER AGENT STARTED")
    logger.info(f"Job ID        : {job_id}")
    logger.info(f"Candidates    : {candidate_count}")
    logger.info(f"Timestamp     : {datetime.now().isoformat()}")
    logger.info("=" * 60)


def log_tool_call(candidate_id: str, candidate_name: str) -> None:
    """
    Logs when the scoring tool is called for a candidate.

    Args:
        candidate_id (str): The candidate's unique ID.
        candidate_name (str): The candidate's full name.

    Returns:
        None
    """
    logger.info(f"[TOOL CALL] Scoring candidate: {candidate_name} (ID: {candidate_id})")


def log_llm_prompt(candidate_id: str, prompt: str) -> None:
    """
    Logs the exact prompt sent to the Ollama LLM.

    Args:
        candidate_id (str): The candidate being scored.
        prompt (str): The full prompt sent to the LLM.

    Returns:
        None
    """
    logger.debug(f"[LLM PROMPT] Candidate {candidate_id}:\n{prompt}")


def log_llm_response(candidate_id: str, response: str) -> None:
    """
    Logs the raw response received from the Ollama LLM.

    Args:
        candidate_id (str): The candidate being scored.
        response (str): The raw LLM response string.

    Returns:
        None
    """
    logger.debug(f"[LLM RESPONSE] Candidate {candidate_id}:\n{response}")


def log_score_result(candidate_id: str, name: str, score: float, matched_skills: list) -> None:
    """
    Logs the final score result after tool execution.

    Args:
        candidate_id (str): The candidate's unique ID.
        name (str): The candidate's full name.
        score (float): The final match score (0-100).
        matched_skills (list): List of skills that matched the job.

    Returns:
        None
    """
    logger.info(
        f"[RESULT] {name} (ID: {candidate_id}) | "
        f"Score: {score}/100 | "
        f"Matched Skills: {matched_skills}"
    )


def log_tool_error(candidate_id: str, error: str) -> None:
    """
    Logs an error that occurred during tool execution.

    Args:
        candidate_id (str): The candidate being processed when error occurred.
        error (str): The error message.

    Returns:
        None
    """
    logger.error(f"[TOOL ERROR] Candidate {candidate_id}: {error}")


def log_agent_complete(job_id: str, total_scored: int) -> None:
    """
    Logs the successful completion of the Job Matcher agent.

    Args:
        job_id (str): The job ID that was processed.
        total_scored (int): Total number of candidates scored.

    Returns:
        None
    """
    logger.info("=" * 60)
    logger.info("JOB MATCHER AGENT COMPLETED")
    logger.info(f"Job ID          : {job_id}")
    logger.info(f"Total Scored    : {total_scored}")
    logger.info(f"Timestamp       : {datetime.now().isoformat()}")
    logger.info("=" * 60)


def log_state_update(stage: str, data: Dict[str, Any]) -> None:
    """
    Logs a state update when data is passed between agents.

    Args:
        stage (str): Description of the state update (e.g. 'Passing to Agent 3').
        data (Dict[str, Any]): The data being passed in the state update.

    Returns:
        None
    """
    logger.info(f"[STATE UPDATE] {stage}")
    logger.debug(f"[STATE DATA] {json.dumps(data, indent=2)}")