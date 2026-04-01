#!/usr/bin/env python3
"""
QuantHub-Terminal: Quantitative Finance Research Aggregator & Summarizer
Scrapes arXiv, RSS feeds, and GitHub trending repos, then uses LLM to summarize and rank.
"""

import os
import json
import time
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import feedparser
import requests
from github import Github
import arxiv
import yaml
from bs4 import BeautifulSoup
import re

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
        # Quant‑specific (reliable, good content)
        "https://www.risk.net/feed/rss",
        "https://papers.ssrn.com/sol3/DisplayAbstractSearch.cfm?feed=rss",
        "https://www.bloomberg.com/quant/feed",
        
        # Financial news (public RSS, no paywalls)
        "https://www.reutersagency.com/feed/?best-topics=financial-regulatory&post_type=best",  # Reuters Financial
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # CNBC Markets
        "https://feeds.marketwatch.com/marketwatch/topstories/",  # MarketWatch
        "https://www.investing.com/rss/news.rss",  # Investing.com
        "https://www.fxstreet.com/rss",  # FXStreet
        "https://www.coindesk.com/arc/outboundfeeds/rss/",  # CoinDesk (crypto)
        
        # Alternative financial feeds
        "https://www.zerohedge.com/full-feed",  # ZeroHedge
        "https://seekingalpha.com/feed.xml",  # Seeking Alpha
        
        # Major publishers (for archive scraping)
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
        "https://www.ft.com/rss/markets",  # FT Markets
        "https://www.economist.com/finance-and-economics/rss.xml",  # Economist Finance
        "https://www.bloomberg.com/markets/rss.xml",  # Bloomberg Markets
    ],
    "github_topics": ["quantitative-finance", "algorithmic-trading", "risk-modeling"],
    "output_dir": "_data",
    "max_papers_per_source": 15,
    "max_news_per_feed": 5,  # Reduced for polite scraping
    "days_lookback": 7,
    "request_delay": 10,  # seconds between scrapes
    "archive_services": [
        "https://12ft.io/proxy?q={url}",
        "https://r.jina.ai/{url}",
        "http://webcache.googleusercontent.com/search?q=cache:{url}",
    ],
}

