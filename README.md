# QuantHub‑Terminal

A self‑automating GitHub Pages website that aggregates, summarizes, and ranks quantitative finance research and news — updated every 5 minutes.

## 🚀 Live Demo
[https://yourusername.github.io/QuantHub‑Terminal](https://yourusername.github.io/QuantHub‑Terminal)

## 📊 What It Does
- **Scrapes** arXiv (cs.CE, q‑fin.CP, q‑fin.ST), RSS feeds (Bloomberg Quant, Risk.net, SSRN), and GitHub trending repos
- **Summarizes** each paper/repo into 3 bullet points using an LLM (OpenAI/Claude)
- **Ranks** items by a weighted relevance score (mathematical complexity + market applicability)
- **Auto‑updates** via GitHub Actions every 5 minutes
- **Publishes** a clean, filterable Jekyll site on GitHub Pages

## 🛠️ Architecture
```
QuantHub‑Terminal/
├── fetch_quant.py              # Main Python scraper + LLM summarizer
├── .github/workflows/cron.yml  # 5‑minute GitHub Action
├── _data/quant_feed.json       # Generated JSON feed
├── _config.yml                 # Jekyll configuration
├── index.md                    # Front‑end with filtering
└── requirements.txt            # Python dependencies
```

## ⚙️ Setup

### 1. Clone & Configure
```bash
git clone https://github.com/yourusername/QuantHub‑Terminal
cd QuantHub‑Terminal
```

### 2. Set Environment Secrets (GitHub Repository Settings → Secrets)
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (for LLM summarization)
- `GITHUB_TOKEN` (auto‑generated; enable repo permissions)

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Test Locally
```bash
python fetch_quant.py
# Check _data/quant_feed.json
```

### 5. Deploy to GitHub Pages
- Push to `main` branch
- GitHub Actions will run automatically
- Enable GitHub Pages in repo settings (source: `main` branch)

## 🔄 The 5‑Minute Loop
1. GitHub Action triggers every 5 minutes
2. `fetch_quant.py` scrapes sources, calls LLM, ranks items
3. Updates `_data/quant_feed.json`
4. Auto‑commits and pushes changes
5. GitHub Pages rebuilds with fresh data

## 📈 Ranking Algorithm
Weighted score =  
`0.6 × relevance_score` (LLM‑assigned 1‑10) +  
`0.3 × recency` (1 if today, 0 if ≥7 days ago) +  
`0.1 × source_weight` (arXiv=1.0, RSS=0.9, GitHub=0.8) +  
`star_boost` (GitHub stars normalized)

## 🧠 LLM Prompt
```
You are a quantitative finance expert. Summarize the following research:

Title: [title]
Abstract/Text: [text]

Provide:
1. **The Core Idea** (one sentence)
2. **The Methodology** (one sentence)
3. **Key Quant Impact** (one sentence)
4. **Relevance Score** (1‑10, where 1=theoretical/academic, 10=immediate trading/risk applicability)
```

## 📁 Output Format
```json
{
  "last_updated": "2026‑03‑24T15:22:00Z",
  "items": [
    {
      "id": "2403.12345",
      "source": "arxiv",
      "title": "Deep Reinforcement Learning for High‑Frequency Portfolio Optimization",
      "authors": ["Jane Doe", "John Smith"],
      "core_idea": "Uses PPO to optimize HFT portfolios under transaction costs.",
      "methodology": "Multi‑agent RL with market‑impact models.",
      "quant_impact": "Reduces slippage by 18% in backtests.",
      "relevance_score": 9,
      "ranking_score": 87.4,
      "url": "https://arxiv.org/abs/2403.12345",
      "published": "2026‑03‑24T10:00:00Z"
    }
  ]
}
```

## 🧪 Customization
- Edit `CONFIG` in `fetch_quant.py` to add/remove sources
- Adjust ranking weights in `calculate_ranking_score()`
- Modify `index.md` styling and layout
- Change LLM model via `LLM_MODEL` environment variable

## 📄 License
MIT