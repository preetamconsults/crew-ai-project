"""Pydantic schemas for structured task handoffs.

Every task uses one of these as `output_pydantic`. This forces the LLM into
structured-output mode and validates every handoff so a single bad response
can't corrupt the rest of the pipeline.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------- Task 1: collect_indian_startup_content ----------

class RawItem(BaseModel):
    title: str
    brief_description: str
    url: str
    source: str
    published: str = Field(
        default="",
        description="ISO 8601 timestamp from the feed, empty if absent.",
    )


class RawItemBatch(BaseModel):
    items: list[RawItem] = Field(min_length=3, max_length=30)


# ---------- Task 2: classify_and_cluster ----------

Stage = Literal["seed", "series-a", "series-b+", "growth", "exits", "irrelevant"]
Pillar = Literal[
    "fundraising", "gtm", "hiring", "product", "founder_psych", "exits", "regulation"
]


class ClassifiedItem(BaseModel):
    title: str
    url: str
    stage: Stage
    pillar: Pillar
    india_specific: bool
    persona_fit_score: float = Field(ge=0.0, le=1.0)


class TopicCluster(BaseModel):
    canonical_topic: str
    items: list[ClassifiedItem] = Field(min_length=1, max_length=5)
    avg_persona_fit_score: float = Field(ge=0.0, le=1.0)


class TopicClusterBatch(BaseModel):
    clusters: list[TopicCluster]


# ---------- Task 3: validate_and_rank ----------

class RankedTopic(BaseModel):
    canonical_topic: str
    items: list[ClassifiedItem]
    relevance_score: float = Field(ge=1.0, le=10.0)
    actionability_score: float = Field(ge=1.0, le=10.0)
    stage_fit_score: float = Field(ge=1.0, le=10.0)
    quality_score: float = Field(ge=1.0, le=10.0)
    final_score: float = Field(
        ge=0.0,
        le=10.0,
        description="Weighted: relevance*0.3 + actionability*0.25 + stage*0.25 + quality*0.2",
    )
    score_breakdown: str
    persona_fit: float = Field(ge=0.0, le=1.0)


class RankedTopicBatch(BaseModel):
    topics: list[RankedTopic] = Field(max_length=3)


# ---------- Task 4: choose_format ----------

InstagramFormat = Literal["reel", "carousel", "story", "static"]
PrimaryMetric = Literal["saves", "watch_time", "shares", "comments"]


class FormatRecommendation(BaseModel):
    canonical_topic: str
    format: InstagramFormat
    expected_primary_metric: PrimaryMetric
    rubric_match: str
    reasoning: str


class FormatRecommendationBatch(BaseModel):
    recommendations: list[FormatRecommendation]


# ---------- Task 5: generate_schema_compliant_instagram_briefs ----------

PrimaryGoal = Literal[
    "awareness", "engagement", "saves", "shares", "follows", "leads"
]


class SourceCitation(BaseModel):
    """A real upstream RawItem url the brief draws from. URLs MUST come from the cluster."""

    title: str
    url: str
    source: str
    relevance_note: str = Field(
        description="One sentence on what specifically this source contributes to the brief."
    )


class HookOption(BaseModel):
    """One of three hook drafts. The agent picks the best at production time."""

    label: Literal["A", "B", "C"]
    angle: str = Field(
        description=(
            "The psychological angle. e.g. 'specific number', 'contrarian', "
            "'insider language', 'named brand', 'pattern recognition', 'question'."
        )
    )
    text: str = Field(description="The hook itself, ≤15 words.")
    character_count: int
    why_it_works: str = Field(
        description="1-2 sentences on the format mechanics — why this hook drives the primary metric."
    )


class SlideOrShot(BaseModel):
    """One slide of a carousel, or one shot of a reel. Mix as appropriate."""

    sequence_number: int = Field(ge=1)
    timestamp_or_slide: str = Field(
        description='Reel: "0:00-0:03". Carousel: "Slide 1". Story: "Frame 1".'
    )
    visual_concept: str = Field(
        description="Composition, B-roll, key imagery. What's literally on screen."
    )
    headline: str = Field(
        description="Large on-screen text or slide headline. ≤8 words for carousel."
    )
    body_copy: str = Field(
        description="Smaller body text on the slide, or '' for reel shots without body copy."
    )
    voiceover: str = Field(
        description="Literal spoken words for video shots. '' for static carousel slides."
    )
    design_notes: str = Field(
        description="Specific design: colors, typography weight, layout grid, motion notes."
    )


class HashtagTier(BaseModel):
    tier: Literal["broad", "niche", "branded"]
    tags: list[str] = Field(
        min_length=1,
        description="Hashtags WITHOUT the # prefix. e.g. ['indianstartups', 'saas'].",
    )
    rationale: str = Field(
        description="Why these tags at this tier — reach vs. relevance trade-off."
    )


class CaptionDraft(BaseModel):
    label: Literal["primary", "alt_1", "alt_2"]
    full_text: str = Field(
        description="The complete caption. Use \\n for line breaks."
    )
    first_line_hook: str = Field(
        description=(
            "The opening line that shows above Instagram's 'Read More' fold. "
            "Should be a strong standalone hook."
        )
    )
    word_count: int


class InstagramBrief(BaseModel):
    """A production-ready, schema-compliant Instagram brief.

    Every field is required. Source URLs MUST come from the upstream
    RawItem/RankedTopic cluster — never invent URLs.
    """

    # ---- Strategic frame ----
    topic_line: str = Field(description="Topic restated in one line.")
    one_line_thesis: str = Field(
        description=(
            "The single-sentence reason this content exists. The 'so what'. "
            "Sharp, specific, no fluff."
        )
    )
    target_subaudience: str = Field(
        description=(
            "Who specifically inside the broader 'Indian early-stage founder' "
            "umbrella this is for. e.g. 'Pre-seed B2B SaaS founders in years 1-2 "
            "navigating their first cap table.'"
        )
    )
    why_now: str = Field(
        description=(
            "What makes this timely THIS WEEK — a regulatory change, a high-profile "
            "fundraise, a market shift mentioned in the source articles."
        )
    )
    primary_goal: PrimaryGoal

    # ---- Format & specs ----
    format: InstagramFormat
    header: str = Field(
        description="'Content Brief — Instagram <Format> | Goal: <Goal> | Audience: <Audience>'"
    )
    specs: str = Field(
        description=(
            "Pipe-separated. e.g. 'Duration: 30-45s | Aspect Ratio: 9:16 | "
            "Hook: 0-3s | Hashtag Count: 5'"
        )
    )

    # ---- Fact-check & sourcing ----
    fact_check_status: Literal["Verified", "Evergreen", "Unverified"]
    fact_check_note: str
    source_citations: list[SourceCitation] = Field(
        min_length=1,
        description=(
            "At least one real source URL drawn from the upstream cluster. "
            "NEVER invent URLs. If the cluster has only one item, cite that one."
        ),
    )

    # ---- The brief proper ----
    hooks: list[HookOption] = Field(min_length=3, max_length=3)
    slides_or_shots: list[SlideOrShot] = Field(min_length=3)
    captions: list[CaptionDraft] = Field(
        min_length=2,
        max_length=3,
        description="At least 2 caption drafts: a primary plus 1-2 alts.",
    )
    hashtag_tiers: list[HashtagTier] = Field(
        min_length=2,
        description="At least 2 tiers (broad + niche). Branded tier optional.",
    )

    # ---- CTA playbook (multiple options for different goals) ----
    primary_cta: str = Field(description="The CTA matched to the primary goal.")
    save_cta: str = Field(description="Variant for save-driven posts.")
    share_cta: str = Field(description="Variant for share-driven posts.")
    follow_cta: str = Field(description="Variant for follow-driven posts.")
    comment_cta: str = Field(description="Variant for comment-driven posts.")

    # ---- Audio & visual identity ----
    audio_recommendation: str = Field(
        description=(
            "For reels: trending audio name, mood, tempo, why it fits. "
            "For static/carousel: 'No audio' or 'Original audio' with note."
        )
    )
    visual_design_notes: str = Field(
        description=(
            "Brand-level: color palette (with hex codes), typography pairing, "
            "layout grid, recurring visual motif."
        )
    )

    # ---- Production & launch ----
    posting_strategy: str = Field(
        description=(
            "Best time IST, best day(s), posting frequency for this pillar, "
            "story tease plan if applicable."
        )
    )
    engagement_playbook: str = Field(
        description=(
            "Specific moves for the first 60 minutes after posting: pinned-comment "
            "copy, reply themes, follow-up post idea."
        )
    )

    # ---- Multipliers ----
    cross_platform_adaptation: str = Field(
        description=(
            "How to repurpose this brief: LinkedIn carousel/post text, X thread "
            "first tweet, YouTube Shorts hook. Concrete drafts."
        )
    )
    success_criteria: str = Field(
        description=(
            "What success looks like in plain language: target saves rate, watch "
            "time, reach band. Numbers grounded in the format mechanics."
        )
    )


class InstagramBriefBatch(BaseModel):
    briefs: list[InstagramBrief] = Field(min_length=3)
