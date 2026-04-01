# Add GitHub Actions Workflow (Manual)

Since the token lacks `workflow` scope, add the workflow file manually:

## Steps
1. Go to: https://github.com/NoiseQuotient/QuantHub-Terminal
2. Click "Add file" → "Create new file"
3. Path: `.github/workflows/cron.yml`
4. Paste this content:

```yaml
name: QuantHub 5‑Minute Update
on:
  schedule:
    # GitHub Actions minimum interval is 5 minutes
    - cron: '*/5 * * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  update-feed:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run QuantHub scraper
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          LLM_MODEL: "gpt-4o-mini"
        run: python fetch_quant.py

      - name: Commit and push changes
        run: |
          git config --global user.name "QuantHub Bot"
          git config --global user.email "bot@quanthub.example.com"
          git add _data/quant_feed.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Auto‑update quant feed [skip ci]"
          git push
```

5. Commit directly to `main` branch

## Set Secrets
1. Go to **Settings → Secrets and variables → Actions**
2. Add **New repository secret**:
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key (starts with `sk-`)

## Verify
- Check **Actions** tab → workflow should run within 5 minutes
- Visit: https://noisequotient.github.io/QuantHub-Terminal/

The site will auto‑update every 5 minutes with fresh quant research!