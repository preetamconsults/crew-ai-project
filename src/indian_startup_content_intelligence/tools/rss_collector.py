"""RSS feed collector for Indian startup ecosystem sources.

Replaces the previous single-page Inc42 scrape with a multi-source RSS fetch.
Returns deterministic, deduplicated, time-bounded items so the source-scout
agent doesn't have to invent or guess content.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Type

import feedparser
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


DEFAULT_INDIAN_STARTUP_FEEDS: list[str] = [
    "https://inc42.com/feed/",
    "https://yourstory.com/feed/",
    "https://entrackr.com/feed/",
    "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
]


class RSSFeedCollectorInput(BaseModel):
    """Input schema for the RSS feed collector tool."""

    feed_urls: list[str] = Field(
        default_factory=lambda: list(DEFAULT_INDIAN_STARTUP_FEEDS),
        description=(
            "RSS feed URLs to fetch. Defaults to Inc42, YourStory, Entrackr, "
            "and ET Tech."
        ),
    )
    hours_back: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Only include items published within this many hours.",
    )
    max_items_per_feed: int = Field(
        default=8,
        ge=1,
        le=25,
        description="Cap items pulled per feed to avoid prompt bloat.",
    )


class RSSFeedCollectorTool(BaseTool):
    """Fetches recent articles across multiple RSS feeds.

    Returns a JSON array of {title, brief_description, url, source, published}.
    Items lacking a publish timestamp are kept (some feeds omit it) but
    items older than `hours_back` are dropped when a timestamp is present.
    """

    name: str = "rss_feed_collector"
    description: str = (
        "Fetches recent articles from one or more RSS feeds and returns a "
        "JSON list of {title, brief_description, url, source, published} "
        "items. Use this to collect Indian startup ecosystem content from "
        "Inc42, YourStory, Entrackr, ET Tech, etc."
    )
    args_schema: Type[BaseModel] = RSSFeedCollectorInput

    def _run(
        self,
        feed_urls: list[str] | None = None,
        hours_back: int = 24,
        max_items_per_feed: int = 8,
    ) -> str:
        urls = feed_urls or list(DEFAULT_INDIAN_STARTUP_FEEDS)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        results: list[dict] = []
        seen_urls: set[str] = set()

        for url in urls:
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                results.append({"_error": f"parse failed for {url}: {exc}"})
                continue

            source = (feed.feed.get("title") if hasattr(feed, "feed") else "") or url
            count = 0

            for entry in feed.entries:
                if count >= max_items_per_feed:
                    break

                item_url = (entry.get("link") or "").strip()
                if not item_url or item_url in seen_urls:
                    continue

                published_str = ""
                published_parsed = entry.get("published_parsed") or entry.get(
                    "updated_parsed"
                )
                if published_parsed:
                    published_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                    if published_dt < cutoff:
                        continue
                    published_str = published_dt.isoformat()

                summary_raw = entry.get("summary") or entry.get("description") or ""
                summary = re.sub(r"<[^>]+>", "", summary_raw).strip()
                summary = re.sub(r"\s+", " ", summary)
                if len(summary) > 280:
                    summary = summary[:277] + "..."

                results.append(
                    {
                        "title": (entry.get("title") or "").strip(),
                        "brief_description": summary,
                        "url": item_url,
                        "source": source,
                        "published": published_str,
                    }
                )
                seen_urls.add(item_url)
                count += 1

        return json.dumps(results, ensure_ascii=False, indent=2)
