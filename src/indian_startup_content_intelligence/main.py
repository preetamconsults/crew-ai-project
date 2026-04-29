#!/usr/bin/env python
"""Entry point for the IndianStartupContentIntelligence crew.

The `inputs` dict defines the API contract on CrewAI AMP — these become the
parameters exposed via the `/inputs` endpoint and accepted by `/kickoff`.

Required env vars:
- OPENAI_API_KEY  — for the agent LLMs
- TAVILY_API_KEY  — for the source scout's targeted web search

On AMP, set both via the deployment dashboard (Settings → Environment).
Locally, drop them in a `.env` file at the project root.
"""

import sys

from indian_startup_content_intelligence.crew import (
    IndianStartupContentIntelligenceCrew,
)


def _default_inputs() -> dict:
    """Sensible defaults so AMP exposes these as the API contract.

    Callers (or AMP API consumers) can override any subset of these by passing
    their own values. Anything not overridden falls back to the default.
    """
    return {
        "topic": "Indian startup ecosystem this week",
        "audience": "Indian early-stage B2B SaaS founders (pre-seed to series-A)",
        "goal": "saves",
        "num_briefs": 3,
    }


def run():
    """Run the crew with user-provided (or default) inputs."""
    IndianStartupContentIntelligenceCrew().crew().kickoff(inputs=_default_inputs())


def train():
    """Train the crew for a given number of iterations."""
    try:
        IndianStartupContentIntelligenceCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=_default_inputs(),
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
            inputs=_default_inputs(),
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
