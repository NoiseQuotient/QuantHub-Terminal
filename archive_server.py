#!/usr/bin/env python3
"""
Simple web server for Quant Frontier Archive System
"""

from flask import Flask, render_template, jsonify, request, redirect, send_file
import sqlite3
import json
from datetime import datetime
import hashlib
from archive_system import QuantArchiveSystem
import os

app = Flask(__name__)
archive_system = QuantArchiveSystem()

@app.route('/')
def index():
    """Home page showing recent archived articles"""
    articles = archive_system.get_archived_articles(limit=20, min_relevance=0.3)
    
    stats = {
        'total_articles': len(articles),
        'high_relevance': len([a for a in articles if a['relevance_score'] > 0.7]),
        'sources': list(set(a['source'] for a in articles))
    }
    
    return render_template('archive_index.html', 
                         articles=articles, 
                         stats=stats,
                         title="Quant Frontier Archive")

@app.route('/archive/<url_hash>')
def view_archive(url_hash):
    """View an archived article"""
    article = archive_system.get_article_by_hash(url_hash)
    
    if not article:
        return "Article not found", 404
    
    # Log access
    conn = sqlite3.connect(archive_system.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE articles 
        SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
        WHERE url_hash = ?
    ''', (url_hash,))
    conn.commit()
    conn.close()
    
    return render_template('archive_view.html', article=article)

@app.route('/api/articles')
def api_articles():
    """API endpoint for archived articles"""
    limit = request.args.get('limit', 20, type=int)
    min_relevance = request.args.get('min_relevance', 0.0, type=float)
    source = request.args.get('source', None)
    
    articles = archive_system.get_archived_articles(limit=100, min_relevance=min_relevance)
    
    if source:
        articles = [a for a in articles if a['source'].lower() == source.lower()]
    
    articles = articles[:limit]
    
    return jsonify({
        'count': len(articles),
        'articles': articles,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/archive', methods=['POST'])
def api_archive():
    """API endpoint to archive a new article"""
    data = request.json
    
    if not data or 'url' not in data:
        return jsonify({'error': 'URL required'}), 400
    
    url = data['url']
    title = data.get('title', 'Untitled Article')
    source = data.get('source', 'Unknown')
    
    archived = archive_system.archive_article(url, title, source)
    
    if archived:
        return jsonify({
            'success': True,
            'article': archived,
            'message': 'Article archived successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to archive article'
        }), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for archive statistics"""
    conn = sqlite3.connect(archive_system.db_path)
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute("SELECT COUNT(*) FROM articles WHERE archive_successful = 1")
    total_articles = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM articles WHERE relevance_score > 0.7")
    high_relevance = cursor.fetchone()[0]
    
    cursor.execute("SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY COUNT(*) DESC")
    sources = cursor.fetchall()
    
    cursor.execute("SELECT SUM(access_count) FROM articles")
    total_accesses = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'total_articles': total_articles,
        'high_relevance_articles': high_relevance,
        'sources': [{'name': s[0], 'count': s[1]} for s in sources],
        'total_accesses': total_accesses,
        'last_updated': datetime.now().isoformat()
    })

@app.route('/search')
def search():
    """Search archived articles"""
    query = request.args.get('q', '')
    source = request.args.get('source', '')
    
    conn = sqlite3.connect(archive_system.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if query:
        # Simple search in title and summary
        cursor.execute('''
            SELECT id, original_url, title, source, publication_date, 
                   summary, relevance_score
            FROM articles 
            WHERE archive_successful = 1 
            AND (title LIKE ? OR summary LIKE ?)
            ORDER BY relevance_score DESC
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%'))
    elif source:
        cursor.execute('''
            SELECT id, original_url, title, source, publication_date, 
                   summary, relevance_score
            FROM articles 
            WHERE archive_successful = 1 AND source = ?
            ORDER BY relevance_score DESC
            LIMIT 20
        ''', (source,))
    else:
        cursor.execute('''
            SELECT id, original_url, title, source, publication_date, 
                   summary, relevance_score
            FROM articles 
            WHERE archive_successful = 1
            ORDER BY relevance_score DESC
            LIMIT 20
        ''')
    
    articles = [dict(row) for row in cursor.fetchall()]
    
    # Add archive URLs
    for article in articles:
        article['archive_url'] = f"/archive/{archive_system.get_url_hash(article['original_url'])}"
    
    conn.close()
    
    return render_template('archive_search.html', 
                         articles=articles, 
                         query=query,
                         source=source)

# Create templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Create basic HTML templates
with open('templates/archive_index.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
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
        .article-title a { 
            color: inherit; 
            text-decoration: none;
        }
        .article-title a:hover { 
            color: #3b82f6;
        }
        .article-summary { 
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
        .view-btn { 
            padding: 0.5rem 1rem;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            font-size: 0.875rem;
        }
        .view-btn:hover { 
            background: #2563eb;
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
                <div class="stat-value">{{ stats.total_articles }}</div>
                <div class="stat-label">Total Articles Archived</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.high_relevance }}</div>
                <div class="stat-label">High Relevance Articles</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.sources|length }}</div>
                <div class="stat-label">Sources Monitored</div>
            </div>
        </div>
        
        <h2 style="margin: 2rem 0 1rem; font-size: 1.5rem;">Recent Archived Articles</h2>
        
        <div class="articles-grid">
            {% for article in articles %}
            <div class="article-card">
                <span class="article-source">{{ article.source }}</span>
                <h3 class="article-title">
                    <a href="{{ article.archive_url }}">{{ article.title }}</a>
                </h3>
                <p class="article-summary">{{ article.summary[:150] }}...</p>
                <div class="article-meta">
                    <span class="article-relevance">{{ (article.relevance_score * 100)|int }}% relevant</span>
                    <a href="{{ article.archive_url }}" class="view-btn">View Archive</a>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Quant Frontier Archive System • All articles archived for quant finance research</p>
            <p style="margin-top: 0.5rem; font-size: 0.875rem;">
                <a href="/search" style="color: #3b82f6; text-decoration: none;">Search Articles</a> • 
                <a href="/api/stats" style="color: #3b82f6; text-decoration: none;">API</a>
            </p>
        </div>
    </div>
