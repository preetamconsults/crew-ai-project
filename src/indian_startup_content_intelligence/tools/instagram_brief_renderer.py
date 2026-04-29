"""Deterministic renderer: InstagramBriefBatch → polished HTML production document.

The previous pipeline asked an LLM to re-serialize structured briefs into
markdown and then into HTML, which let the model mangle ordering, hashtag
counts, and slide structure. This module renders directly from the typed
Pydantic batch with no LLM in the loop, so the output is byte-stable for a
given input.
"""

from __future__ import annotations

import html as html_module
import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from indian_startup_content_intelligence.models import (
    InstagramBrief,
    InstagramBriefBatch,
)


# ---------- HTML rendering ----------

_CSS = """
  :root {
    --ink: #0f172a;
    --muted: #64748b;
    --accent: #1f4e79;
    --accent-soft: #eaf1f8;
    --accent-deep: #143a5e;
    --rule: #e2e8f0;
    --rule-strong: #cbd5e1;
    --bg: #ffffff;
    --bg-alt: #f8fafc;
    --tag-bg: #f1f5f9;
    --hook-bg: #fff8e6;
    --caption-bg: #f0fbf4;
    --good: #1e7c3a;
    --warn: #8a6300;
    --bad: #a31d1d;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', 'Calibri', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: var(--ink);
    background: var(--bg);
    max-width: 9in;
    margin: 0.5in auto;
    padding: 0.4in 0.7in;
  }
  header.doc {
    border-bottom: 4px solid var(--accent);
    padding-bottom: 14pt;
    margin-bottom: 24pt;
  }
  header.doc h1 {
    font-size: 26pt;
    font-weight: 800;
    color: var(--accent);
    margin: 0;
    letter-spacing: -0.4pt;
  }
  header.doc .subtitle {
    color: var(--muted);
    font-size: 10.5pt;
    margin-top: 6pt;
  }

  nav.toc {
    background: var(--accent-soft);
    border-radius: 8pt;
    padding: 16pt 22pt;
    margin-bottom: 28pt;
  }
  nav.toc h2 {
    margin: 0 0 10pt 0;
    color: var(--accent);
    font-size: 11pt;
    text-transform: uppercase;
    letter-spacing: 0.6pt;
  }
  nav.toc ol { margin: 0; padding-left: 22pt; }
  nav.toc li { margin-bottom: 5pt; }
  nav.toc a {
    color: var(--ink);
    text-decoration: none;
    font-weight: 600;
  }
  nav.toc a:hover { text-decoration: underline; }
  nav.toc .meta {
    color: var(--muted);
    font-size: 10pt;
    margin-left: 6pt;
  }

  article.brief {
    border: 1px solid var(--rule);
    border-radius: 10pt;
    padding: 22pt 28pt;
    margin-bottom: 32pt;
    background: var(--bg);
    page-break-after: always;
  }
  article.brief > h2 {
    font-size: 18pt;
    color: var(--accent);
    margin: 0 0 8pt 0;
    line-height: 1.3;
  }
  article.brief > .brief-id {
    color: var(--muted);
    font-size: 10pt;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin-bottom: 16pt;
  }

  /* Strategic frame */
  .strategic-frame {
    background: var(--bg-alt);
    border-left: 4px solid var(--accent);
    border-radius: 6pt;
    padding: 16pt 20pt;
    margin: 14pt 0 22pt 0;
  }
  .strategic-frame .thesis {
    font-size: 13pt;
    font-weight: 600;
    color: var(--accent-deep);
    margin: 0 0 14pt 0;
    line-height: 1.45;
    border-left: none;
    padding-left: 0;
  }
  .frame-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12pt 22pt;
  }
  .frame-grid .label {
    display: block;
    color: var(--muted);
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin-bottom: 3pt;
  }
  .frame-grid .v {
    color: var(--ink);
  }

  section {
    margin: 22pt 0;
    padding-top: 14pt;
    border-top: 1px solid var(--rule);
  }
  section > h3 {
    font-size: 11pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.6pt;
    color: var(--accent);
    margin: 0 0 10pt 0;
  }
  section .body { margin: 0; }

  p { margin: 0 0 8pt 0; }
  ul, ol { margin: 6pt 0 8pt 0; padding-left: 22pt; }
  li { margin-bottom: 5pt; }

  /* Pills & badges */
  .pill {
    display: inline-block;
    padding: 2pt 9pt;
    border-radius: 999pt;
    font-size: 9.5pt;
    font-weight: 700;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .pill.verified { background: #e6f4ea; color: var(--good); }
  .pill.evergreen { background: #fff4d6; color: var(--warn); }
  .pill.unverified { background: #fde2e2; color: var(--bad); }
  .pill.format-reel { background: #fde6f3; color: #9a2266; }
  .pill.format-carousel { background: #e0ecff; color: #1d4ed8; }
  .pill.format-story { background: #fff4e0; color: #b45309; }
  .pill.format-static { background: #ecfdf5; color: #047857; }
  .pill.goal {
    background: var(--accent-deep);
    color: #fff;
  }

  /* Specs */
  .specs-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6pt 18pt;
    margin: 6pt 0;
  }
  .specs-grid .k { color: var(--muted); font-size: 10pt; }
  .specs-grid .v { font-weight: 600; }

  /* Sources */
  ul.sources { padding-left: 22pt; }
  ul.sources li { margin-bottom: 8pt; }
  ul.sources a {
    color: var(--accent);
    font-weight: 600;
    text-decoration: none;
  }
  ul.sources a:hover { text-decoration: underline; }
  ul.sources .meta {
    color: var(--muted);
    font-size: 9.5pt;
    display: block;
    margin-top: 1pt;
  }

  /* Hooks */
  .hooks-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10pt;
  }
  .hook-card {
    background: var(--hook-bg);
    border-left: 3px solid #d97706;
    border-radius: 4pt;
    padding: 10pt 14pt;
  }
  .hook-card .hook-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6pt;
  }
  .hook-card .hook-label {
    background: #d97706;
    color: #fff;
    width: 22pt;
    height: 22pt;
    border-radius: 999pt;
    text-align: center;
    line-height: 22pt;
    font-weight: 800;
    display: inline-block;
    margin-right: 8pt;
  }
  .hook-card .hook-angle {
    color: var(--muted);
    font-size: 9.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
  }
  .hook-card .hook-text {
    font-size: 12.5pt;
    font-weight: 700;
    line-height: 1.4;
    margin: 4pt 0 8pt 0;
    color: var(--ink);
  }
  .hook-card .hook-meta {
    font-size: 9.5pt;
    color: var(--muted);
    margin-bottom: 6pt;
  }
  .hook-card .hook-rationale {
    font-size: 10pt;
    color: var(--ink);
    margin: 0;
    font-style: italic;
  }

  /* Slide / shot table */
  table.shot-list {
    border-collapse: collapse;
    width: 100%;
    margin: 8pt 0;
    font-size: 10pt;
  }
  table.shot-list th {
    background: var(--accent-soft);
    color: var(--accent);
    text-align: left;
    padding: 7pt 9pt;
    font-weight: 700;
    border: 1px solid var(--rule);
    text-transform: uppercase;
    font-size: 9pt;
    letter-spacing: 0.4pt;
  }
  table.shot-list td {
    padding: 8pt 9pt;
    border: 1px solid var(--rule);
    vertical-align: top;
  }
  table.shot-list .seq {
    font-weight: 800;
    color: var(--accent);
    text-align: center;
    background: var(--bg-alt);
  }
  table.shot-list tr:nth-child(even) td:not(.seq) { background: #fafbfc; }
  table.shot-list .design {
    color: var(--muted);
    font-size: 9pt;
    margin-top: 4pt;
    border-top: 1px dashed var(--rule);
    padding-top: 4pt;
  }

  /* Captions */
  .caption-card {
    background: var(--caption-bg);
    border-left: 3px solid var(--good);
    border-radius: 4pt;
    padding: 12pt 16pt;
    margin-bottom: 10pt;
  }
  .caption-card .caption-label {
    display: inline-block;
    background: var(--good);
    color: #fff;
    padding: 2pt 9pt;
    border-radius: 999pt;
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin-bottom: 6pt;
  }
  .caption-card .first-line {
    font-weight: 700;
    font-size: 11.5pt;
    margin: 4pt 0 8pt 0;
    color: var(--ink);
  }
  .caption-card .full-text {
    white-space: pre-wrap;
    margin: 0 0 8pt 0;
    font-family: Georgia, 'Iowan Old Style', serif;
    font-size: 11pt;
    line-height: 1.55;
    color: var(--ink);
  }
  .caption-card .meta {
    color: var(--muted);
    font-size: 9pt;
    text-align: right;
  }

  /* Hashtags */
  .hashtag-tier {
    background: var(--tag-bg);
    border-radius: 5pt;
    padding: 10pt 14pt;
    margin-bottom: 8pt;
  }
  .hashtag-tier .tier-label {
    display: inline-block;
    padding: 2pt 9pt;
    border-radius: 999pt;
    font-size: 8.5pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin-bottom: 6pt;
  }
  .hashtag-tier .tier-broad { background: #1d4ed8; color: #fff; }
  .hashtag-tier .tier-niche { background: #047857; color: #fff; }
  .hashtag-tier .tier-branded { background: #9a2266; color: #fff; }
  .hashtag-tier .tags {
    color: var(--accent);
    font-weight: 700;
    margin: 4pt 0 4pt 0;
  }
  .hashtag-tier .rationale {
    color: var(--muted);
    font-size: 9.5pt;
    font-style: italic;
    margin: 0;
  }

  /* CTA playbook */
  .cta-primary {
    background: var(--accent);
    color: #fff;
    padding: 12pt 16pt;
    border-radius: 6pt;
    margin-bottom: 10pt;
    font-weight: 600;
    font-size: 11.5pt;
  }
  .cta-primary .label {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    padding: 1pt 8pt;
    border-radius: 999pt;
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin-right: 8pt;
  }
  .cta-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8pt;
  }
  .cta-grid .cta-cell {
    background: var(--bg-alt);
    border: 1px solid var(--rule);
    border-radius: 4pt;
    padding: 8pt 12pt;
  }
  .cta-grid .label {
    display: block;
    color: var(--muted);
    font-size: 8.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin-bottom: 3pt;
  }

  /* Multiline text blocks */
  .text-block {
    white-space: pre-wrap;
    margin: 0;
    line-height: 1.6;
  }

  footer.doc {
    border-top: 1px solid var(--rule);
    padding-top: 12pt;
    margin-top: 30pt;
    color: var(--muted);
    font-size: 9.5pt;
    text-align: center;
  }

  @media print {
    body { margin: 0.4in; padding: 0; max-width: none; }
    article.brief { page-break-after: always; box-shadow: none; }
    nav.toc { page-break-after: always; }
  }
"""


