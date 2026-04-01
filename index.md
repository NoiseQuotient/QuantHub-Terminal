---
layout: default
title: Quant Frontier
subtitle: AI‑curated frontier of quantitative finance research
---

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<header class="site-header">
  <div class="container">
    <div class="header-content">
      <div class="header-text">
        <h1 class="site-title">{{ page.title }}</h1>
        <p class="site-subtitle">{{ page.subtitle }}</p>
        <p class="site-update">Live updates every 5 minutes • <span id="last-updated">Loading...</span></p>
      </div>
      <div class="header-badge">
        <div class="badge">
          <span class="badge-dot"></span>
          <span class="badge-text">LIVE</span>
        </div>
      </div>
    </div>
  </div>
</header>

<main class="container">
  <div class="controls-panel">
    <div class="filters-row">
      <div class="filter-group">
        <span class="filter-label">Filter:</span>
        <div class="filter-buttons">
          <button class="filter-btn active" data-filter="all">All Sources</button>
          <button class="filter-btn" data-filter="quant">Quant Research</button>
          <button class="filter-btn" data-filter="news">Financial News</button>
          <button class="filter-btn" data-filter="arxiv">arXiv</button>
          <button class="filter-btn" data-filter="github">GitHub</button>
        </div>
      </div>
      <div class="sort-group">
        <span class="filter-label">Sort:</span>
        <select class="sort-select" id="sort-select">
          <option value="ranking_score">Ranking Score</option>
          <option value="relevance_score">Relevance</option>
          <option value="published">Most Recent</option>
        </select>
      </div>
    </div>
    
    <div class="stats-bar">
      <div class="stat">
        <span class="stat-value" id="stats-count">—</span>
        <span class="stat-label">items</span>
      </div>
      <div class="stat">
        <span class="stat-value" id="stats-sources">—</span>
        <span class="stat-label">sources</span>
      </div>
      <div class="stat">
        <span class="stat-value" id="stats-time">—</span>
        <span class="stat-label">updated</span>
      </div>
    </div>
  </div>

  <div id="loading" class="loading-state">
    <div class="spinner"></div>
    <p>Loading quant frontier data...</p>
  </div>

  <div id="feed" class="feed-grid"></div>

  <div id="empty-state" class="empty-state" style="display: none;">
    <div class="empty-icon">📊</div>
    <h3>No items found</h3>
    <p>Try adjusting filters or check back soon. The feed updates every 5 minutes.</p>
  </div>
</main>

<footer class="site-footer">
  <div class="container">
    <div class="footer-content">
      <div class="footer-brand">
        <h4>Quant Frontier</h4>
        <p>AI‑powered quantitative finance research aggregator</p>
      </div>
      <div class="footer-links">
        <a href="https://github.com/NoiseQuotient/QuantHub-Terminal" target="_blank" rel="noopener">GitHub</a>
        <a href="/data/quant_feed.json" target="_blank" rel="noopener">JSON API</a>
        <span id="auto-refresh-status">Auto‑refresh enabled</span>
      </div>
    </div>
  </div>
</footer>

