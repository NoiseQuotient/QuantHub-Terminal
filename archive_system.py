#!/usr/bin/env python3
"""
Quant Frontier Archive System - Our own archive.ph for quant finance articles
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import feedparser
import hashlib
import time
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class QuantArchiveSystem:
    def __init__(self, db_path: str = "quant_archive.db"):
        """Initialize the archive system with SQLite database"""
        self.db_path = db_path
        self.init_database()
        
        # Headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        # Quant-relevant keywords for filtering
        self.quant_keywords = [
            'quantitative', 'algorithmic', 'machine learning', 'AI', 'options', 'derivatives',
            'volatility', 'risk management', 'trading', 'hedge fund', 'portfolio',
            'Black-Scholes', 'stochastic', 'Monte Carlo', 'regression', 'neural network',
            'crypto', 'blockchain', 'DeFi', 'stablecoin', 'liquidity',
            'Basel', 'regulation', 'compliance', 'stress test', 'capital',
            'high frequency', 'HFT', 'market making', 'arbitrage', 'spread'
        ]
        
        # Sources to monitor
        self.sources = [
            {
                'name': 'Bloomberg',
                'rss': 'https://www.bloomberg.com/markets/rss.xml',
                'domain': 'bloomberg.com',
                'priority': 10
            },
            {
                'name': 'Wall Street Journal',
                'rss': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
                'domain': 'wsj.com',
                'priority': 10
            },
            {
                'name': 'Financial Times',
                'rss': 'https://www.ft.com/rss/markets',
                'domain': 'ft.com',
                'priority': 10
            },
            {
                'name': 'Reuters',
                'rss': 'https://www.reutersagency.com/feed/?best-topics=financial-regulatory&post_type=best',
                'domain': 'reuters.com',
                'priority': 9
            },
            {
                'name': 'Risk.net',
                'rss': 'https://www.risk.net/feed/rss',
                'domain': 'risk.net',
                'priority': 8
            },
            {
                'name': 'Wilmott',
                'rss': 'https://www.wilmott.com/feed',
                'domain': 'wilmott.com',
                'priority': 7
            }
        ]
    
    def init_database(self):
        """Initialize SQLite database for storing archived articles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Articles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                publication_date TIMESTAMP,
                archive_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_html TEXT,
                content_text TEXT,
                summary TEXT,
                relevance_score REAL DEFAULT 0.0,
                is_quant_relevant BOOLEAN DEFAULT 0,
                archive_successful BOOLEAN DEFAULT 0,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP
            )
        ''')
        
        # Keywords table for search
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_keywords (
                article_id INTEGER,
                keyword TEXT,
                relevance REAL,
                FOREIGN KEY (article_id) REFERENCES articles (id),
                PRIMARY KEY (article_id, keyword)
            )
        ''')
        
        # Access logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def get_url_hash(self, url: str) -> str:
        """Generate hash for URL to use as unique identifier"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def is_quant_relevant(self, title: str, description: str = "") -> bool:
        """Check if article is relevant to quantitative finance"""
        text = (title + " " + description).lower()
        
        # Check for quant keywords
        keyword_matches = sum(1 for keyword in self.quant_keywords if keyword.lower() in text)
        
        # Calculate relevance score
        relevance_score = keyword_matches / len(self.quant_keywords)
        
        # Consider relevant if at least 2 keywords match or high relevance score
        return keyword_matches >= 2 or relevance_score > 0.15
    
    def calculate_relevance_score(self, title: str, description: str = "") -> float:
        """Calculate relevance score (0.0 to 1.0) for quant finance"""
        text = (title + " " + description).lower()
        
        # Count keyword matches
        matches = 0
        for keyword in self.quant_keywords:
            if keyword.lower() in text:
                matches += 1
        
        # Normalize score
        return min(1.0, matches / 5.0)  # Cap at 1.0, 5 matches = perfect score
    
    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch articles from RSS feeds"""
        articles = []
        
        for source in self.sources:
            try:
                logger.info(f"Fetching RSS feed: {source['name']}")
                feed = feedparser.parse(source['rss'])
                
                for entry in feed.entries[:10]:  # Limit to 10 per source
                    # Extract article info
                    article = {
                        'url': entry.get('link', ''),
                        'title': entry.get('title', 'No title'),
                        'description': entry.get('description', ''),
                        'source': source['name'],
                        'publication_date': entry.get('published', ''),
                        'relevance_score': self.calculate_relevance_score(
                            entry.get('title', ''), 
                            entry.get('description', '')
                        ),
                        'is_quant_relevant': self.is_quant_relevant(
                            entry.get('title', ''), 
                            entry.get('description', '')
                        )
                    }
                    
                    # Only add if relevant to quant finance
                    if article['is_quant_relevant']:
                        articles.append(article)
                        logger.info(f"Found relevant article: {article['title'][:50]}... (score: {article['relevance_score']:.2f})")
                
                time.sleep(1)  # Be polite to servers
                
            except Exception as e:
                logger.error(f"Error fetching RSS from {source['name']}: {e}")
        
        return articles
    
    def archive_article(self, url: str, title: str, source: str) -> Optional[Dict[str, Any]]:
        """Archive a single article by fetching and saving its content"""
        url_hash = self.get_url_hash(url)
        
        # Check if already archived
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM articles WHERE url_hash = ?", (url_hash,))
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"Article already archived: {title[:50]}...")
            conn.close()
            return None
        
        try:
            # Fetch article content
            logger.info(f"Archiving article: {title[:50]}...")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main content (simple heuristic)
            # Remove scripts, styles, nav, footer, etc.
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Get text content
            content_text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            lines = [line.strip() for line in content_text.split('\n') if line.strip()]
            content_text = '\n'.join(lines[:500])  # Limit to 500 lines
            
            # Generate simple summary (first 200 chars)
            summary = content_text[:200] + "..." if len(content_text) > 200 else content_text
            
            # Save to database
            cursor.execute('''
                INSERT INTO articles (
                    url_hash, original_url, title, source, publication_date,
                    content_html, content_text, summary, relevance_score,
                    is_quant_relevant, archive_successful
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                url_hash, url, title, source, datetime.now().isoformat(),
                str(soup), content_text, summary, 0.0,  # relevance_score will be updated
                True, True
            ))
            
            article_id = cursor.lastrowid
            
            # Update relevance score based on actual content
            relevance_score = self.calculate_relevance_score(title, content_text)
            cursor.execute(
                "UPDATE articles SET relevance_score = ? WHERE id = ?",
                (relevance_score, article_id)
            )
            
            # Add keywords
            text_for_keywords = (title + " " + content_text).lower()
            for keyword in self.quant_keywords:
                if keyword.lower() in text_for_keywords:
                    cursor.execute(
                        "INSERT INTO article_keywords (article_id, keyword, relevance) VALUES (?, ?, ?)",
                        (article_id, keyword, 1.0)
                    )
            
            conn.commit()
            
            archived_article = {
                'id': article_id,
                'url_hash': url_hash,
                'original_url': url,
                'title': title,
                'source': source,
                'summary': summary,
                'relevance_score': relevance_score,
                'archive_url': f"/archive/{url_hash}"  # Our internal URL
            }
            
            logger.info(f"Successfully archived article: {title[:50]}... (score: {relevance_score:.2f})")
            return archived_article
            
        except Exception as e:
            logger.error(f"Error archiving article {url}: {e}")
            return None
        finally:
            conn.close()
    
    def run_archive_pipeline(self):
        """Run the complete archive pipeline"""
        logger.info("Starting archive pipeline...")
        
        # Step 1: Fetch RSS feeds
        articles = self.fetch_rss_feeds()
        logger.info(f"Found {len(articles)} relevant articles")
        
        # Step 2: Archive each article
        archived_count = 0
        for article in articles:
            if article['is_quant_relevant']:
                archived = self.archive_article(
                    article['url'],
                    article['title'],
                    article['source']
                )
                if archived:
                    archived_count += 1
                time.sleep(2)  # Be polite to servers
        
        logger.info(f"Archive pipeline complete. Archived {archived_count} new articles.")
        return archived_count
    
    def get_archived_articles(self, limit: int = 20, min_relevance: float = 0.0) -> List[Dict[str, Any]]:
        """Retrieve archived articles from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, original_url, title, source, publication_date, 
                   summary, relevance_score, archive_date
            FROM articles 
            WHERE archive_successful = 1 AND relevance_score >= ?
            ORDER BY relevance_score DESC, publication_date DESC
            LIMIT ?
        ''', (min_relevance, limit))
        
        articles = []
        for row in cursor.fetchall():
            article = dict(row)
            # Add our archive URL
            article['archive_url'] = f"/archive/{self.get_url_hash(article['original_url'])}"
            articles.append(article)
        
        conn.close()
        return articles
    
    def get_article_by_hash(self, url_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific archived article"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, original_url, title, source, publication_date,
                   content_text, summary, relevance_score, archive_date
            FROM articles 
            WHERE url_hash = ? AND archive_successful = 1
        ''', (url_hash,))
        
        row = cursor.fetchone()
        if row:
            article = dict(row)
            article['archive_url'] = f"/archive/{url_hash}"
            conn.close()
            return article
        
        conn.close()
        return None

def main():
    """Main function to run the archive system"""
    archive = QuantArchiveSystem()
    
    # Run archive pipeline
    archived_count = archive.run_archive_pipeline()
    
    # Get recent archived articles
    recent_articles = archive.get_archived_articles(limit=10)
    
    print(f"\n📊 Archive System Report:")
    print(f"   New articles archived: {archived_count}")
    print(f"   Total articles in database: {len(recent_articles)}")
    
    if recent_articles:
        print(f"\n📰 Recent Archived Articles:")
        for i, article in enumerate(recent_articles[:5], 1):
            print(f"   {i}. {article['title'][:60]}...")
            print(f"      Source: {article['source']}")
            print(f"      Relevance: {article['relevance_score']:.2f}")
            print(f"      Archive URL: {article['archive_url']}")
            print()

if __name__ == "__main__":
    main()