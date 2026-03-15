"""
Scribe — Parallel Content Creator

Reads improvement_plan.json from TrendAnalyzer and generates:
- Twitter/X thread (12 tweets)
- Reddit post (r/MachineLearning, r/algotrading)
- Show HN draft
- LinkedIn post
- README improvement proposal

All 5 generated simultaneously via ThreadPoolExecutor.
All content targets: github.com/jellyforex/askelira

Third agent in the marketing pipeline.
"""

import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
from dotenv import load_dotenv

log = logging.getLogger("scribe")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTENT_DIR = DATA_DIR / "content"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

IMPROVEMENT_PLAN_FILE = DATA_DIR / "improvement_plan.json"

TARGET_REPO = "jellyforex/askelira"
TARGET_URL = f"https://github.com/{TARGET_REPO}"

MODEL = "claude-sonnet-4-5"

# ------------------------------------------------------------------ #
# Platform system prompts
# ------------------------------------------------------------------ #

SYSTEM_TWITTER = """You write punchy, technical Twitter/X threads for developer audiences.
Rules:
- Each tweet ≤280 characters (count carefully)
- Number tweets 1/12 through 12/12
- First tweet is the hook — make developers stop scrolling
- Include real specifics: accuracy numbers, agent names, MiroFish
- No generic hype like "Revolutionary!" or "Game-changing!"
- End with GitHub link and CTA to star
- Technical but accessible to ML engineers and Python devs
Output format: JSON array of 12 tweet strings."""

SYSTEM_REDDIT = """You write authentic, non-promotional Reddit posts for technical communities.
Rules:
- No marketing speak, no hype, no corporate tone
- Show real data, real code examples, real limitations
- Acknowledge what doesn't work yet
- r/MachineLearning audience: researchers, ML engineers, PhD students
- r/algotrading audience: quant traders, finance devs, data scientists
- Lead with what you built and why, then how it works technically
- Include honest accuracy numbers
Output format: JSON with title, body (markdown), and subreddits list."""

SYSTEM_SHOW_HN = """You write Show HN submissions that make Hacker News front page.
Rules:
- First line format: "Show HN: [concise description]" — this is the title
- HN audience: engineers, founders, skeptics who hate hype
- Be technical and humble: explain what it actually does
- Mention open source, MIT license, self-hostable
- Include the surprising/interesting technical detail (MiroFish swarm)
- Acknowledge current limitations honestly
- No emojis, no marketing language
Output format: JSON with title (the Show HN: line) and body (plain text, no markdown headers)."""

SYSTEM_LINKEDIN = """You write professional LinkedIn posts for AI founders and technical operators.
Rules:
- Hook in first 2 lines (before "see more")
- Professional but direct tone — not corporate speak
- Focus on the product insight, not the hype
- Include specific numbers and results
- End with clear CTA (link to GitHub, ask for feedback)
- Hashtags at end, 3-5 relevant ones
Output format: JSON with post (string) and hashtags (array)."""

SYSTEM_README = """You propose specific improvements to a GitHub README.md to maximize viral appeal.
Rules:
- Propose changes to: hero section, demo section, quick-start section, CTA section
- Keep technical accuracy — don't oversell
- Make install steps shorter if possible (target ≤3 commands)
- Suggest adding demo video link/embed
- Propose stronger opening hook
- Each section improvement should explain the rationale
Output format: JSON with sections array, each having: section_name, proposed_content, rationale."""


# ------------------------------------------------------------------ #
# Data loading
# ------------------------------------------------------------------ #

def load_improvement_plan(path: Path = IMPROVEMENT_PLAN_FILE) -> Dict:
    """Load improvement_plan.json from TrendAnalyzer."""
    if not path.exists():
        raise FileNotFoundError(
            f"improvement_plan.json not found at {path}\n"
            "Run Phase 2 first: python -m Agents.trend_analyzer --skip-mirofish"
        )
    with open(path) as f:
        return json.load(f)


def _build_context(plan: Dict, target_repo: str) -> str:
    """Build context string from plan for use in all prompts."""
    tactics_text = "\n".join(
        f"  {t['priority']}. [{t['confidence']}%] {t['name']}"
        for t in plan.get("tactics", [])[:5]
    )
    return f"""Target repository: https://github.com/{target_repo}

Project: AskElira — Multi-agent binary outcome prediction system
- 5 AI agents: Alba (research), David (simulations), Vex (audit), Elira (orchestrator), Steven (executor)
- MiroFish swarm: 1000+ AI agents simulate crowd behavior to predict YES/NO outcomes
- Prediction markets: Polymarket, Kalshi
- Accuracy: ~65% overall, ~75% high-confidence (>80%)
- Cost: ~$0.015 per prediction
- License: MIT, fully open source
- Self-hostable (Docker + Python)

Campaign theme: {plan.get('campaign_theme', 'Watch the swarm think: AskElira live demo')}

Top tactics (confidence-scored by MiroFish simulation):
{tactics_text}

Top tactic: {plan.get('top_tactic', '')}"""


