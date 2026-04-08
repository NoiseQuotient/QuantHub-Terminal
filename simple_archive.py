#!/usr/bin/env python3
"""
Simple Quant Frontier Archive System - No external dependencies
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
import time
from urllib.parse import urlparse
import http.client
import ssl

class SimpleArchive:
    def __init__(self, db_path: str = "simple_archive.db"):
        self.db_path = db_path
        self.init_database()
        
        # Quant keywords for filtering
        self.quant_keywords = [
            'quantitative', 'algorithmic', 'machine learning', 'AI', 'options', 'derivatives',
            'volatility', 'risk', 'trading', 'hedge fund', 'portfolio', 'crypto', 'blockchain'
        ]
        
        # Simple test URLs (headlines only - no full article scraping)
        self.test_articles = [
            {
                'url': 'https://www.bloomberg.com/news/articles/2026-04-07/quant-funds-ai-models',
                'title': 'Quant Funds Adopt AI Models for Market Prediction',
                'source': 'Bloomberg',
                'description': 'Hedge funds are implementing machine learning models for better market predictions.'
            },
            {
                'url': 'https://www.wsj.com/articles/options-trading-algorithms-2026-04-07',
                'title': 'New Algorithms Transform Options Trading',
                'source': 'Wall Street Journal',
                'description': 'Advanced algorithms are changing how options are priced and traded.'
            },
            {
                'url': 'https://www.ft.com/content/quant-risk-models-2026',
                'title': 'Quantitative Risk Models Face Regulatory Scrutiny',
                'source': 'Financial Times',
                'description': 'Regulators examine AI-based risk models in major banks.'
            },
            {
                'url': 'https://www.reuters.com/finance/quant-2026-04-07',
                'title': 'Quantitative Finance Jobs Surge Amid AI Boom',
                'source': 'Reuters',
                'description': 'Demand for quant finance professionals with AI skills reaches record high.'
            },
            {
                'url': 'https://www.risk.net/quant/2026/04/07',
                'title': 'Machine Learning Revolutionizes Risk Management',
                'source': 'Risk.net',
                'description': 'ML models show 40% improvement in risk prediction accuracy.'
            }
        ]
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                description TEXT,
                publication_date TIMESTAMP,
                archive_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL DEFAULT 0.0,
                is_quant_relevant BOOLEAN DEFAULT 0,
                archive_successful BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")
    
    def get_url_hash(self, url: str) -> str:
        """Generate hash for URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def calculate_relevance(self, title: str, description: str = "") -> float:
        """Calculate relevance score for quant finance"""
        text = (title + " " + description).lower()
        matches = sum(1 for keyword in self.quant_keywords if keyword in text)
        return min(1.0, matches / 3.0)  # Simple scoring
    
    def add_test_articles(self):
        """Add test articles to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        added_count = 0
        for article in self.test_articles:
            url_hash = self.get_url_hash(article['url'])
            
            # Check if already exists
            cursor.execute("SELECT id FROM articles WHERE url_hash = ?", (url_hash,))
            if cursor.fetchone():
                continue
            
            relevance = self.calculate_relevance(article['title'], article['description'])
            is_quant = relevance > 0.3
            
            cursor.execute('''
                INSERT INTO articles (
                    url_hash, original_url, title, source, description,
                    publication_date, relevance_score, is_quant_relevant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                url_hash, article['url'], article['title'], article['source'],
                article['description'], datetime.now().isoformat(), relevance, is_quant
            ))
            
            added_count += 1
            print(f"Added: {article['title'][:40]}... (relevance: {relevance:.2f})")
        
        conn.commit()
        conn.close()
        return added_count
    
    def get_articles(self, limit: int = 10, min_relevance: float = 0.0):
        """Get archived articles"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT url_hash, original_url, title, source, description,
                   relevance_score, archive_date
            FROM articles 
            WHERE archive_successful = 1 AND relevance_score >= ?
            ORDER BY relevance_score DESC
            LIMIT ?
        ''', (min_relevance, limit))
        
        articles = []
        for row in cursor.fetchall():
            article = dict(row)
            article['archive_url'] = f"/archive/{article['url_hash']}"
            articles.append(article)
        
        conn.close()
        return articles
    
    def generate_html(self, output_path: str = "archive_index.html"):
        """Generate HTML page for archived articles"""
        articles = self.get_articles(limit=20, min_relevance=0.3)
        
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quant Frontier Archive</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; 
            color: #f8fafc; 
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%);
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        .header h1 { 
            font-size: 2.5rem; 
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #fff 0%, #93c5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .stats { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem; 
            margin: 2rem 0; 
        }
        .stat-card { 
            background: #1e293b; 
            padding: 1.5rem; 
            border-radius: 8px;
            border: 1px solid #475569;
        }
        .stat-value { 
            font-size: 2rem; 
            font-weight: 700; 
            color: #3b82f6; 
        }
        .stat-label { 
            color: #94a3b8; 
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }
        .articles-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem; 
            margin-top: 2rem;
        }
        .article-card { 
            background: #1e293b; 
            padding: 1.5rem; 
            border-radius: 12px;
            border: 1px solid #475569;
            transition: all 0.2s ease;
        }
        .article-card:hover { 
            border-color: #3b82f6;
            transform: translateY(-2px);
        }
        .article-source { 
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .article-title { 
            font-size: 1.125rem; 
            font-weight: 600; 
            margin-bottom: 0.75rem;
            color: #f8fafc;
        }
        .article-description { 
            color: #94a3b8; 
            font-size: 0.9375rem;
            margin-bottom: 1rem;
            line-height: 1.6;
        }
        .article-meta { 
            display: flex; 
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #475569;
        }
        .article-relevance { 
            font-family: monospace;
            color: #10b981;
            font-weight: 600;
        }
        .original-link { 
            color: #3b82f6; 
            text-decoration: none;
            font-size: 0.875rem;
        }
        .original-link:hover { 
            text-decoration: underline;
        }
        .footer { 
            margin-top: 3rem; 
            padding-top: 2rem;
            border-top: 1px solid #475569;
            color: #94a3b8;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Quant Frontier Archive</h1>
            <p>Our own archive.ph for quantitative finance articles</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">''' + str(len(articles)) + '''</div>
                <div class="stat-label">Articles Archived</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">''' + str(len([a for a in articles if a['relevance_score'] > 0.7])) + '''</div>
                <div class="stat-label">High Relevance</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">''' + str(len(set(a['source'] for a in articles))) + '''</div>
                <div class="stat-label">Sources</div>
            </div>
        </div>
        
        <h2 style="margin: 2rem 0 1rem; font-size: 1.5rem;">Archived Articles</h2>
        
        <div class="articles-grid">
'''
        
        for article in articles:
            relevance_percent = int(article['relevance_score'] * 100)
            html += f'''
            <div class="article-card">
                <span class="article-source">{article['source']}</span>
                <h3 class="article-title">{article['title']}</h3>
                <p class="article-description">{article['description']}</p>
                <div class="article-meta">
                    <span class="article-relevance">{relevance_percent}% relevant</span>
                    <a href="{article['original_url']}" class="original-link" target="_blank">Original Article</a>
                </div>
            </div>
'''
        
        html += '''
        </div>
        
        <div class="footer">
            <p>Quant Frontier Archive System • All articles filtered for quant finance relevance</p>
            <p style="margin-top: 0.5rem; font-size: 0.875rem;">
                Generated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M') + '''
            </p>
        </div>
    </div>
</body>
</html>'''
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"Generated archive page: {output_path}")
        return len(articles)

def main():
    """Main function"""
    print("🚀 Quant Frontier Archive System")
    print("=" * 40)
    
    archive = SimpleArchive()
    
    # Add test articles
    print("\n📥 Adding test articles...")
    added = archive.add_test_articles()
    print(f"   Added {added} new articles")
    
    # Generate HTML
    print("\n📄 Generating archive page...")
    article_count = archive.generate_html("quant_archive.html")
    
    # Show statistics
    articles = archive.get_articles()
    print(f"\n📊 Archive Statistics:")
    print(f"   Total articles: {len(articles)}")
    
    if articles:
        print(f"\n📰 Top Articles:")
        for i, article in enumerate(articles[:3], 1):
            print(f"   {i}. {article['title'][:50]}...")
            print(f"      Source: {article['source']}")
            print(f"      Relevance: {article['relevance_score']:.2f}")
    
    print(f"\n✅ Archive system ready!")
    print(f"   HTML file: quant_archive.html")
    print(f"   Database: simple_archive.db")

if __name__ == "__main__":
    main()