def _esc(value: str) -> str:
    return html_module.escape(str(value or ""), quote=True)


def _format_label(brief: InstagramBrief) -> str:
    return brief.format.capitalize()


def _fact_check_pill(status: str, note: str) -> str:
    cls = status.lower()
    return (
        f'<span class="pill {_esc(cls)}">{_esc(status)}</span> '
        f'<span>{_esc(note)}</span>'
    )


def _render_specs(specs_text: str) -> str:
    parts = [p.strip() for p in specs_text.split("|") if p.strip()]
    if len(parts) <= 1:
        return f'<p class="body">{_esc(specs_text)}</p>'
    rows = []
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
            rows.append(
                f'<div class="k">{_esc(k.strip())}</div>'
                f'<div class="v">{_esc(v.strip())}</div>'
            )
        else:
            rows.append(f'<div class="k">·</div><div class="v">{_esc(part)}</div>')
    return f'<div class="specs-grid">{"".join(rows)}</div>'


def _render_strategic_frame(brief: InstagramBrief) -> str:
    return f"""
    <div class="strategic-frame">
      <p class="thesis">{_esc(brief.one_line_thesis)}</p>
      <div class="frame-grid">
        <div>
          <span class="label">Target Subaudience</span>
          <span class="v">{_esc(brief.target_subaudience)}</span>
        </div>
        <div>
          <span class="label">Why Now</span>
          <span class="v">{_esc(brief.why_now)}</span>
        </div>
        <div>
          <span class="label">Primary Goal</span>
          <span class="v"><span class="pill goal">{_esc(brief.primary_goal)}</span></span>
        </div>
        <div>
          <span class="label">Format</span>
          <span class="v"><span class="pill format-{_esc(brief.format)}">{_esc(_format_label(brief))}</span></span>
        </div>
      </div>
    </div>
    """


