import os
from pathlib import Path

from crewai import LLM, Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, after_kickoff, agent, crew, task
from crewai_tools import FileReadTool, TavilySearchTool

from indian_startup_content_intelligence.models import (
    FormatRecommendationBatch,
    InstagramBriefBatch,
    RankedTopicBatch,
    RawItemBatch,
    TopicClusterBatch,
)
from indian_startup_content_intelligence.tools.instagram_brief_renderer import (
    InstagramBriefRendererTool,
    render_briefs_to_html,
)
from indian_startup_content_intelligence.tools.rss_collector import (
    RSSFeedCollectorTool,
)


# Azure OpenAI deployment names. Override via env vars on AMP if your Azure
# deployments are named differently. The provider is locked to "azure/" — the
# litellm router uses AZURE_API_KEY / AZURE_API_BASE / AZURE_API_VERSION.
_AZURE_GPT4O = os.getenv("AZURE_GPT4O_DEPLOYMENT", "gpt-4o")
_AZURE_GPT4O_MINI = os.getenv("AZURE_GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini")


def _make_llm(deployment: str) -> LLM:
    # Force LiteLLM routing — the "native" CrewAI Azure provider is Azure AI
    # Inference (different service); for Azure OpenAI we want the LiteLLM
    # azure/ prefix which uses AZURE_API_KEY / AZURE_API_BASE / AZURE_API_VERSION.
    return LLM(model=f"azure/{deployment}", is_litellm=True)


@CrewBase
class IndianStartupContentIntelligenceCrew:
    """IndianStartupContentIntelligence crew."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---------- Agents ----------

    @agent
    def source_scout_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["source_scout_agent"],  # type: ignore[index]
            tools=[
                RSSFeedCollectorTool(),
                TavilySearchTool(
                    topic="news",
                    time_range="week",
                    search_depth="basic",
                    max_results=8,
                    days=7,
                    include_answer=False,
                    include_raw_content=False,
                ),
            ],
            llm=_make_llm(_AZURE_GPT4O),
        )

    @agent
    def content_classifier_and_topic_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["content_classifier_and_topic_analyzer"],  # type: ignore[index]
            llm=_make_llm(_AZURE_GPT4O),
        )

    @agent
    def topic_ranking_and_selection_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["topic_ranking_and_selection_specialist"],  # type: ignore[index]
            tools=[FileReadTool()],
            llm=_make_llm(_AZURE_GPT4O),
        )

    @agent
    def instagram_content_format_specialist_for_b2b_founder_audiences(self) -> Agent:
        return Agent(
            config=self.agents_config["instagram_content_format_specialist_for_b2b_founder_audiences"],  # type: ignore[index]
            llm=_make_llm(_AZURE_GPT4O),
        )

    @agent
    def senior_creative_director_for_instagram_b2b_content___schema_compliant(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_creative_director_for_instagram_b2b_content___schema_compliant"],  # type: ignore[index]
            llm=_make_llm(_AZURE_GPT4O),
        )

    @agent
    def document_generation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["document_generation_specialist"],  # type: ignore[index]
            tools=[InstagramBriefRendererTool()],
            llm=_make_llm(_AZURE_GPT4O_MINI),
        )

    # ---------- Tasks ----------

    @task
    def collect_indian_startup_content(self) -> Task:
        return Task(
            config=self.tasks_config["collect_indian_startup_content"],  # type: ignore[index]
            output_pydantic=RawItemBatch,
        )

    @task
    def classify_and_cluster(self) -> Task:
        return Task(
            config=self.tasks_config["classify_and_cluster"],  # type: ignore[index]
            output_pydantic=TopicClusterBatch,
        )

    @task
    def validate_and_rank(self) -> Task:
        return Task(
            config=self.tasks_config["validate_and_rank"],  # type: ignore[index]
            output_pydantic=RankedTopicBatch,
        )

    @task
    def choose_format(self) -> Task:
        return Task(
            config=self.tasks_config["choose_format"],  # type: ignore[index]
            output_pydantic=FormatRecommendationBatch,
        )

    @task
    def generate_schema_compliant_instagram_briefs(self) -> Task:
        return Task(
            config=self.tasks_config["generate_schema_compliant_instagram_briefs"],  # type: ignore[index]
            output_pydantic=InstagramBriefBatch,
        )

    @task
    def generate_professional_word_ready_documents(self) -> Task:
        return Task(
            config=self.tasks_config["generate_professional_word_ready_documents"],  # type: ignore[index]
        )

    # ---------- Lifecycle hooks ----------

    @after_kickoff
    def _persist_html_locally(self, result):
        """Save the final HTML to ./output/briefs.html for local convenience.

        On CrewAI AMP this is best-effort — the platform doesn't persist files,
        but the HTML is also returned in `result.raw` so it's still available
        via the API. Locally the user just opens the file in browser or Word.
        """
        try:
            html: str | None = None

            if result.raw and "<!doctype html" in result.raw.lower():
                html = result.raw

            if not html and getattr(result, "tasks_output", None):
                for task_output in result.tasks_output:
                    pyd = getattr(task_output, "pydantic", None)
                    if isinstance(pyd, InstagramBriefBatch):
                        html = render_briefs_to_html(pyd)
                        break

            if not html:
                return result

            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            html_path = output_dir / "briefs.html"
            html_path.write_text(html, encoding="utf-8")

            banner = (
                "\n"
                "================================================================\n"
                "  ✓  YOUR INSTAGRAM BRIEFS ARE READY\n"
                "================================================================\n"
                f"  File:   {html_path.resolve()}\n"
                f"  Briefs: {len(html):,} characters of formatted content\n"
                "\n"
                "  → Double-click the file to open it in your browser.\n"
                "  → Or right-click → Open With → Microsoft Word.\n"
                "================================================================\n"
            )
            print(banner)
        except Exception as exc:
            print(f"\n[after_kickoff] Could not persist HTML to disk: {exc}\n")
        return result

    # ---------- Crew ----------

    @crew
    def crew(self) -> Crew:
        """Creates the IndianStartupContentIntelligence crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            chat_llm=_make_llm(_AZURE_GPT4O_MINI),
        )
