# GitHub Scout - Marketing Agent

**First agent in the marketing pipeline. Learns from trending AI repos.**

## What It Does

1. **Scrapes GitHub trending repos** (AI agents, ML, autonomous AI topics)
2. **Analyzes success tactics** using Claude web search:
   - README hook (opening line)
   - Demo video/GIF presence
   - Installation complexity (# of commands)
   - Show HN submission (if exists)
   - Launch tactics
3. **Builds success patterns** (aggregated insights)
4. **Outputs JSON files:**
   - `data/trending_repos.json` (repos with tactics)
   - `data/success_patterns.json` (recommendations)

## Setup

### 1. Get GitHub Personal Access Token

Go to: https://github.com/settings/tokens

Click: **"Generate new token (classic)"**

Name: `marketing-swarm-research`

Permissions: Check **`public_repo`**

Copy token → Paste into `.env`:

```bash
GITHUB_TOKEN=github_pat_YOUR_TOKEN_HERE
```

### 2. Install Dependencies

```bash
cd ~/Desktop/marketing-swarm/workspace/askelira
python3 -m venv venv
source venv/bin/activate
pip install anthropic requests
```

### 3. Test GitHub API

```bash
python -c "
import os
import requests

token = os.getenv('GITHUB_TOKEN')
if not token:
    print('❌ Set GITHUB_TOKEN in .env')
else:
    r = requests.get('https://api.github.com/rate_limit', headers={'Authorization': f'token {token}'})
    if r.status_code == 200:
        print('✅ GitHub API working!')
        print(f'Rate limit: {r.json()[\"rate\"][\"remaining\"]}/5000 remaining')
    else:
        print(f'❌ Error: {r.status_code}')
"
```

## Usage

### Run the Scout

```bash
cd ~/Desktop/marketing-swarm/workspace/askelira
source venv/bin/activate
python Agents/github_scout.py
```

**This will:**
1. Search GitHub for trending AI repos (500+ stars)
2. Analyze top 5 repos (takes ~3-5 minutes with web search)
3. Save results to `data/`

**Output:**
```
✅ GITHUB SCOUT COMPLETE

Found 5 trending repos

Success Pattern Recommendations:
  1. Add demo video/GIF (80% of successful repos have one)
  2. Simplify installation to ≤3 commands
  3. Launch on Show HN (60% of trending repos did)

Data saved to:
  - data/trending_repos.json
  - data/success_patterns.json
```

### View Results

```bash
# Trending repos
cat data/trending_repos.json | python -m json.tool

# Success patterns
cat data/success_patterns.json | python -m json.tool
```

## What You Get

### `data/trending_repos.json`

```json
[
  {
    "name": "cursor-ai/cursor",
    "url": "https://github.com/cursor-ai/cursor",
    "stars": 12500,
    "description": "AI-first code editor",
    "language": "TypeScript",
    "tactics": {
      "readme_hook": "The AI Code Editor. Built to make you extraordinarily productive.",
      "has_demo": true,
      "demo_url": "https://...",
      "install_steps": 1,
      "show_hn": {
        "exists": true,
        "score": 450,
        "url": "https://news.ycombinator.com/item?id=..."
      },
      "launch_tactics": ["demo_video", "show_hn", "twitter_launch"]
    }
  }
]
```

### `data/success_patterns.json`

```json
{
  "analyzed_repos": 5,
  "demo_percentage": 0.8,
  "avg_install_steps": 2.6,
  "show_hn_success_rate": 0.6,
  "recommendations": [
    "Add demo video/GIF (80% of successful repos have one)",
    "Simplify installation to ≤3 commands",
    "Launch on Show HN (60% of trending repos did)"
  ],
  "readme_hooks": [
    {
      "repo": "cursor-ai/cursor",
      "hook": "The AI Code Editor. Built to make you extraordinarily productive."
    }
  ],
  "common_tactics": ["demo_video", "show_hn", "twitter_launch"],
  "timestamp": "2026-03-15T10:30:00"
}
```

## Customize

### Change Topics

```python
result = run_scout(
    topics=["prediction-markets", "trading-bots", "mirofish"],
    min_stars=300,
    save=True
)
```

### Analyze More Repos

Edit line 233:
```python
for repo in unique_repos[:10]:  # Analyze top 10 (instead of 5)
```

### Use as Python Module

```python
from Agents.github_scout import run_scout

result = run_scout(
    topics=["ai-agents"],
    min_stars=1000,
    save=True
)

print(result['success_patterns']['recommendations'])
```

## Next Step

**After running GitHub Scout:**

Use the results to feed **MiroFish Trend Analyzer**:

```bash
python Agents/trend_analyzer.py --input data/success_patterns.json
```

This will simulate: "Will these tactics work for AskElira?"

## Troubleshooting

### "GITHUB_TOKEN not set"
Add to `.env`:
```
GITHUB_TOKEN=github_pat_YOUR_TOKEN_HERE
```

### "Rate limit exceeded"
GitHub API limit: 5,000 requests/hour

Check remaining:
```bash
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

### "Claude API error"
Check `ANTHROPIC_API_KEY` in `.env`

---

**This is the FIRST agent in the marketing pipeline.**

Next: Build MiroFish Trend Analyzer to validate which tactics work for us!