<script>
  let allItems = [];
  let currentFilter = 'all';

  // Initialize
  document.addEventListener('DOMContentLoaded', () => {
    loadFeed();
    setupEventListeners();
  });

  function setupEventListeners() {
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        applyFilterAndSort();
      });
    });

    // Sort select
    document.getElementById('sort-select').addEventListener('change', applyFilterAndSort);
  }

  async function loadFeed() {
    try {
      const response = await fetch('/data/quant_feed.json');
      if (!response.ok) throw new Error('Feed not available');
      const data = await response.json();
      
      allItems = data.items;
      updateStats(data.last_updated);
      applyFilterAndSort();
      
    } catch (error) {
      showError();
      console.error('Feed load error:', error);
    }
  }

  function updateStats(lastUpdated) {
    const date = new Date(lastUpdated);
    const sources = new Set(allItems.map(getItemCategory));
    
    document.getElementById('last-updated').textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    document.getElementById('stats-count').textContent = allItems.length;
    document.getElementById('stats-sources').textContent = sources.size;
    document.getElementById('stats-time').textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    document.getElementById('loading').style.display = 'none';
  }

  function getItemCategory(item) {
    if (item.source.includes('arxiv')) return 'arXiv';
    if (item.source.includes('github')) return 'GitHub';
    if (item.source_type === 'news') return 'News';
    if (item.source_type === 'quant') return 'Quant';
    return 'Other';
  }

  function applyFilterAndSort() {
    let filtered = filterItems(allItems, currentFilter);
    const sortBy = document.getElementById('sort-select').value;
    filtered = sortItems(filtered, sortBy);
    renderFeed(filtered);
  }

  function filterItems(items, filter) {
    if (filter === 'all') return items;
    if (filter === 'quant') return items.filter(item => getItemCategory(item) === 'Quant' || item.source.includes('arxiv'));
    if (filter === 'news') return items.filter(item => getItemCategory(item) === 'News');
    if (filter === 'arxiv') return items.filter(item => item.source.includes('arxiv'));
    if (filter === 'github') return items.filter(item => item.source.includes('github'));
    return items;
  }

  function sortItems(items, criteria) {
    const sorted = [...items];
    if (criteria === 'ranking_score') sorted.sort((a, b) => b.ranking_score - a.ranking_score);
    if (criteria === 'relevance_score') sorted.sort((a, b) => b.relevance_score - a.relevance_score);
    if (criteria === 'published') sorted.sort((a, b) => new Date(b.published || 0) - new Date(a.published || 0));
    return sorted;
  }

  function renderFeed(items) {
    const container = document.getElementById('feed');
    const emptyState = document.getElementById('empty-state');
    
    if (items.length === 0) {
      container.innerHTML = '';
      emptyState.style.display = 'block';
      return;
    }
    
    emptyState.style.display = 'none';
    
    container.innerHTML = items.map(item => {
      const category = getItemCategory(item);
      const sourceName = getSourceName(item.source);
      const timeAgo = getTimeAgo(item.published);
      
      return `
        <article class="feed-card" data-category="${category.toLowerCase()}">
          <div class="card-header">
            <div class="source-tag source-${category.toLowerCase()}">
              ${sourceName}
              ${item.relevance_score >= 8 ? '<span class="high-relevance">★ High Impact</span>' : ''}
            </div>
            <div class="card-meta">
              <span class="ranking">${item.ranking_score.toFixed(1)}</span>
              <span class="date">${timeAgo}</span>
            </div>
          </div>
          
          <h3 class="card-title">
            <a href="${item.url}" target="_blank" rel="noopener">${item.title}</a>
          </h3>
          
          ${item.authors ? `
            <div class="card-authors">
              ${item.authors.slice(0, 2).map(a => `<span class="author">${a}</span>`).join('')}
              ${item.authors.length > 2 ? '<span class="author-more">+' + (item.authors.length - 2) + '</span>' : ''}
            </div>
          ` : ''}
          
          <div class="card-summary">
            <div class="summary-point">
              <strong>Core Idea</strong>
              <p>${item.core_idea || 'Summary not available'}</p>
            </div>
            ${item.methodology ? `
            <div class="summary-point">
              <strong>Methodology</strong>
              <p>${item.methodology}</p>
            </div>
            ` : ''}
            ${item.quant_impact ? `
            <div class="summary-point">
              <strong>Quant Impact</strong>
              <p>${item.quant_impact}</p>
            </div>
            ` : ''}
          </div>
          
          <div class="card-footer">
            <div class="relevance-score">
              <span class="score-label">Relevance</span>
              <div class="score-bar">
                <div class="score-fill" style="width: ${item.relevance_score * 10}%"></div>
              </div>
              <span class="score-value">${item.relevance_score}/10</span>
            </div>
            <a href="${item.url}" class="card-action" target="_blank" rel="noopener">
              Read
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M7 17L17 7M17 7H7M17 7V17"/>
              </svg>
            </a>
          </div>
        </article>
      `;
    }).join('');
  }

  function getSourceName(sourceUrl) {
    const sources = {
      'arxiv': 'arXiv',
      'github': 'GitHub',
      'wsj': 'WSJ',
      'ft.com': 'Financial Times',
      'economist': 'The Economist',
      'bloomberg': 'Bloomberg',
      'reuters': 'Reuters',
      'risk.net': 'Risk.net',
      'ssrn': 'SSRN'
    };
    
    for (const [key, name] of Object.entries(sources)) {
      if (sourceUrl.includes(key)) return name;
    }
    return 'Research';
  }

  function getTimeAgo(dateStr) {
    if (!dateStr) return 'Recently';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  function showError() {
    document.getElementById('loading').innerHTML = `
      <div class="error-state">
        <div class="error-icon">⚠️</div>
        <h3>Unable to load feed</h3>
        <p>The system is updating. Check back in a few minutes.</p>
        <button onclick="loadFeed()" class="retry-btn">Retry</button>
      </div>
    `;
  }

  // Auto‑refresh every 5 minutes
  setInterval(loadFeed, 300000);
</script>

<style>
  :root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --secondary: #7c3aed;
    --accent: #06b6d4;
    --text: #1f2937;
    --text-light: #6b7280;
    --bg: #ffffff;
    --bg-alt: #f9fafb;
    --border: #e5e7eb;
    --card-bg: #ffffff;
    --shadow: 0 1px 3px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 25px -5px rgba(0,0,0,0.1);
    --radius: 8px;
    --radius-sm: 4px;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: var(--font-sans);
    color: var(--text);
    background: var(--bg-alt);
    line-height: 1.6;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
  }

  /* Header */
  .site-header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    color: white;
    padding: 3rem 0;
    margin-bottom: 2rem;
  }

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .site-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    line-height: 1.2;
  }

  .site-subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-bottom: 0.5rem;
  }

  .site-update {
    font-size: 0.9rem;
    opacity: 0.8;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(255,255,255,0.2);
    padding: 0.5rem 1rem;
    border-radius: 2rem;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .badge-dot {
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* Controls */
  .controls-panel {
    background: var(--bg);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin-bottom: 2rem;
    box-shadow: var(--shadow);
  }

  .filters-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .filter-label {
    font-weight: 600;
    color: var(--text-light);
    font-size: 0.875rem;
  }

  .filter-buttons {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .filter-btn {
    padding: 0.5rem 1rem;
    background: var(--bg-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-light);
    cursor: pointer;
    transition: all 0.2s;
  }

  .filter-btn:hover {
    background: var(--border);
  }

  .filter-btn.active {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
  }

  .sort-select {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    background: var(--bg);
    color: var(--text);
  }

  .stats-bar {
    display: flex;
    gap: 2rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
  }

  .stat {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
  }

  .stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--primary);
  }

  .stat-label {
    font-size: 0.875rem;
    color: var(--text-light);
  }

  /* Feed */
  .feed-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
  }

  .feed-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    transition: transform 0.2s, box-shadow 0.2s;