def _render_sources(brief: InstagramBrief) -> str:
    items = []
    for cite in brief.source_citations:
        items.append(
            f'<li>'
            f'<a href="{_esc(cite.url)}" target="_blank" rel="noopener">{_esc(cite.title)}</a>'
            f'<span class="meta">{_esc(cite.source)} · {_esc(cite.relevance_note)}</span>'
            f'</li>'
        )
    return f'<ul class="sources">{"".join(items)}</ul>'


def _render_hooks(brief: InstagramBrief) -> str:
    cards = []
    for hook in brief.hooks:
        cards.append(f"""
        <div class="hook-card">
          <div class="hook-head">
            <div>
              <span class="hook-label">{_esc(hook.label)}</span>
              <span class="hook-angle">{_esc(hook.angle)}</span>
            </div>
          </div>
          <p class="hook-text">{_esc(hook.text)}</p>
          <p class="hook-meta">{hook.character_count} chars</p>
          <p class="hook-rationale">{_esc(hook.why_it_works)}</p>
        </div>
        """)
    return f'<div class="hooks-grid">{"".join(cards)}</div>'


def _render_shot_list(brief: InstagramBrief) -> str:
    rows = []
    for shot in brief.slides_or_shots:
        rows.append(
            "<tr>"
            f"<td class='seq'>{shot.sequence_number}</td>"
            f"<td><strong>{_esc(shot.timestamp_or_slide)}</strong><br>{_esc(shot.visual_concept)}<br>"
            f"<div class='design'>{_esc(shot.design_notes)}</div></td>"
            f"<td>{_esc(shot.headline)}</td>"
            f"<td>{_esc(shot.body_copy) or '<span style=\"color:#9ca3af\">—</span>'}</td>"
            f"<td>{_esc(shot.voiceover) or '<span style=\"color:#9ca3af\">—</span>'}</td>"
            "</tr>"
        )
    return f"""
    <table class="shot-list">
      <thead>
        <tr>
          <th style="width:32pt">#</th>
          <th>Visual / Design</th>
          <th>Headline</th>
          <th>Body</th>
          <th>Voiceover</th>
        </tr>
      </thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    """


