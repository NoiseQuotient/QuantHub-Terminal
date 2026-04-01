#!/usr/bin/env python3
"""
Simple Quant Frontier scraper - just RSS headlines, no archive scraping
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import feedparser
import requests
from github import Github
import arxiv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "arxiv_categories": ["cs.CE", "q-fin.CP", "q-fin.ST", "q-fin.PR", "q-fin.TR"],
    "rss_feeds": [
        # Quant research
        "https://www.risk.net/feed/rss",
        "https://papers.ssrn.com/sol3/DisplayAbstractSearch.cfm?feed=rss",
        "https://www.bloomberg.com/quant/feed",
        
        # Financial news (headlines only)
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ
        "https://www.ft.com/rss/markets",  # FT
        "https://www.economist.com/finance-and-economics/rss.xml",  # Economist
        "https://www.bloomberg.com/markets/rss.xml",  # Bloomberg
        "https://www.reutersagency.com/feed/?best-topics=financial-regulatory&post_type=best",  # Reuters
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # CNBC
        "https://feeds.marketwatch.com/marketwatch/topstories/",  # MarketWatch
        "https://www.investing.com/rss/news.rss",  # Investing.com
        "https://www.fxstreet.com/rss",  # FXStreet
        "https://www.coindesk.com/arc/outboundfeeds/rss/",  # CoinDesk
        "https://www.zerohedge.com/full-feed",  # ZeroHedge
        "https://seekingalpha.com/feed.xml",  # Seeking Alpha
    ],
    "github_topics": ["quantitative-finance", "algorithmic-trading", "risk-modeling"],
    "output_dir": "_data",
    "max_items_per_source": 8,
    "days_lookback": 3,
}

class SimpleQuantScraper:
    def __init__(self):
        self.results = []
        self.seen_ids = set()
        self.github = None
        if os.getenv("GITHUB_TOKEN"):
            self.github = Github(os.getenv("GITHUB_TOKEN"))

    def fetch_arxiv(self) -> List[Dict[str, Any]]:
        """Fetch arXiv papers."""
        papers = []
        client = arxiv.Client()
        cutoff_date = datetime.now() - timedelta(days=CONFIG["days_lookback"])

        for category in CONFIG["arxiv_categories"]:
            query = f"cat:{category}"
            search = arxiv.Search(
                query=query,
                max_results=CONFIG["max_items_per_source"],
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
                        "source_type": "quant",
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "summary": result.summary,
                        "published": result.published.isoformat(),
                        "url": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "categories": result.categories,
                    })
            except Exception as e:
                logger.error(f"arXiv error: {e}")
        logger.info(f"Fetched {len(papers)} arXiv papers")
        return papers

    def fetch_rss(self) -> List[Dict[str, Any]]:
        """Fetch RSS feeds - simple headlines only."""
        articles = []
        for feed_url in CONFIG["rss_feeds"]:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:CONFIG["max_items_per_source"]]:
                    article_id = entry.get("id", entry.get("link", ""))
                    if article_id in self.seen_ids:
                        continue
                    
                    url = entry.get("link", "")
                    if not url or not url.startswith('http'):
                        continue
                    
                    self.seen_ids.add(article_id)
                    
                    # Determine source type
                    source_type = "quant"
                    if any(x in feed_url for x in ["wsj", "ft.com", "economist", "bloomberg.com", "reuters", "cnbc", "marketwatch", "investing.com", "fxstreet", "coindesk", "zerohedge", "seekingalpha"]):
                        source_type = "news"
                    
                    articles.append({
                        "id": article_id[:100],
                        "source": feed_url,
                        "source_type": source_type,
                        "title": entry.get("title", "No title"),
                        "summary": entry.get("summary", entry.get("description", "")),
                        "published": entry.get("published", entry.get("updated", "")),
                        "url": url,
                        "author": entry.get("author", ""),
                    })
            except Exception as e:
                logger.error(f"RSS error for {feed_url}: {e}")
        
        logger.info(f"Fetched {len(articles)} RSS articles")
        return articles

    def fetch_github(self) -> List[Dict[str, Any]]:
        """Fetch GitHub trending repos."""
        repos = []
        if not self.github:
            logger.warning("No GitHub token")
            return repos
        
        for topic in CONFIG["github_topics"]:
            try:
                query = f"topic:{topic}"
                result = self.github.search_repositories(query, sort="stars", order="desc")
                for repo in result[:CONFIG["max_items_per_source"]]:
                    repo_id = str(repo.id)
                    if repo_id in self.seen_ids:
                        continue
                    self.seen_ids.add(repo_id)
                    repos.append({
                        "id": repo_id,
                        "source": "github",
                        "source_type": "quant",
                        "title": repo.name,
                        "summary": repo.description or "",
                        "published": repo.updated_at.isoformat(),
                        "url": repo.html_url,
                        "stars": repo.stargazers_count,
                        "forks": repo.forks_count,
                        "language": repo.language,
                        "topics": repo.topics,
                    })
            except Exception as e:
                logger.error(f"GitHub error: {e}")
        
        logger.info(f"Fetched {len(repos)} GitHub repos")
        return repos

    def generate_simple_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Generate simple summary without LLM."""
        text = item.get("summary") or item.get("title", "")
        sentences = text.split(". ")
        
        return {
            "core_idea": sentences[0] if sentences else text[:100],
            "methodology": sentences[1] if len(sentences) > 1 else "",
            "quant_impact": sentences[2] if len(sentences) > 2 else "",
            "relevance_score": 7 if item.get("source_type") == "quant" else 5,
        }

    def calculate_score(self, item: Dict[str, Any]) -> float:
        """Simple ranking score."""
        relevance = 7 if item.get("source_type") == "quant" else 5
        
        # Recency
        published = item.get("published", "")
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            days_ago = (datetime.now() - pub_date).days
            recency = max(0, 1 - days_ago / 7)
        except:
            recency = 0.5
        
        # Source weight
        source = item.get("source", "")
        source_weight = 1.0
        if "arxiv" in source:
            source_weight = 1.3
        elif "risk.net" in source or "ssrn" in source:
            source_weight = 1.2
        elif "github" in source:
            source_weight = 1.1 + min(0.2, item.get("stars", 0) / 1000)
        
        return min(100, (relevance * 6 + recency * 3 + source_weight * 1) * 10)

    def run(self):
        """Run the simple scraper."""
        logger.info("Starting simple Quant Frontier scraper...")
        
        # Fetch all data
        arxiv_papers = self.fetch_arxiv()
        rss_articles = self.fetch_rss()
        github_repos = self.fetch_github()
        
        all_items = arxiv_papers + rss_articles + github_repos
        
        # Add summaries and scores
        for item in all_items:
            summary = self.generate_simple_summary(item)
            item.update(summary)
            item["ranking_score"] = self.calculate_score(item)
        
        # Sort by score
        all_items.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
        
        # Save to JSON
        os.makedirs(CONFIG["output_dir"], exist_ok=True)
        output_path = os.path.join(CONFIG["output_dir"], "quant_feed.json")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": datetime.now().isoformat(),
                "items": all_items[:50],  # Top 50
            }, f, indent=2, default=str)
        
        logger.info(f"Saved {len(all_items)} items to {output_path}")
        
        # Log sources
        sources = {}
        for item in all_items:
            src = item.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        
        logger.info(f"Sources: {sources}")
        return all_items

if __name__ == "__main__":
    scraper = SimpleQuantScraper()
    scraper.run()