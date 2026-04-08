#!/usr/bin/env python3
"""
Quant Frontier News Pipeline System
Continuously monitors major financial news sources for relevant quant finance articles
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import feedparser
import re
from typing import List, Dict, Optional
import hashlib

class NewsPipeline:
    """Pipeline system for monitoring financial news sources"""
    
    def __init__(self, db_path: str = "news_pipeline.db"):
        self.db_path = db_path
        self.setup_database()
        
        # Major financial news sources with their RSS feeds
        self.news_sources = {
            "Bloomberg": {
                "rss": "https://www.bloomberg.com/markets/rss.xml",
                "quant_keywords": ["quantitative", "algorithmic", "hedge fund", "AI", "machine learning", 
                                  "trading", "risk", "derivatives", "options", "portfolio"]
            },
            "Wall Street Journal": {
                "rss": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
                "quant_keywords": ["quant", "algorithm", "trading", "finance", "investment", "market"]
            },
            "Financial Times": {
                "rss": "https://www.ft.com/rss/markets",
                "quant_keywords": ["quantitative", "trading", "finance", "investment", "markets"]
            },
            "Reuters": {
                "rss": "https://www.reuters.com/markets/rss",
                "quant_keywords": ["finance", "trading", "markets", "investment", "economy"]
            },
            "Risk.net": {
                "rss": "https://www.risk.net/feed",
                "quant_keywords": ["risk", "derivatives", "regulation", "trading", "finance"]
            }
        }
        
        # Quant-specific keywords for deep relevance filtering
        self.quant_core_keywords = [
            # AI & Machine Learning
            "machine learning", "artificial intelligence", "neural network", "deep learning",
            "reinforcement learning", "transformer", "GPT", "LLM", "AI model",
            
            # Trading & Algorithms
            "algorithmic trading", "high-frequency trading", "HFT", "quant trading",
            "market making", "execution algorithm", "smart order routing",
            
            # Risk Management
            "value at risk", "VaR", "risk management", "stress testing", "counterparty risk",
            "market risk", "credit risk", "liquidity risk",
            
            # Derivatives & Options
            "options pricing", "derivatives", "Black-Scholes", "volatility", "Greeks",
            "exotic options", "swaps", "futures", "forwards",
            
            # Portfolio Management
            "portfolio optimization", "mean-variance", "modern portfolio theory",
            "factor investing", "smart beta", "risk parity",
            
            # Quantitative Methods
            "stochastic calculus", "Monte Carlo", "numerical methods", "time series",
            "regression analysis", "statistical arbitrage", "cointegration",
            
            # Crypto & DeFi
            "cryptocurrency", "blockchain", "DeFi", "smart contract", "AMM",
            "liquidity pool", "staking", "yield farming",
            
            # Regulation
            "Basel", "Dodd-Frank", "MiFID", "regulation", "compliance", "reporting"
        ]
    
    def setup_database(self):
        """Initialize SQLite database for pipeline tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Articles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                summary TEXT,
                content_hash TEXT NOT NULL,
                relevance_score REAL DEFAULT 0,
                quant_category TEXT,
                publish_date TIMESTAMP,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0,
                ai_rewritten BOOLEAN DEFAULT 0
            )
        ''')
        
        # Pipeline logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                articles_found INTEGER,
                articles_relevant INTEGER,
                run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def fetch_rss_feed(self, source: str, rss_url: str) -> List[Dict]:
        """Fetch and parse RSS feed from a news source"""
        try:
            print(f"📡 Fetching RSS feed: {source}")
            feed = feedparser.parse(rss_url)
            
            articles = []
            for entry in feed.entries[:20]:  # Limit to 20 most recent
                article = {
                    "source": source,
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "publish_date": entry.get("published", ""),
                    "content_hash": self.generate_content_hash(
                        entry.get("title", "") + entry.get("summary", "")
                    )
                }
                articles.append(article)
            
            print(f"   Found {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            print(f"   Error fetching {source}: {e}")
            return []
    
    def generate_content_hash(self, content: str) -> str:
        """Generate hash for content to detect duplicates"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def calculate_relevance_score(self, article: Dict) -> float:
        """Calculate how relevant an article is to quantitative finance"""
        text = f"{article['title']} {article['summary']}".lower()
        
        score = 0
        matches = []
        
        # Check for quant core keywords
        for keyword in self.quant_core_keywords:
            if keyword.lower() in text:
                score += 2.0  # Higher weight for core quant terms
                matches.append(keyword)
        
        # Check for source-specific keywords
        source_keywords = self.news_sources.get(article["source"], {}).get("quant_keywords", [])
        for keyword in source_keywords:
            if keyword.lower() in text:
                score += 1.0
                matches.append(keyword)
        
        # Bonus for multiple matches
        if len(matches) > 3:
            score += len(matches) * 0.5
        
        # Category detection
        categories = {
            "AI/ML": ["machine learning", "artificial intelligence", "neural", "deep learning"],
            "Trading": ["algorithmic trading", "HFT", "market making", "execution"],
            "Risk": ["risk management", "VaR", "stress testing", "counterparty"],
            "Derivatives": ["options", "derivatives", "volatility", "Greeks"],
            "Portfolio": ["portfolio", "optimization", "factor", "allocation"],
            "Crypto": ["crypto", "blockchain", "DeFi", "smart contract"],
            "Regulation": ["regulation", "compliance", "Basel", "Dodd-Frank"]
        }
        
        detected_categories = []
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    detected_categories.append(category)
                    break
        
        article["quant_category"] = ", ".join(detected_categories[:2]) if detected_categories else "General"
        
        return min(score, 10.0)  # Cap at 10
    
    def store_articles(self, articles: List[Dict]):
        """Store articles in database if not already present"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_count = 0
        relevant_count = 0
        
        for article in articles:
            # Check if article already exists
            cursor.execute(
                "SELECT id FROM articles WHERE content_hash = ?",
                (article["content_hash"],)
            )
            
            if not cursor.fetchone():
                # Calculate relevance
                relevance = self.calculate_relevance_score(article)
                article["relevance_score"] = relevance
                
                # Only store if relevant enough
                if relevance >= 1.0:
                    cursor.execute('''
                        INSERT INTO articles 
                        (source, title, url, summary, content_hash, relevance_score, 
                         quant_category, publish_date, processed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        article["source"],
                        article["title"],
                        article["url"],
                        article["summary"],
                        article["content_hash"],
                        relevance,
                        article["quant_category"],
                        article["publish_date"],
                        0  # Not yet processed for AI rewriting
                    ))
                    new_count += 1
                    relevant_count += 1 if relevance >= 2.0 else 0
        
        conn.commit()
        conn.close()
        
        return new_count, relevant_count
    
    def run_pipeline(self):
        """Run the complete pipeline for all news sources"""
        print("🚀 Starting Quant Frontier News Pipeline")
        print("=" * 50)
        
        total_new = 0
        total_relevant = 0
        
        for source, config in self.news_sources.items():
            print(f"\n📰 Processing: {source}")
            
            # Fetch RSS feed
            articles = self.fetch_rss_feed(source, config["rss"])
            
            if articles:
                # Store articles
                new_count, relevant_count = self.store_articles(articles)
                total_new += new_count
                total_relevant += relevant_count
                
                print(f"   ✅ New articles: {new_count}")
                print(f"   🔥 Highly relevant: {relevant_count}")
                
                # Log pipeline run
                self.log_pipeline_run(source, len(articles), relevant_count, "success")
            else:
                print(f"   ⚠️ No articles found")
                self.log_pipeline_run(source, 0, 0, "no_articles")
        
        print(f"\n📊 Pipeline Summary:")
        print(f"   Total new articles: {total_new}")
        print(f"   Highly relevant: {total_relevant}")
        print(f"   Database updated: news_pipeline.db")
        
        return total_new, total_relevant
    
    def log_pipeline_run(self, source: str, articles_found: int, articles_relevant: int, status: str):
        """Log pipeline execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO pipeline_logs (source, articles_found, articles_relevant, status)
            VALUES (?, ?, ?, ?)
        ''', (source, articles_found, articles_relevant, status))
        
        conn.commit()
        conn.close()
    
    def get_relevant_articles(self, min_relevance: float = 2.0, limit: int = 20) -> List[Dict]:
        """Get most relevant articles from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM articles 
            WHERE relevance_score >= ? 
            AND processed = 0
            ORDER BY relevance_score DESC, publish_date DESC
            LIMIT ?
        ''', (min_relevance, limit))
        
        articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return articles
    
    def mark_as_processed(self, article_id: int):
        """Mark article as processed (AI rewritten)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE articles 
            SET processed = 1, ai_rewritten = 1
            WHERE id = ?
        ''', (article_id,))
        
        conn.commit()
        conn.close()
    
    def get_pipeline_stats(self) -> Dict:
        """Get pipeline statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total articles
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]
        
        # Relevant articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE relevance_score >= 2.0")
        relevant_articles = cursor.fetchone()[0]
        
        # Processed articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE ai_rewritten = 1")
        processed_articles = cursor.fetchone()[0]
        
        # Recent pipeline runs
        cursor.execute('''
            SELECT source, articles_found, articles_relevant, run_time
            FROM pipeline_logs
            ORDER BY run_time DESC
            LIMIT 10
        ''')
        recent_runs = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_articles": total_articles,
            "relevant_articles": relevant_articles,
            "processed_articles": processed_articles,
            "recent_runs": recent_runs
        }

def main():
    """Main pipeline execution"""
    pipeline = NewsPipeline()
    
    print("🔧 Quant Frontier News Pipeline System")
    print("=" * 50)
    
    # Run pipeline
    new_articles, relevant_articles = pipeline.run_pipeline()
    
    # Get relevant articles for AI rewriting
    if relevant_articles > 0:
        print(f"\n🎯 Found {relevant_articles} highly relevant articles")
        
        relevant = pipeline.get_relevant_articles(min_relevance=2.0, limit=10)
        
        print("\n📋 Top relevant articles:")
        for i, article in enumerate(relevant, 1):
            print(f"{i}. [{article['source']}] {article['title']}")
            print(f"   Relevance: {article['relevance_score']:.1f} | Category: {article['quant_category']}")
            print(f"   URL: {article['url']}")
            print()
    
    # Show pipeline stats
    stats = pipeline.get_pipeline_stats()
    print("\n📊 Pipeline Statistics:")
    print(f"   Total articles in database: {stats['total_articles']}")
    print(f"   Relevant articles (score ≥ 2.0): {stats['relevant_articles']}")
    print(f"   AI-rewritten articles: {stats['processed_articles']}")
    
    print("\n✅ Pipeline completed successfully!")

if __name__ == "__main__":
    main()