#!/usr/bin/env python
"""Entry point for the IndianStartupContentIntelligence crew.

This crew is HARDCODED for early-stage Indian SaaS/B2B founder content
(awareness-driven, follower-growth oriented). No user inputs — every run
produces 3 briefs (1 carousel + 2 stories) on auto-discovered trending topics.

Required env vars on CrewAI AMP:
- AZURE_API_KEY
- AZURE_API_BASE              (e.g. https://<resource>.openai.azure.com)
- AZURE_API_VERSION           (e.g. 2024-08-01-preview)
- AZURE_GPT4O_DEPLOYMENT      (your gpt-4o deployment name; defaults to "gpt-4o")
- AZURE_GPT4O_MINI_DEPLOYMENT (your gpt-4o-mini deployment name; defaults to "gpt-4o-mini")
- TAVILY_API_KEY              (free tier at https://tavily.com)
"""

import sys

from indian_startup_content_intelligence.crew import (
    IndianStartupContentIntelligenceCrew,
)


def run():
    """Run the crew. No inputs — fully autonomous, hardcoded persona."""
    IndianStartupContentIntelligenceCrew().crew().kickoff(inputs={})


def train():
    """Train the crew for a given number of iterations."""
    try:
        IndianStartupContentIntelligenceCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs={},
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """Replay the crew execution from a specific task."""
    try:
        IndianStartupContentIntelligenceCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """Test the crew execution and return the results."""
    try:
        IndianStartupContentIntelligenceCrew().crew().test(
            n_iterations=int(sys.argv[1]),
            openai_model_name=sys.argv[2],
            inputs={},
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: main.py <command> [<args>]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "run":
        run()
    elif command == "train":
        train()
    elif command == "replay":
        replay()
    elif command == "test":
        test()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