def _render_captions(brief: InstagramBrief) -> str:
    cards = []
    for cap in brief.captions:
        cards.append(f"""
        <div class="caption-card">
          <span class="caption-label">{_esc(cap.label)}</span>
          <p class="first-line">{_esc(cap.first_line_hook)}</p>
          <p class="full-text">{_esc(cap.full_text)}</p>
          <p class="meta">{cap.word_count} words</p>
        </div>
        """)
    return "".join(cards)


def _render_hashtags(brief: InstagramBrief) -> str:
    blocks = []
    for tier in brief.hashtag_tiers:
        tags = " ".join(f"#{_esc(t.lstrip('#'))}" for t in tier.tags)
        blocks.append(f"""
        <div class="hashtag-tier">
          <span class="tier-label tier-{_esc(tier.tier)}">{_esc(tier.tier)}</span>
          <p class="tags">{tags}</p>
          <p class="rationale">{_esc(tier.rationale)}</p>
        </div>
        """)
    return "".join(blocks)


def _render_cta_playbook(brief: InstagramBrief) -> str:
    return f"""
    <div class="cta-primary">
      <span class="label">Primary</span>
      {_esc(brief.primary_cta)}
    </div>
    <div class="cta-grid">
      <div class="cta-cell">
        <span class="label">Save</span>
        {_esc(brief.save_cta)}
      </div>
      <div class="cta-cell">
        <span class="label">Share</span>
        {_esc(brief.share_cta)}
      </div>
      <div class="cta-cell">
        <span class="label">Follow</span>
        {_esc(brief.follow_cta)}
      </div>
      <div class="cta-cell">
        <span class="label">Comment</span>
        {_esc(brief.comment_cta)}
      </div>
    </div>
    """


