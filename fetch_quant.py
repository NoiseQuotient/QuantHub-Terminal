#!/usr/bin/env python3
"""
QuantHub-Terminal: Quantitative Finance Research Aggregator & Summarizer
Scrapes arXiv, RSS feeds, and GitHub trending repos, then uses LLM to summarize and rank.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import feedparser
import requests
from github import Github
import arxiv
import yaml

# LLM imports
try:
    import openai
    LLM_BACKEND = "openai"
except ImportError:
    LLM_BACKEND = "none"

# Configuration
CONFIG = {
    "arxiv_categories": ["cs.CE", "q-fin.CP", "q-fin.ST", "q-fin.PR", "q-fin.TR"],
    "rss_feeds": [
        # Quant‑specific (full content often available)
        "https://www.risk.net/feed/rss",
        "https://papers.ssrn.com/sol3/DisplayAbstractSearch.cfm?feed=rss",
        "https://www.bloomberg.com/quant/feed",
        
        # Mainstream finance (headlines + snippets)
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
        "https://www.ft.com/rss/markets",  # FT Markets
        "https://www.economist.com/finance-and-economics/rss.xml",  # Economist Finance
        "https://www.bloomberg.com/markets/rss.xml",  # Bloomberg Markets
        "https://www.reutersagency.com/feed/?best-topics=financial-regulatory&post_type=best",  # Reuters Financial
    ],
    "github_topics": ["quantitative-finance", "algorithmic-trading", "risk-modeling"],
    "output_dir": "_data",
    "max_papers_per_source": 15,
    "max_news_per_feed": 8,
    "days_lookback": 7,
}

# LLM configuration (set via environment variables)
LLM_CONFIG = {
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY"),
    "model": os.getenv("LLM_MODEL", "deepseek-chat"),  # or "gpt-4o-mini"
    "max_tokens": 500,
    "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QuantScraper:
    """Main scraper class for quantitative finance sources."""

    def __init__(self):
        self.results = []
        self.seen_ids = set()
        self.github = None
        if os.getenv("GITHUB_TOKEN"):
            self.github = Github(os.getenv("GITHUB_TOKEN"))

    def fetch_arxiv(self) -> List[Dict[str, Any]]:
        """Fetch recent papers from arXiv quant categories."""
        papers = []
        client = arxiv.Client()
        cutoff_date = datetime.now() - timedelta(days=CONFIG["days_lookback"])

        for category in CONFIG["arxiv_categories"]:
            query = f"cat:{category}"
            search = arxiv.Search(
                query=query,
                max_results=CONFIG["max_papers_per_source"],
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            try:
                for result in client.results(search):
                    if result.published.date() < cutoff_date.date():
                        continue
                    paper_id = result.entry_id.split("/")[-1]
                    if paper_id in self.seen_ids:
                        continue
                    self.seen_ids.add(paper_id)
                    papers.append({
                        "id": paper_id,
                        "source": "arxiv",
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "abstract": result.summary,
                        "published": result.published.isoformat(),
                        "url": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "categories": result.categories,
                        "primary_category": result.primary_category,
                    })
            except Exception as e:
                logger.error(f"arXiv error for {category}: {e}")
        logger.info(f"Fetched {len(papers)} arXiv papers.")
        return papers

    def fetch_rss(self) -> List[Dict[str, Any]]:
        """Parse RSS feeds from quant and mainstream finance sources."""
        articles = []
        for feed_url in CONFIG["rss_feeds"]:
            try:
                parsed = feedparser.parse(feed_url)
                limit = CONFIG["max_papers_per_source"] if "quant" in feed_url or "ssrn" in feed_url or "risk" in feed_url else CONFIG["max_news_per_feed"]
                for entry in parsed.entries[:limit]:
                    article_id = entry.get("id", entry.get("link", ""))
                    if article_id in self.seen_ids:
                        continue
                    self.seen_ids.add(article_id)
                    
                    # Categorize source
                    source_type = "quant"
                    if any(x in feed_url for x in ["wsj", "ft.com", "economist", "bloomberg.com/markets", "reuters"]):
                        source_type = "news"
                    
                    articles.append({
                        "id": article_id[:100],
                        "source": feed_url,
                        "source_type": source_type,
                        "title": entry.get("title", "No title"),
                        "summary": entry.get("summary", entry.get("description", "")),
                        "published": entry.get("published", entry.get("updated", "")),
                        "url": entry.get("link", ""),
                        "author": entry.get("author", ""),
                    })
            except Exception as e:
                logger.error(f"RSS error for {feed_url}: {e}")
        logger.info(f"Fetched {len(articles)} RSS articles.")
        return articles

    def fetch_github_trending(self) -> List[Dict[str, Any]]:
        """Find trending GitHub repos in quantitative finance topics."""
        repos = []
        if not self.github:
            logger.warning("No GitHub token provided; skipping GitHub trending.")
            return repos

        for topic in CONFIG["github_topics"]:
            try:
                # Search repos with topic, sorted by stars
                query = f"topic:{topic}"
                result = self.github.search_repositories(query, sort="stars", order="desc")
                for repo in result[:CONFIG["max_papers_per_source"]]:
                    repo_id = str(repo.id)
                    if repo_id in self.seen_ids:
                        continue
                    self.seen_ids.add(repo_id)
                    repos.append({
                        "id": repo_id,
                        "source": "github",
                        "title": repo.name,
                        "description": repo.description or "",
                        "url": repo.html_url,
                        "stars": repo.stargazers_count,
                        "forks": repo.forks_count,
                        "updated": repo.updated_at.isoformat(),
                        "language": repo.language,
                        "topics": repo.topics,
                    })
            except Exception as e:
                logger.error(f"GitHub error for topic {topic}: {e}")
        logger.info(f"Fetched {len(repos)} GitHub repos.")
        return repos

    def summarize_with_llm(self, text: str, title: str) -> Dict[str, Any]:
        """
        Use LLM to generate a 3‑bullet summary and relevance score.
        Supports OpenAI, DeepSeek, or fallback.
        """
        prompt = f"""
        You are a quantitative finance expert. Summarize the following research:

        Title: {title}

        Abstract/Text: {text[:2000]}

        Provide:
        1. **The Core Idea** (one sentence)
        2. **The Methodology** (one sentence)
        3. **Key Quant Impact** (one sentence)
        4. **Relevance Score** (1‑10, where 1=theoretical/academic, 10=immediate trading/risk applicability)

        Return JSON with keys: core_idea, methodology, quant_impact, relevance_score.
        """
        
        # Try DeepSeek first (free)
        if LLM_CONFIG["deepseek_api_key"]:
            try:
                client = openai.OpenAI(
                    api_key=LLM_CONFIG["deepseek_api_key"],
                    base_url=LLM_CONFIG["base_url"]
                )
                response = client.chat.completions.create(
                    model=LLM_CONFIG["model"],
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=LLM_CONFIG["max_tokens"],
                    temperature=0.2,
                )
                content = response.choices[0].message.content.strip()
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                logger.info("DeepSeek summarization succeeded")
            except Exception as e:
                logger.error(f"DeepSeek summarization failed: {e}")
        
        # Fallback to OpenAI
        elif LLM_BACKEND == "openai" and LLM_CONFIG["openai_api_key"]:
            openai.api_key = LLM_CONFIG["openai_api_key"]
            try:
                response = openai.chat.completions.create(
                    model=LLM_CONFIG["model"],
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=LLM_CONFIG["max_tokens"],
                    temperature=0.2,
                )
                content = response.choices[0].message.content.strip()
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.error(f"OpenAI summarization failed: {e}")

        # Fallback: simple extraction
        sentences = text.split(". ")
        return {
            "core_idea": sentences[0] if sentences else "No core idea extracted.",
            "methodology": sentences[1] if len(sentences) > 1 else "No methodology extracted.",
            "quant_impact": sentences[2] if len(sentences) > 2 else "No quant impact extracted.",
            "relevance_score": 5,  # neutral fallback
        }

    def calculate_ranking_score(self, item: Dict[str, Any]) -> float:
        """Compute a weighted ranking score (0‑100)."""
        relevance = item.get("relevance_score", 5)
        
        # Recency: newer is better (within last 7 days)
        published_str = item.get("published", "")
        try:
            pub_date = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            days_ago = (datetime.now(pub_date.tzinfo) - pub_date).days
            recency = max(0, 1 - days_ago / 7)  # 1 if today, 0 if ≥7 days
        except:
            recency = 0.5

        # Source type weight (prioritize quant over general news)
        source_type = item.get("source_type", "quant")
        type_weights = {"quant": 1.0, "news": 0.7, "arxiv": 1.0, "github": 0.9}
        type_weight = type_weights.get(source_type, 0.8)
        
        # Specific source boosts
        source = item.get("source", "")
        source_boost = 1.0
        if "arxiv" in source:
            source_boost = 1.1  # Academic papers
        elif "risk.net" in source:
            source_boost = 1.05  # Risk professional
        elif "ssrn" in source:
            source_boost = 1.05  # Working papers
        elif "github" in source:
            source_boost = 0.9 + min(0.2, item.get("stars", 0) / 5000)  # GitHub stars

        # GitHub stars boost (if applicable)
        star_boost = 0
        if source_type == "github":
            stars = item.get("stars", 0)
            star_boost = min(0.5, stars / 2000)  # normalize

        # Final score: 50% relevance, 30% recency, 15% source quality, 5% stars
        score = (0.5 * relevance * 10 + 
                 0.3 * recency * 10 + 
                 0.15 * type_weight * 10 * source_boost + 
                 star_boost * 5)
        return min(100, score)

    def run(self):
        """Execute full scraping → summarization → ranking pipeline."""
        logger.info("Starting QuantHub scraper...")

        # Fetch data
        arxiv_papers = self.fetch_arxiv()
        rss_articles = self.fetch_rss()
        github_repos = self.fetch_github_trending()

        all_items = arxiv_papers + rss_articles + github_repos

        # Summarize and rank
        for item in all_items:
            text = item.get("abstract") or item.get("summary") or item.get("description", "")
            title = item.get("title", "")
            if text and title:
                summary = self.summarize_with_llm(text, title)
                item.update(summary)
            else:
                item.update({
                    "core_idea": "No summary available.",
                    "methodology": "",
                    "quant_impact": "",
                    "relevance_score": 3,
                })
            item["ranking_score"] = self.calculate_ranking_score(item)

        # Sort by ranking score
        all_items.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)

        # Save to JSON
        os.makedirs(CONFIG["output_dir"], exist_ok=True)
        output_path = os.path.join(CONFIG["output_dir"], "quant_feed.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": datetime.now().isoformat(),
                "items": all_items[:50],  # top 50
            }, f, indent=2, default=str)

        logger.info(f"Saved {len(all_items)} items to {output_path}")
        return all_items


if __name__ == "__main__":
    scraper = QuantScraper()
    scraper.run()