#!/usr/bin/env python3
# ======================================================================================
# Agent: Device Compliance Alert Extractor
# ======================================================================================
"""Extract a single structured compliance alert object from a short incident description.

Features:
    * Uses Pydantic model enforcement via response_format for strict JSON schema.
    * Logs token usage (prompt, completion, reasoning, total).
    * Pretty-prints the resulting alert object.

Usage:
    $ python -m src.agents.structured

Environment:
    OPENAI_API_KEY must be set.
"""

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Literal
load_dotenv()

# ======================================================================================
# Initialize Logging
# ======================================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)

# ======================================================================================
# Vars
# ======================================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ======================================================================================
# Define response format in a Pydantic model
# ======================================================================================

class ComplianceAlert(BaseModel):
    """Structured object representing a compliance alert."""
    title: str = Field(..., min_length=3, description="Short human-readable title")
    platform: Literal["macOS", "Windows", "iOS", "iPadOS", "Android", "Unknown"] = Field(
        default="Unknown", description="Impacted platform, or Unknown"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="Severity level"
    )
    issue: str = Field(..., min_length=5, description="One or two sentence description")
    affected_devices: int = Field(..., ge=0, description="Approximate affected device count")
    actions: List[str] = Field(default_factory=list, description="Suggested remediation actions")

# ======================================================================================
# Initialize OpenAI Client
# ======================================================================================

def instantiate_client(system_prompt: str, user_prompt: str):
    """Create a structured completion using the ComplianceAlert model."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        return client.chat.completions.parse(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=ComplianceAlert,
            reasoning_effort="minimal",
        )
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}")
        return None
    
def parse_data(completion):
    """Extract structured alert and token usage tuple."""
    try:
        msg = completion.choices[0].message
        alert_data = msg.parsed
        usage = completion.usage
        return (
            alert_data,
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.completion_tokens_details.reasoning_tokens,
            usage.total_tokens,
        )
    except Exception as e:
        logger.error(f"Error parsing completion data: {e}")
        return None

def main():
    """
    Main function to run the OpenAI API call and process the response
    """

    completion = instantiate_client(
        system_prompt=(
            "You extract device compliance alerts for IT. Return exactly one ComplianceAlert object. "
            "If platform unclear use 'Unknown'. Infer severity from urgency words. Keep title short; issue one or two sentences."
        ),
        user_prompt=(
            "Heads up—lots of Macs stuck on outdated CrowdStrike sensor.\n"
            "Impact: roughly 27 devices are non-compliant and failing vulnerability checks.\n"
            "This is pretty urgent because of SOC requirements.\n"
            "Please advise A/V team to push sensor update via Jamf Self Service and notify owners."
        ),
    )

    if completion:
        data = parse_data(completion)
        if data:
            alert_data, prompt_tokens, completion_tokens, reasoning_tokens, total_tokens = data

            # Usage details
            logger.info("\n=== Token Usage ===")
            logger.info(f"Prompt: {prompt_tokens} | Completion: {completion_tokens} | Reasoning: {reasoning_tokens} | Total: {total_tokens}")
            logger.info("\n=== Compliance Alert ===")
            logger.info(alert_data.model_dump_json(indent=2))  # type: ignore

if __name__ == "__main__":
    """
    Entry point for the application
    """
    main()