def _render_brief(brief: InstagramBrief, idx: int) -> str:
    return f"""
    <article class="brief" id="brief-{idx}">
      <h2>{_esc(brief.topic_line)}</h2>
      <div class="brief-id">Brief #{idx}</div>

      {_render_strategic_frame(brief)}

      <section>
        <h3>📋 Specs &amp; Fact-Check</h3>
        <p class="body"><strong>{_esc(brief.header)}</strong></p>
        {_render_specs(brief.specs)}
        <p class="body" style="margin-top:8pt">{_fact_check_pill(brief.fact_check_status, brief.fact_check_note)}</p>
      </section>

      <section>
        <h3>📚 Sources Cited</h3>
        {_render_sources(brief)}
      </section>

      <section>
        <h3>🎣 Hook Options</h3>
        {_render_hooks(brief)}
      </section>

      <section>
        <h3>🎬 Slide / Shot Blueprint</h3>
        {_render_shot_list(brief)}
      </section>

      <section>
        <h3>✏️ Caption Drafts</h3>
        {_render_captions(brief)}
      </section>

      <section>
        <h3># Hashtag Strategy</h3>
        {_render_hashtags(brief)}
      </section>

      <section>
        <h3>📣 CTA Playbook</h3>
        {_render_cta_playbook(brief)}
      </section>

      <section>
        <h3>🎵 Audio Recommendation</h3>
        <p class="body text-block">{_esc(brief.audio_recommendation)}</p>
      </section>

      <section>
        <h3>🎨 Visual Design Notes</h3>
        <p class="body text-block">{_esc(brief.visual_design_notes)}</p>
      </section>

      <section>
        <h3>⏰ Posting Strategy</h3>
        <p class="body text-block">{_esc(brief.posting_strategy)}</p>
      </section>

      <section>
        <h3>🤝 Engagement Playbook</h3>
        <p class="body text-block">{_esc(brief.engagement_playbook)}</p>
      </section>

      <section>
        <h3>🔄 Cross-Platform Adaptation</h3>
        <p class="body text-block">{_esc(brief.cross_platform_adaptation)}</p>
      </section>

      <section>
        <h3>✅ Success Criteria</h3>
        <p class="body text-block">{_esc(brief.success_criteria)}</p>
      </section>
    </article>
    """


def _render_toc(batch: InstagramBriefBatch) -> str:
    items = []
    for i, b in enumerate(batch.briefs, start=1):
        items.append(
            f'<li><a href="#brief-{i}">{_esc(b.topic_line)}</a>'
            f'<span class="meta"> — {_esc(_format_label(b))}'
            f' · Goal: {_esc(b.primary_goal)}'
            f' · {_esc(b.fact_check_status)}</span></li>'
        )
    return (
        '<nav class="toc">'
        '<h2>Briefs in this document</h2>'
        f'<ol>{"".join(items)}</ol>'
        '</nav>'
    )


def render_briefs_to_html(
    batch: InstagramBriefBatch,
    *,
    title: str = "Instagram Content Briefs — Indian Founder Edition",
) -> str:
    briefs_html = "".join(
        _render_brief(b, i) for i, b in enumerate(batch.briefs, start=1)
    )
    count = len(batch.briefs)
    plural = "s" if count != 1 else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
  <style>{_CSS}</style>
</head>
<body>
  <header class="doc">
    <h1>{_esc(title)}</h1>
    <div class="subtitle">{count} production-ready Instagram brief{plural} · For Indian early-stage SaaS / B2B founders · Generated by the Indian Startup Content Intelligence Crew</div>
  </header>
  {_render_toc(batch)}
  {briefs_html}
  <footer class="doc">
    Open this file in your browser, or open it directly in Microsoft Word. Every claim cites a real source URL — verify before publishing.
  </footer>
</body>
</html>
"""


# ---------- Tool wrapper for the document_generation_specialist agent ----------

class InstagramBriefRendererInput(BaseModel):
    briefs_json: str = Field(
        ...,
        description=(
            "JSON string of an InstagramBriefBatch — pass the previous task's "
            "structured output verbatim."
        ),
    )


class InstagramBriefRendererTool(BaseTool):
    """Renders an InstagramBriefBatch JSON into a polished HTML production document."""

    name: str = "instagram_brief_renderer"
    description: str = (
        "Renders an InstagramBriefBatch JSON string into a complete, "
        "professionally styled HTML production document with embedded CSS. "
        "Output opens directly in any browser and imports cleanly into "
        "Microsoft Word. Pass the previous task's InstagramBriefBatch output "
        "as briefs_json. Return the tool's output verbatim — never edit it."
    )
    args_schema: Type[BaseModel] = InstagramBriefRendererInput

    def _run(self, briefs_json: str) -> str:
        try:
            batch = InstagramBriefBatch.model_validate_json(briefs_json)
        except Exception:
            try:
                data = json.loads(briefs_json)
                batch = InstagramBriefBatch.model_validate(data)
            except Exception as exc:
                return (
                    "<!DOCTYPE html><html><body>"
                    f"<h1>Render error</h1><pre>{html_module.escape(str(exc))}</pre>"
                    f"<pre>{html_module.escape(briefs_json[:1500])}</pre>"
                    "</body></html>"
                )
        return render_briefs_to_html(batch)