# ------------------------------------------------------------------ #
# Content generators (each runs in its own thread)
# ------------------------------------------------------------------ #

def generate_twitter_thread(plan: Dict, target_repo: str) -> Dict:
    """Generate a 12-tweet thread. Each tweet gets its own anthropic client (thread-safe)."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = _build_context(plan, target_repo)

    prompt = f"""Write a 12-tweet thread launching AskElira on GitHub.

{context}

Tweet 1 must start with: "Just open-sourced AskElira: 5 AI agents + MiroFish swarm intelligence that predict ANYTHING binary"
Then: explain what it does, how the swarm works, accuracy numbers, demo, install, and end with GitHub CTA.

Respond with a JSON array of exactly 12 tweet strings. Each ≤280 chars. Include tweet numbers like "1/12" at end."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_TWITTER,
        messages=[{"role": "user", "content": prompt}]
    )

    tweets = []
    for block in response.content:
        if block.type == "text":
            json_match = re.search(r'\[[\s\S]*\]', block.text)
            if json_match:
                tweets = json.loads(json_match.group())
                break

    if not tweets:
        # Fallback: split by newlines and clean up
        text = response.content[0].text if response.content else ""
        tweets = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 20][:12]

    return {
        "platform": "twitter",
        "tweets": tweets,
        "character_counts": [len(t) for t in tweets],
        "target_repo": target_repo,
        "generated_at": datetime.utcnow().isoformat(),
    }


def generate_reddit_post(plan: Dict, target_repo: str) -> Dict:
    """Generate a Reddit post for r/MachineLearning and r/algotrading."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = _build_context(plan, target_repo)

    prompt = f"""Write a Reddit post to launch AskElira.

{context}

Primary target: r/MachineLearning
Secondary: r/algotrading

Include:
- Technical explanation of how MiroFish swarm simulation works
- Real accuracy numbers and what categories perform best
- Code snippet showing how to run a prediction
- Honest limitations (needs Docker for MiroFish, requires API keys)
- Link to GitHub: https://github.com/{target_repo}

