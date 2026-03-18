# AskElira Marketing - Viral Marketing Automation

> **Built on the [AskElira Framework](https://github.com/AskElira/askelira)** - Multi-agent orchestration with swarm intelligence

**Automate viral marketing campaigns for ANY GitHub project.**

Scout trending repos → Validate tactics with AI swarm → Generate multi-platform content → Get 100+ stars in week 1.

## What It Does

**Input:** Your GitHub repo URL + campaign goal

**Output:** Complete viral marketing campaign:
- Twitter thread (12 tweets)
- Show HN post
- Reddit submissions (r/MachineLearning, relevant subs)
- LinkedIn post
- README improvements
- Campaign posters/videos

**Validated by:** 1000+ AI agents simulating developers/founders/HN users

**Cost:** $0.02 per campaign

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/AskElira/askeliramarketing.git
cd askeliramarketing

# 2. Install
pip install -r requirements.txt

# 3. Setup
cp .env.example .env
# Add your ANTHROPIC_API_KEY, GITHUB_TOKEN

# 4. Generate campaign
python campaign.py --target="your-username/your-repo" --goal="100 stars week 1"
```

First campaign takes ~3 minutes. Content appears in `data/content/`

---

## The 5-Agent Pipeline

Built on the AskElira Framework 5-agent pattern:

| Agent | Role | What They Do |
|-------|------|--------------|
| **Alba (Scout)** | Trending Researcher | Scrapes GitHub trending, extracts viral tactics |
| **TrendAnalyzer** | Validation Engine | Simulates 1000 agents debating which tactics work |
| **Scribe** | Content Creator | Generates Twitter, HN, Reddit, LinkedIn content |
| **Lens** | Media Producer | Creates posters, videos, thumbnails |
| **Pixel** | Interface Manager | Generates README improvement diffs |

**+ MiroFish:** Swarm intelligence engine (validates tactics before applying them)

---

## How It Works

### 1. Scout Trending Repos

```bash
python -m Agents.github_scout --topics="ai-agents,machine-learning"
```

Alba finds repos with 500+ stars, extracts their viral tactics:
- README hooks
- Demo presence
- Install complexity
- Show HN success
- Launch strategies

Output: `data/trending_repos.json`, `data/success_patterns.json`

### 2. Validate Tactics (MiroFish Swarm)

```bash
python campaign.py --phase=2 --target="your-username/your-repo"
```

Simulates 1000 AI agents (developers, founders, HN users) debating:
- "Will 3-step install work for this repo?"
- "Do developers care about demo videos for this use case?"
- "Will 'concrete results' hook resonate?"

Output: `data/improvement_plan.json` with confidence scores (0-100%)

### 3. Generate Content

```bash
python campaign.py --target="your-username/your-repo"
```

Creates all content in parallel:
- **Twitter:** 12-tweet thread with hooks, metrics, CTAs
- **Show HN:** Technical depth + humble questions
- **Reddit:** Platform-specific formatting
- **LinkedIn:** Professional tone + hashtags
- **README:** Hero, demo, CTA sections

Output: `data/content/*.json`

### 4. Review & Approve

```
Campaign Preview:
- Target: github.com/your-username/your-repo
- Top Tactic: Concrete demos (82% confidence)
- Cost: $0.02

Content ready. Approve? (y/n)
```

Nothing posts without your approval.

---

## Use Cases

**What can you market with this?**

1. **Open Source Projects** — Get your repo trending
2. **SaaS Products** — Launch campaigns, drive signups
3. **Personal Brands** — Grow your GitHub profile
4. **Blog Posts** — Viral distribution across platforms
5. **Research Papers** — Reach wider audience

Works for AI/ML projects, developer tools, SaaS products, frameworks/libraries, and any GitHub repo.

---

## Framework

AskElira Marketing is the marketing use case of the AskElira Framework.

**Other AskElira Applications:**
- [AskElira Trader](https://github.com/AskElira/AskEliraTrader) — Prediction market trading (65% accuracy)
- [AskElira Framework](https://github.com/AskElira/askelira) — Build your own automation

Want to build your own? Fork the framework and adapt the 5-agent pattern to your domain (sales, research, analysis, etc.)

---

## Configuration

Environment variables (`.env`):

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...

# Optional (for auto-posting)
TWITTER_API_KEY=...
REDDIT_CLIENT_ID=...
OPENAI_API_KEY=...    # for DALL-E posters
```

Campaign flags:

```bash
python campaign.py \
  --target="username/repo" \
  --goal="100 stars week 1" \
  --topics="ai-agents,python" \
  --dry-run        # Safe test mode
  --skip-mirofish  # Faster (uses Claude fallback)
  --fresh          # Ignore cached state
```

---

## Documentation

- [Architecture](ASKELIRA_MARKETING_READY.md)
- [Agent Details](Agents/)
- [Campaign CLI](campaign.py)
- [MiroFish Validation](mirofish_client.py)

---

## Contributing

Contributions welcome!

Areas we need help:
- New platform integrations (TikTok, YouTube, Medium)
- Cost optimization
- Alternative swarm implementations
- Campaign templates

---

## License

MIT License — see LICENSE

---

## Links

- Framework: [github.com/AskElira/askelira](https://github.com/AskElira/askelira)
- Trader Use Case: [github.com/AskElira/AskEliraTrader](https://github.com/AskElira/AskEliraTrader)

---

**Built with 🧠 by the [AskElira Team](https://github.com/AskElira)**