# Quantitative keywords for filtering
QUANT_KEYWORDS = [
    "quantitative", "algorithmic", "derivatives", "volatility", "var", "value at risk",
    "risk model", "portfolio optimization", "high-frequency", "hft", "market making",
    "statistical arbitrage", "machine learning", "deep learning", "neural network",
    "options pricing", "black-scholes", "monte carlo", "expected shortfall", "es",
    "liquidity", "market microstructure", "systematic", "factor investing", "smart beta",
    "quant fund", "hedge fund", "prop trading", "backtest", "alpha", "beta", "sharpe",
    "stochastic", "time series", "garch", "regression", "copula", "brownian motion",
    "ito", "calculus", "probability", "statistics", "econometrics", "bayesian",
    "reinforcement learning", "natural language processing", "nlp", "sentiment analysis"
]

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
    """Main scraper class for quantitative finance sources with archive access."""

    def __init__(self):
        self.results = []
        self.seen_ids = set()
        self.github = None
        if os.getenv("GITHUB_TOKEN"):
            self.github = Github(os.getenv("GITHUB_TOKEN"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_request_time = 0

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

    def polite_request(self, url: str) -> Optional[str]:
        """Make a polite HTTP request with rate limiting."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < CONFIG["request_delay"]:
            time.sleep(CONFIG["request_delay"] - elapsed)
        
        try:
            response = self.session.get(url, timeout=15)
            self.last_request_time = time.time()
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.warning(f"Request failed for {url}: {e}")
        return None

    def extract_full_text(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract full article text using archive services.
        Returns (text, archive_url) where archive_url is the successful archive URL.
        """
        # Try archive services
        for archive_template in CONFIG["archive_services"]:
            archive_url = archive_template.format(url=url)
            try:
                html = self.polite_request(archive_url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    # Remove scripts, styles, navigation
                    for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
                        element.decompose()
                    
                    # Try to find main content
                    main_selectors = ["article", "main", ".article-content", ".post-content", ".story-body", ".content"]
                    text = ""
                    
                    for selector in main_selectors:
                        elements = soup.select(selector)
                        if elements:
                            text = " ".join([elem.get_text(separator=' ', strip=True) for elem in elements])
                            break
                    
                    # Fallback to all text
                    if not text or len(text) < 200:
                        text = soup.get_text(separator=' ', strip=True)
                    
                    # Clean up
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    if len(text) > 300:
                        logger.info(f"Archive access succeeded via {archive_template.split('/')[2]}")
                        return text, archive_url
            except Exception as e:
                logger.debug(f"Archive {archive_template} failed: {e}")
                continue
        
        return None, None

    def is_quantitative_content(self, title: str, text: str) -> bool:
        """Determine if content is quantitative using keyword matching + LLM."""
        # Keyword matching (fast)
        content_lower = (title + " " + text[:2000]).lower()
        keyword_matches = sum(1 for kw in QUANT_KEYWORDS if kw.lower() in content_lower)
        
        if keyword_matches >= 3:
            return True
        
        # LLM classification for borderline cases
        if keyword_matches >= 1:
            prompt = f"""Is this financial article quantitative/technical? Answer only YES or NO.

Title: {title}
First 500 chars: {text[:500]}

Quantitative means: mathematical models, algorithms, statistical analysis, derivatives pricing, risk management, portfolio optimization, machine learning in finance, high-frequency trading, market microstructure."""
            
            try:
                if LLM_CONFIG["openai_api_key"]:
                    import openai
                    openai.api_key = LLM_CONFIG["openai_api_key"]
                    response = openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=10,
                        temperature=0.1,
                    )
                    answer = response.choices[0].message.content.strip().upper()
                    return "YES" in answer
            except Exception as e:
                logger.debug(f"LLM classification failed: {e}")
        
        return False

    def fetch_rss(self) -> List[Dict[str, Any]]:
        """Parse RSS feeds and extract full text for quantitative articles."""
        articles = []
        for feed_url in CONFIG["rss_feeds"]:
            try:
                parsed = feedparser.parse(feed_url)
                limit = CONFIG["max_papers_per_source"] if "quant" in feed_url or "ssrn" in feed_url or "risk" in feed_url else CONFIG["max_news_per_feed"]
                
                for entry in parsed.entries[:limit]:
                    article_id = entry.get("id", entry.get("link", ""))
                    if article_id in self.seen_ids:
                        continue
                    
                    url = entry.get("link", "")
                    if not url:
                        continue
                    
                    # Skip non‑HTTP URLs
                    if not url.startswith('http'):
                        continue
                    
                    self.seen_ids.add(article_id)
                    
                    # Categorize source
                    source_type = "quant"
                    if any(x in feed_url for x in ["wsj", "ft.com", "economist", "bloomberg.com/markets", "reuters", "cnbc", "marketwatch", "investing.com", "fxstreet", "zerohedge", "seekingalpha"]):
                        source_type = "news"
                    
                    title = entry.get("title", "No title")
                    summary = entry.get("summary", entry.get("description", ""))
                    
                    # For major publishers, try to get full text
                    full_text = None
                    archive_url = None
                    is_quant = False
                    
                    if source_type == "news" and any(x in feed_url for x in ["wsj", "ft.com", "economist", "bloomberg.com"]):
                        # Extract full text for major publishers
                        full_text, archive_url = self.extract_full_text(url)
                        
                        # Check if quantitative
                        if full_text:
                            is_quant = self.is_quantitative_content(title, full_text)
                            if not is_quant:
                                logger.debug(f"Skipping non‑quantitative: {title[:50]}...")
                                continue  # Skip non‑quant articles from major publishers
                    
                    # For quant sources, always include
                    elif source_type == "quant":
                        is_quant = True
                        full_text = summary  # Use RSS summary
                    
                    articles.append({
                        "id": article_id[:100],
                        "source": feed_url,
                        "source_type": source_type,
                        "title": title,
                        "summary": summary,
                        "full_text": full_text[:5000] if full_text else None,  # Limit size
                        "published": entry.get("published", entry.get("updated", "")),
                        "url": url,
                        "archive_url": archive_url,
                        "author": entry.get("author", ""),
                        "is_quantitative": is_quant,
                    })
                    
                    # Be polite between requests
                    if source_type == "news" and full_text:
                        time.sleep(CONFIG["request_delay"])
                        
            except Exception as e:
                logger.error(f"RSS error for {feed_url}: {e}")
        
        logger.info(f"Fetched {len(articles)} RSS articles ({sum(1 for a in articles if a['is_quantitative'])} quantitative).")
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

    def summarize_with_llm(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to generate a 3‑bullet summary and relevance score.
        Uses full text if available, otherwise summary.
        """
        title = item.get("title", "")
        text = item.get("full_text") or item.get("summary") or item.get("description", "")
        
        prompt = f"""
        You are a quantitative finance expert. Summarize the following:

        Title: {title}

        Content: {text[:2500]}

        Provide:
        1. **The Core Idea** (one sentence)
        2. **The Methodology** (one sentence) 
        3. **Key Quant Impact** (one sentence)
        4. **Relevance Score** (1‑10, where 1=theoretical/academic, 10=immediate trading/risk applicability)

        Return JSON with keys: core_idea, methodology, quant_impact, relevance_score.
        """
        
        # Try OpenAI
        if LLM_BACKEND == "openai" and LLM_CONFIG["openai_api_key"]:
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
        is_quant = item.get("is_quantitative", False)
        
        # Recency: newer is better (within last 7 days)
        published_str = item.get("published", "")
        try:
            pub_date = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            days_ago = (datetime.now(pub_date.tzinfo) - pub_date).days
            recency = max(0, 1 - days_ago / 7)  # 1 if today, 0 if ≥7 days
        except:
            recency = 0.5

        # Quantitative content boost (MOST IMPORTANT)
        quant_boost = 1.5 if is_quant else 0.8
        
        # Source type weight
        source_type = item.get("source_type", "quant")
        type_weights = {"quant": 1.2, "news": 0.7, "arxiv": 1.3, "github": 1.1}
        type_weight = type_weights.get(source_type, 0.8)
        
        # Specific source boosts
        source = item.get("source", "")
        source_boost = 1.0
        if "arxiv" in source:
            source_boost = 1.3  # Academic papers (highest)
        elif "risk.net" in source:
            source_boost = 1.2  # Risk professional
        elif "ssrn" in source:
            source_boost = 1.2  # Working papers
        elif "github" in source:
            source_boost = 1.0 + min(0.3, item.get("stars", 0) / 3000)  # GitHub stars
        elif any(x in source for x in ["wsj", "ft.com", "economist", "bloomberg.com"]):
            source_boost = 1.1 if is_quant else 0.6  # Major publishers only if quant

        # GitHub stars boost (if applicable)
        star_boost = 0
        if source_type == "github":
            stars = item.get("stars", 0)
            star_boost = min(0.8, stars / 1000)  # Stronger boost

        # Archive access bonus (users can read full article)
        archive_bonus = 0.3 if item.get("archive_url") else 0

        # Final score: 40% relevance, 25% recency, 20% quant boost, 10% source, 5% extras
        score = (0.4 * relevance * 10 * quant_boost + 
                 0.25 * recency * 10 + 
                 0.2 * type_weight * 10 * source_boost + 
                 0.1 * (star_boost + archive_bonus) * 10)
        return min(100, score)

    def run(self):
        """Execute full scraping → summarization → ranking pipeline."""
        logger.info("Starting QuantHub scraper...")

        # Fetch data
        arxiv_papers = self.fetch_arxiv()
        rss_articles = self.fetch_rss()
        github_repos = self.fetch_github_trending()

        all_items = arxiv_papers + rss_articles + github_repos

        # Summarize and rank (only quantitative items get full LLM treatment)
        for item in all_items:
            if item.get("is_quantitative", False):
                summary = self.summarize_with_llm(item)
                item.update(summary)
            else:
                # Non‑quant items get simple extraction
                text = item.get("summary") or item.get("description", "")
                sentences = text.split(". ")
                item.update({
                    "core_idea": sentences[0] if sentences else "Summary not available.",
                    "methodology": sentences[1] if len(sentences) > 1 else "",
                    "quant_impact": sentences[2] if len(sentences) > 2 else "",
                    "relevance_score": 3,  # Lower for non‑quant
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