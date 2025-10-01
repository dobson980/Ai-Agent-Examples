#!/usr/bin/env python3
# ======================================================================================
# Agent: Python Haiku Generator
# ======================================================================================
"""Minimal example agent that creates a haiku using the OpenAI Chat Completions API.

Features:
    * Simple system + user prompts.
    * Logs token usage (prompt, completion, reasoning, total).
    * Prints the generated haiku.

Usage:
    $ python -m src.agents.basic

Environment:
    OPENAI_API_KEY must be set.
"""

from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
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
MODEL = "gpt-5-nano"

# ======================================================================================
# Initialize OpenAI Client
# ======================================================================================

def instantiate_client(system_prompt: str, user_prompt: str):
    """Create a completion with the supplied prompts.

    Returns:
        The completion object on success, otherwise None.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        return client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            reasoning_effort="minimal",
        )
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}")
        return None

# ======================================================================================
# Parse Data
# ======================================================================================

def parse_data(completion):
    """Return token usage and response text.

    Returns:
        tuple(prompt_tokens, completion_tokens, reasoning_tokens, total_tokens, content)
    """
    data = completion.model_dump()
    usage = data["usage"]
    input_tokens = usage["prompt_tokens"]
    output_tokens = usage["completion_tokens"]
    reasoning_tokens = usage["completion_tokens_details"]["reasoning_tokens"]
    total_tokens = usage["total_tokens"]
    response_text = data["choices"][0]["message"]["content"]
    return input_tokens, output_tokens, reasoning_tokens, total_tokens, response_text

# ======================================================================================
# Define Main Function
# ======================================================================================

def main():
    """
    Main function to run the OpenAI client and print the response.
    """
    completion = instantiate_client(
        system_prompt="You are the best haiku poet in the world.",
        user_prompt="Write a haiku about the beauty of Python and OpenAI.",
    )
    if completion:
        input_tokens, output_tokens, reasoning_tokens, total_tokens, response_text = parse_data(completion)

        logger.info(
            f"\n=== Token Usage ===\nPrompt: {input_tokens} | Completion: {output_tokens} | Reasoning: {reasoning_tokens} | Total: {total_tokens}\n"
        )
        logger.info("=== Haiku ===\n" + response_text + "\n")

# ======================================================================================
# App Entry Point
# ======================================================================================

if __name__ == "__main__":
    main()
    """
    Run the main function if this script is executed directly.
    """