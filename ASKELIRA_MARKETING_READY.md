# AskElira Marketing — Autonomous Viral Marketing Module

## The Meta-Play

AskElira Marketing uses swarm intelligence to create viral campaigns for **[github.com/jellyforex/askelira](https://github.com/jellyforex/askelira)**.

Every GitHub star = proof AskElira's swarm intelligence works.
Every Show HN upvote = proof the platform can market itself.
AskElira Marketing is AskElira deployed for autonomous viral distribution.

**Goal:** 100+ GitHub stars in week 1. GitHub trending. Show HN front page.

---

## Architecture

```
Alba (github_scout.py)
    ↓ data/trending_repos.json + data/success_patterns.json
TrendAnalyzer (trend_analyzer.py)
    ↓ data/improvement_plan.json  [MiroFish confidence scores]
    ↓
    ├── Scribe (scribe.py) ──────── data/content/twitter.json
    │                               data/content/reddit.json
    │                               data/content/show_hn.json
    │                               data/content/linkedin.json
    │                               data/content/readme.json
    │
    ├── Lens (lens.py) ─────────── data/media/poster.png
    │                               data/media/thumbnail.png
    │                               data/media/demo.mp4
    │
    └── Pixel (pixel.py) ─────────  data/readme_diff.md
                    ↓
            Elira Marketing (elira_marketing.py)
                    ↓
            Terminal Preview + Approval Gate
                    ↓ (human approves)
            Publish (manual: Twitter, Reddit, Show HN)
```

---

## The 5 Marketing Agents

| Agent | File | Role |
|-------|------|------|
| **Alba** | `Agents/github_scout.py` | Scouts GitHub trending repos. Extracts viral tactics (demo videos, install steps, Show HN launches). |
| **TrendAnalyzer** | `Agents/trend_analyzer.py` | Runs MiroFish simulations (or Claude fallback) to score each tactic. Outputs confidence percentages. |
| **Scribe** | `Agents/scribe.py` | Generates Twitter thread, Reddit post, Show HN draft, LinkedIn post, README proposal — all in parallel. |
| **Lens** | `Agents/lens.py` | Produces campaign poster, YouTube thumbnail, 60-second demo video via ffmpeg. |
| **Pixel** | `Agents/pixel.py` | Analyzes README.md and generates a unified diff with viral improvements. Preview only — doesn't push. |

Coordinated by **Elira Marketing** (`Agents/elira_marketing.py`), which manages state, renders the terminal preview, and gates the approval.

---

## First Run

### Prerequisites

1. **ANTHROPIC_API_KEY** — already set in `.env`
2. **GITHUB_TOKEN** — needs a real token:
   - GitHub → Settings → Developer settings → Personal access tokens → Fine-grained
   - Scope: Public repositories (read-only)
   - Paste into `.env`: `GITHUB_TOKEN=github_pat_...`
3. **Python deps:**
   ```bash
   cd workspace/askelira
   pip install -r requirements.txt
   ```

### Run

```bash
cd workspace/askelira

# Safe dry run (no API calls — good for testing the pipeline)
python campaign.py --dry-run

# Phase 1 only: Test Alba (requires GITHUB_TOKEN)
python campaign.py --phase=1

# Phase 2 only: Run TrendAnalyzer without MiroFish
python campaign.py --phase=2 --skip-mirofish

# Full pipeline (MiroFish optional — falls back to Claude)
python campaign.py --fresh --skip-mirofish

# Full pipeline with MiroFish (requires Docker running)
python campaign.py --fresh
```

### What happens after approval

AskElira Marketing does NOT auto-post. After you approve the campaign:
1. Review `data/content/twitter.json` → post thread manually on Twitter/X
2. Review `data/content/show_hn.json` → submit to [news.ycombinator.com/submit](https://news.ycombinator.com/submit)
3. Review `data/content/reddit.json` → post to r/MachineLearning and r/algotrading
4. Review `data/readme_diff.md` → apply improvements to README.md manually

---

## CLI Reference

```
python campaign.py [options]

Options:
  --dry-run           No API calls; tests the pipeline flow
  --phase=N           Run only phase N (1-6) and exit
  --skip-mirofish     Use Claude instead of MiroFish for confidence scoring
  --fresh             Ignore state.json; restart from Phase 1
  --target=REPO       Override target repo (default: jellyforex/askelira)
  --topics=TOPICS     GitHub topics to scout (comma-separated)
  --verbose           DEBUG logging
```

### Phase numbers

| Phase | Agent | Output |
|-------|-------|--------|
| 1 | Alba (github_scout) | `data/trending_repos.json`, `data/success_patterns.json` |
| 2 | TrendAnalyzer | `data/improvement_plan.json` |
| 3 | Scribe | `data/content/*.json` (5 files) |
| 4 | Lens | `data/media/` (poster, thumbnail, video) |
| 5 | Pixel | `data/readme_diff.md` |
| 6 | Elira Marketing | Terminal preview + approval gate |

---

## Data Files

```
workspace/askelira/data/
├── trending_repos.json      # Phase 1: Trending repos with tactics
├── success_patterns.json    # Phase 1: Aggregated viral patterns
├── improvement_plan.json    # Phase 2: Confidence-scored tactics
├── seeds/                   # Phase 2: MiroFish seed files
├── content/
│   ├── twitter.json         # Phase 3: 12-tweet thread
│   ├── reddit.json          # Phase 3: r/ML + r/algotrading post
│   ├── show_hn.json         # Phase 3: Show HN draft
│   ├── linkedin.json        # Phase 3: LinkedIn post
│   └── readme.json          # Phase 3: README section proposals
├── media/
│   ├── poster.png           # Phase 4: Campaign poster
│   ├── thumbnail.png        # Phase 4: YouTube thumbnail
│   ├── demo.mp4             # Phase 4: 60-second demo video
│   └── slides/              # Phase 4: Individual slide PNGs
├── readme_diff.md           # Phase 5: README improvement preview
├── state.json               # Pipeline state (phase completion)
└── campaign.log             # Full run log
```

---

## Success Metrics

| Metric | Week 1 Goal | Month 1 Goal |
|--------|-------------|--------------|
| GitHub stars | 100+ | 500+ |
| GitHub trending | Yes | Sustained |
| Show HN | Front page | — |
| Reddit upvotes | 50+ | — |
| Forks | 10+ | 50+ |

Every metric is proof AskElira's swarm intelligence works.

---

## MiroFish Integration

If MiroFish Docker is running (`MIROFISH_URL=http://localhost:5001`):
- TrendAnalyzer runs 3 simulations per tactic
- Agent population: 40% developers, 30% HN users, 20% founders, 10% OSS
- Variance gate: >15% variance marks tactic "unstable" (doesn't block)
- Confidence scores appear in the terminal preview

If MiroFish is down: automatic Claude fallback — `--skip-mirofish` forces this.

---

*AskElira Marketing is part of AskElira v1.0 — the self-improving viral marketing engine.*
*Target: https://github.com/jellyforex/askelira*
