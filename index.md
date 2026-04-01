---
layout: default
title: Quant Frontier
subtitle: AI‑currated frontier of quantitative finance research
---

{{ content }}

<script>
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
        if (item.source.includes('arxiv')) return 'arxiv';
        if (item.source.includes('github')) return 'github';
        if (item.source_type === 'news') return 'news';
        if (item.source_type === 'quant') return 'quant';
        return 'other';
    }

    function applyFilterAndSort() {
        let filtered = filterItems(allItems, currentFilter);
        const sortBy = document.getElementById('sort-select').value;
        filtered = sortItems(filtered, sortBy);
        renderFeed(filtered);
    }

    function filterItems(items, filter) {
        if (filter === 'all') return items;
        if (filter === 'quant') return items.filter(item => getItemCategory(item) === 'quant' || item.source.includes('arxiv'));
        if (filter === 'news') return items.filter(item => getItemCategory(item) === 'news');
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
            const hasArchive = item.archive_url;
            
            return `
                <article class="feed-card" data-category="${category}">
                    <div class="card-header">
                        <div class="source-tag source-${category}">
                            ${sourceName}
                            ${item.relevance_score >= 8 ? '<span class="high-relevance">★ High Impact</span>' : ''}
                        </div>
                        <div class="card-meta">
                            <span class="ranking">${item.ranking_score.toFixed(1)}</span>
                            <span class="date">${timeAgo}</span>
                        </div>
                    </div>
                    
                    <h3 class="card-title">
                        <a href="${hasArchive ? item.archive_url : item.url}" target="_blank" rel="noopener">${item.title}</a>
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
                        <div>
                            ${hasArchive ? `
                                <a href="${item.archive_url}" class="card-action" target="_blank" rel="noopener" title="Read via archive">
                                    Read Free
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M7 17L17 7M17 7H7M17 7V17"/>
                                    </svg>
                                </a>
                            ` : `
                                <a href="${item.url}" class="card-action" target="_blank" rel="noopener">
                                    Read
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M7 17L17 7M17 7H7M17 7V17"/>
                                    </svg>
                                </a>
                            `}
                        </div>
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
            'ssrn': 'SSRN',
            'cnbc': 'CNBC',
            'marketwatch': 'MarketWatch',
            'investing.com': 'Investing.com',
            'fxstreet': 'FXStreet',
            'coindesk': 'CoinDesk',
            'zerohedge': 'ZeroHedge',
            'seekingalpha': 'Seeking Alpha'
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