# QuantHub‑Terminal Setup Checklist

## ✅ 1. Repository Created
- **Repo:** https://github.com/NoiseQuotient/QuantHub‑Terminal
- **Branch:** `main` (pushed with all code except workflow file)

## 🔐 2. Set GitHub Secrets
Go to **Settings → Secrets and variables → Actions** → **New repository secret**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `OPENAI_API_KEY` | Your OpenAI API key (starts with `sk-`) |
| `ANTHROPIC_API_KEY` | (Optional) Claude API key |
| `GITHUB_TOKEN` | Auto‑generated (no need to set) |

## ⚙️ 3. Add GitHub Actions Workflow
**Method A (Recommended):** Copy the workflow file via GitHub UI
1. Go to https://github.com/NoiseQuotient/QuantHub-Terminal
2. Click "Add file" → "Create new file"
3. Path: `.github/workflows/cron.yml`
4. Paste content from [cron.yml](.github/workflows/cron.yml) in this workspace
5. Commit directly to `main` branch

**Method B:** Use GitHub CLI (if you have `gh` installed)
```bash
gh workflow add .github/workflows/cron.yml
```

## 🌐 4. Enable GitHub Pages
1. Go to **Settings → Pages**
2. **Source:** Deploy from a branch → `main` branch
3. **Folder:** `/ (root)`
4. Save

Wait 1‑2 minutes, then visit:  
**https://noisequotient.github.io/QuantHub‑Terminal**

## 🧪 5. Test Locally (Optional)
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your_key"
python fetch_quant.py
# Check _data/quant_feed.json
```

## 🔄 6. Verify Automation
- The GitHub Action will run every 5 minutes
- Check **Actions** tab in your repo
- Each run should update `_data/quant_feed.json` and trigger a Pages rebuild

## 📝 7. Customization
- Edit `fetch_quant.py` → `CONFIG` to add/remove sources
- Modify ranking weights in `calculate_ranking_score()`
- Update `_config.yml` and `index.md` styling

## 🚨 Troubleshooting
- **Workflow fails:** Check Actions log for missing dependencies or API key issues
- **No data:** Verify RSS feeds are accessible; arXiv API may have rate limits
- **Pages not updating:** Ensure `_data/quant_feed.json` is being committed

---

**Live site will be ready within 5 minutes of completing steps 2‑4.**