Respond with JSON: {{"title": "...", "body": "...markdown...", "subreddits": ["MachineLearning", "algotrading"]}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_REDDIT,
        messages=[{"role": "user", "content": prompt}]
    )

    result = {"platform": "reddit", "title": "", "body": "", "subreddits": ["MachineLearning", "algotrading"], "generated_at": datetime.utcnow().isoformat()}
    for block in response.content:
        if block.type == "text":
            json_match = re.search(r'\{[\s\S]*\}', block.text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    result.update(parsed)
                except Exception:
                    pass
            break

    result["target_repo"] = target_repo
    result["platform"] = "reddit"
    return result


def generate_show_hn(plan: Dict, target_repo: str) -> Dict:
    """Generate a Show HN submission."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = _build_context(plan, target_repo)

    prompt = f"""Write a Show HN submission for AskElira.

{context}

The title MUST be: "Show HN: AskElira – 5 AI agents + MiroFish swarm predict binary outcomes (open source)"

Body should explain:
1. What you built (1 sentence)
2. How it actually works technically (MiroFish, the 5 agents, the pipeline)
3. Real example: "We asked 'Will the Fed cut rates in March?' — here's what the swarm showed"
4. Accuracy data
5. How to try it (3 commands max)
6. GitHub link: https://github.com/{target_repo}
7. What you want feedback on

Respond with JSON: {{"title": "Show HN: ...", "body": "plain text..."}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM_SHOW_HN,
        messages=[{"role": "user", "content": prompt}]
    )

    result = {
        "platform": "show_hn",
        "title": f"Show HN: AskElira – 5 AI agents + MiroFish swarm predict binary outcomes (open source)",
        "body": "",
        "target_repo": target_repo,
        "generated_at": datetime.utcnow().isoformat(),
    }
    for block in response.content:
        if block.type == "text":
            json_match = re.search(r'\{[\s\S]*\}', block.text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    result.update(parsed)
                except Exception:
                    pass
            break

    result["platform"] = "show_hn"
    return result


def generate_linkedin_post(plan: Dict, target_repo: str) -> Dict:
    """Generate a LinkedIn post."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = _build_context(plan, target_repo)

    prompt = f"""Write a LinkedIn post launching AskElira.

{context}

Audience: AI founders, quant traders, ML engineers
Hook first (2 lines before "see more"): Something that makes technical founders stop scrolling
Include: the swarm intelligence angle, accuracy numbers, open source CTA
GitHub link: https://github.com/{target_repo}

Respond with JSON: {{"post": "...", "hashtags": ["AI", "OpenSource", ...]}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_LINKEDIN,
        messages=[{"role": "user", "content": prompt}]
    )

    result = {
        "platform": "linkedin",
        "post": "",
        "hashtags": ["AI", "OpenSource", "MachineLearning", "PredictionMarkets"],
        "target_repo": target_repo,
        "generated_at": datetime.utcnow().isoformat(),
    }
    for block in response.content:
        if block.type == "text":
            json_match = re.search(r'\{[\s\S]*\}', block.text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    result.update(parsed)
                except Exception:
                    pass
            break

    result["platform"] = "linkedin"
    return result


def generate_readme_proposal(plan: Dict, target_repo: str) -> Dict:
    """Generate README improvement proposals."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = _build_context(plan, target_repo)

    # Read current README for context
    readme_path = Path(__file__).parent.parent / "README.md"
    readme_content = ""
    if readme_path.exists():
        with open(readme_path) as f:
            readme_content = f.read()[:3000]  # first 3000 chars

    prompt = f"""Propose improvements to the AskElira README.md for maximum GitHub viral appeal.

{context}

Current README (first 3000 chars):
{readme_content}

Propose improvements to these sections:
1. Hero headline (opening H1 + tagline) — make it a hook that makes developers star immediately
2. Demo section — add 60s demo video placeholder + improve quick start
3. CTA section — star, contribute, show HN, share
4. Accuracy section — make the numbers more compelling

Respond with JSON:
{{
  "sections": [
    {{
      "section_name": "hero_headline",
      "proposed_content": "...full markdown...",
      "rationale": "Why this change increases stars"
    }},
    ...
  ]
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_README,
        messages=[{"role": "user", "content": prompt}]
    )

    result = {
        "platform": "readme",
        "sections": [],
        "target_repo": target_repo,
        "generated_at": datetime.utcnow().isoformat(),
    }
    for block in response.content:
        if block.type == "text":
            json_match = re.search(r'\{[\s\S]*\}', block.text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    result.update(parsed)
                except Exception:
                    pass
            break

    result["platform"] = "readme"
    return result


# ------------------------------------------------------------------ #
# Main orchestrator
# ------------------------------------------------------------------ #

def run_scribe(
    plan: Optional[Dict] = None,
    save: bool = True,
    target_repo: str = TARGET_REPO,
) -> Dict[str, Dict]:
    """
    Generate all 5 content pieces in parallel using ThreadPoolExecutor.

    Returns dict mapping platform -> content dict.
    Failed platforms return {"platform": name, "error": "..."}.
    """
    load_dotenv(Path(__file__).parent.parent / ".env")

    if plan is None:
        plan = load_improvement_plan()

    log.info("=" * 60)
    log.info("[Scribe] STARTING PARALLEL CONTENT GENERATION")
    log.info(f"[Scribe] Target: https://github.com/{target_repo}")
    log.info(f"[Scribe] Theme: {plan.get('campaign_theme', 'N/A')}")
    log.info("=" * 60)

    generators = {
        "twitter":  lambda: generate_twitter_thread(plan, target_repo),
        "reddit":   lambda: generate_reddit_post(plan, target_repo),
        "show_hn":  lambda: generate_show_hn(plan, target_repo),
        "linkedin": lambda: generate_linkedin_post(plan, target_repo),
        "readme":   lambda: generate_readme_proposal(plan, target_repo),
    }

    results = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): name for name, fn in generators.items()}
        for future in as_completed(futures, timeout=300):
            name = futures[future]
            try:
                result = future.result()
                results[name] = result
                log.info(f"[Scribe] {name.upper()} ✓ generated")
            except Exception as e:
                log.error(f"[Scribe] {name} generation failed: {e}")
                results[name] = {"platform": name, "error": str(e)}

    if save:
        for platform, content in results.items():
            out_path = CONTENT_DIR / f"{platform}.json"
            with open(out_path, 'w') as f:
                json.dump(content, f, indent=2)
            log.info(f"[Scribe] Saved: {out_path}")

    log.info("=" * 60)
    log.info("[Scribe] CONTENT GENERATION COMPLETE")
    log.info(f"[Scribe] Generated: {', '.join(k for k,v in results.items() if 'error' not in v)}")
    failed = [k for k,v in results.items() if 'error' in v]
    if failed:
        log.warning(f"[Scribe] Failed: {', '.join(failed)}")
    log.info("=" * 60)

    # Log cost
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.cost_tracker import log_pipeline_run
        log_pipeline_run(approved=True)
    except Exception:
        pass

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )

    results = run_scribe()

    print("\n" + "=" * 60)
    print("SCRIBE COMPLETE")
    print("=" * 60)

    if "twitter" in results and "tweets" in results["twitter"]:
        tweets = results["twitter"]["tweets"]
        print(f"\nTwitter thread ({len(tweets)} tweets):")
        print(f"  Tweet 1: {tweets[0][:120]}...")

    if "show_hn" in results:
        print(f"\nShow HN title: {results['show_hn'].get('title', 'N/A')}")

    if "reddit" in results:
        print(f"\nReddit title: {results['reddit'].get('title', 'N/A')}")

    print(f"\nAll content saved to: {CONTENT_DIR}")
