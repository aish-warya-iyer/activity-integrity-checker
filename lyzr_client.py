import json
import os
import uuid

from lyzr_python_sdk import LyzrAgentAPI

API_KEY = os.environ.get("LYZR_AGENT_API_KEY")
AGENT_ID = os.environ.get("LYZR_AGENT_ID")
USER_ID = os.environ.get("USER_EMAIL", "athlete@activity-integrity-checker")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = LyzrAgentAPI(API_KEY)
    return _client


def generate_explanation(deviation_results):
    message = (
        "Analysis data (JSON): "
        + json.dumps(deviation_results)
        + ". Write a short, factual, plain-language explanation of these segment "
        "deviation findings. Only state facts present in the input data. "
        "Do not speculate about cause or intent."
    )
    resp = _get_client().inference.chat(
        {
            "user_id": USER_ID,
            "agent_id": AGENT_ID,
            "session_id": str(uuid.uuid4()),
            "message": message,
        }
    )
    return resp["response"]
