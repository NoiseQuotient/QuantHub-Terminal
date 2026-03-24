---
layout: default
title: Quant Frontier
subtitle: AI‑curated frontier of quantitative finance research, updated every 5 minutes
---

<div class="header">
  <h1>{{ page.title }}</h1>
  <p class="subtitle">{{ page.subtitle }}</p>
  <p class="last-updated">Last updated: <span id="last-updated">Loading...</span></p>
</div>

<div class="controls">
  <button onclick="filterBySource('all')">All Sources</button>
  <button onclick="filterBySource('quant')">Quant Research</button>
  <button onclick="filterBySource('news')">Financial News</button>
  <button onclick="filterBySource('arxiv')">arXiv</button>
  <button onclick="filterBySource('github')">GitHub</button>
  <select onchange="sortBy(this.value)">
    <option value="ranking_score">Ranking Score</option>
    <option value="relevance_score">Relevance</option>
    <option value="published">Recent</option>
  </select>
</div>

<div id="loading">Loading quant feed...</div>

<div id="feed" class="feed"></div>

<script>
  let allItems = [];

  async function loadFeed() {
    try {
      // Try direct JSON file (GitHub Pages serves _data as /data/)
      const response = await fetch('{{ site.baseurl }}/data/quant_feed.json');
      if (!response.ok) throw new Error('JSON not found');
      const data = await response.json();
      document.getElementById('last-updated').textContent = new Date(data.last_updated).toLocaleString();
      allItems = data.items;
      renderFeed(allItems);
    } catch (error) {
      // Fallback: use inline data if available
      {% if site.data.quant_feed %}
        allItems = {{ site.data.quant_feed.items | jsonify }};
        document.getElementById('last-updated').textContent = '{{ site.data.quant_feed.last_updated }}';
        renderFeed(allItems);
      {% else %}
        document.getElementById('loading').innerHTML = '<p style="color: #e74c3c;">No feed data available yet. First update in progress.</p>';
        console.error('Feed load error:', error);
      {% endif %}
    }
  }

  function renderFeed(items) {
    const container = document.getElementById('feed');
    const loading = document.getElementById('loading');
    loading.style.display = 'none';

    if (items.length === 0) {
      container.innerHTML = '<p>No items found.</p>';
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="card" data-source="${item.source}">
        <div class="card-header">
          <span class="source-badge ${item.source}">${item.source.toUpperCase()}</span>
          <span class="score">Rank: ${item.ranking_score.toFixed(1)}</span>
        </div>
        <h3><a href="${item.url}" target="_blank">${item.title}</a></h3>
        <div class="meta">
          ${item.authors ? `<span class="authors">${item.authors.slice(0, 3).join(', ')}${item.authors.length > 3 ? ' et al.' : ''}</span>` : ''}
          <span class="date">${formatDate(item.published)}</span>
          ${item.stars ? `<span class="stars">⭐ ${item.stars}</span>` : ''}
        </div>
        <div class="summary">
          <p><strong>Core Idea:</strong> ${item.core_idea}</p>
          <p><strong>Methodology:</strong> ${item.methodology}</p>
          <p><strong>Quant Impact:</strong> ${item.quant_impact}</p>
        </div>
        <div class="footer">
          <span class="relevance">Relevance: ${item.relevance_score}/10</span>
          <a href="${item.url}" class="btn" target="_blank">Read →</a>
        </div>
      </div>
    `).join('');
  }

  function filterBySource(source) {
    let filtered;
    if (source === 'all') {
      filtered = allItems;
    } else if (source === 'quant') {
      filtered = allItems.filter(item => item.source_type === 'quant' || item.source === 'arxiv' || item.source === 'github');
    } else if (source === 'news') {
      filtered = allItems.filter(item => item.source_type === 'news');
    } else {
      filtered = allItems.filter(item => item.source === source);
    }
    renderFeed(filtered);
  }

  function sortBy(criteria) {
    const sorted = [...allItems];
    if (criteria === 'ranking_score') sorted.sort((a, b) => b.ranking_score - a.ranking_score);
    if (criteria === 'relevance_score') sorted.sort((a, b) => b.relevance_score - a.relevance_score);
    if (criteria === 'published') sorted.sort((a, b) => new Date(b.published) - new Date(a.published));
    renderFeed(sorted);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  // Initial load
  loadFeed();
  // Auto‑refresh every 5 minutes
  setInterval(loadFeed, 300000);
</script>

<style>
  .header {
    text-align: center;
    margin-bottom: 2rem;
  }
  .subtitle {
    color: #666;
    font-size: 1.1rem;
  }
  .last-updated {
    font-size: 0.9rem;
    color: #888;
  }
  .controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }
  .controls button, .controls select {
    padding: 0.5rem 1rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: white;
    cursor: pointer;
  }
  .feed {
    display: grid;
    gap: 1.5rem;
  }
  .card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1.5rem;
    background: #fafafa;
    transition: box-shadow 0.2s;
  }
  .card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }
  .source-badge {
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: bold;
    color: white;
  }
  .source-badge.arxiv {
    background: #3498db;
  }
  .source-badge.github {
    background: #2ecc71;
  }
  .source-badge.rss {
    background: #e74c3c;
  }
  .score {
    font-weight: bold;
    color: #2c3e50;
  }
  .card h3 {
    margin: 0.5rem 0;
    font-size: 1.25rem;
  }
  .card h3 a {
    color: #2980b9;
    text-decoration: none;
  }
  .card h3 a:hover {
    text-decoration: underline;
  }
  .meta {
    font-size: 0.9rem;
    color: #555;
    margin-bottom: 1rem;
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .summary p {
    margin: 0.5rem 0;
    line-height: 1.5;
  }
  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #eee;
  }
  .relevance {
    font-weight: bold;
    color: #27ae60;
  }
  .btn {
    padding: 0.4rem 1rem;
    background: #2980b9;
    color: white;
    border-radius: 4px;
    text-decoration: none;
    font-size: 0.9rem;
  }
  .btn:hover {
    background: #1c5d87;
  }
</style>