"""
Logging utilities for the Multi-Agent System (MAS).

Provides a simple logging function for tracking agent events.
"""
import json
from datetime import datetime
from typing import Any, Optional


def log_event(
    agent_name: str,
    event_type: str,
    tool_name: Optional[str] = None,
    inputs: Optional[dict] = None,
    outputs: Optional[dict] = None,
    message: Optional[str] = None,
) -> None:
    """
    Log an event from an agent.
    
    Args:
        agent_name: Name of the agent generating the event
        event_type: Type of event (e.g., 'agent_start', 'agent_end', 'tool_call', 'error')
        tool_name: Name of the tool if this is a tool call
        inputs: Input parameters if this is a tool call
        outputs: Output results if this is a tool call
        message: Additional message to log
    """
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "agent": agent_name,
        "event_type": event_type,
    }
    
    if tool_name:
        log_entry["tool_name"] = tool_name
    if inputs:
        log_entry["inputs"] = inputs
    if outputs:
        log_entry["outputs"] = outputs
    if message:
        log_entry["message"] = message
    
    # Print to console (can be replaced with proper logging or file output)
    print(json.dumps(log_entry, indent=2))