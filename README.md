# IndianStartupContentIntelligence Crew

Welcome to the IndianStartupContentIntelligence Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on complex tasks, maximizing their collective intelligence and capabilities.

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```
### Customizing

**This crew uses Azure OpenAI (NOT direct OpenAI).** Copy `.env.example` to `.env` and set:
- `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION`
- `AZURE_GPT4O_DEPLOYMENT` and `AZURE_GPT4O_MINI_DEPLOYMENT` (your Azure deployment names)
- `TAVILY_API_KEY`

Do NOT set `OPENAI_API_KEY` — it's not used.

- Modify `src/indian_startup_content_intelligence/config/agents.yaml` to define your agents
- Modify `src/indian_startup_content_intelligence/config/tasks.yaml` to define your tasks
- Modify `src/indian_startup_content_intelligence/crew.py` to add your own logic, tools and specific args
- The crew runs autonomously with no inputs — every kickoff produces 3 briefs (1 carousel + 2 stories) for Indian early-stage SaaS/B2B founders.

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ crewai run
```

This command initializes the indian_startup_content_intelligence Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folder.

## Understanding Your Crew

The indian_startup_content_intelligence Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the IndianStartupContentIntelligence Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