</body>
</html>''')

with open('templates/archive_view.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ article.title }} - Quant Frontier Archive</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; 
            color: #f8fafc; 
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header { 
            background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%);
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        .header h1 { 
            font-size: 2rem; 
            font-weight: 700;
            margin-bottom: 1rem;
            line-height: 1.3;
        }
        .article-meta { 
            display: flex; 
            gap: 1rem;
            color: #cbd5e1;
            font-size: 0.875rem;
            margin-top: 1rem;
        }
        .article-source { 
            background: rgba(255, 255, 255, 0.1);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
        }
        .article-content { 
            background: #1e293b; 
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #475569;
            margin-top: 2rem;
            line-height: 1.8;
        }
        .article-content p { 
            margin-bottom: 1.5rem; 
        }
        .back-btn { 
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            margin-top: 2rem;
            font-weight: 600;
        }
        .back-btn:hover { 
            background: #2563eb;
        }
        .original-link { 
            margin-top: 2rem; 
            padding: 1rem;
            background: rgba(59, 130, 246, 0.1);
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }
        .original-link a { 
            color: #93c5fd; 
            text-decoration: none;
        }
        .original-link a:hover { 
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
            <h1>{{ article.title }}</h1>
            <div class="article-meta">
                <span class="article-source">{{ article.source }}</span>
                <span>Archived: {{ article.archive_date[:10] }}</span>
                <span>Relevance: {{ (article.relevance_score * 100)|int }}%</span>
            </div>
        </div>
        
        <div class="original-link">
            <strong>Original Article:</strong> 
            <a href="{{ article.original_url }}" target="_blank" rel="noopener">{{ article.original_url }}</a>
        </div>
        
        <div class="article-content">
            {{ article.content_text|replace('\\n', '<br>')|safe }}
        </div>
        
        <a href="/" class="back-btn">← Back to Archive</a>
        
        <div class="footer">
            <p>Quant Frontier Archive • Preserving quantitative finance research</p>
        </div>
    </div>
</body>
</html>''')

with open('templates/archive_search.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search - Quant Frontier Archive</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: