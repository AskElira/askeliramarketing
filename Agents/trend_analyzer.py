"""
Trend Analyzer — MiroFish Confidence Engine

Reads success patterns from Alba (github_scout.py) and scores each tactic.
Question: "Will [tactic] increase github.com/jellyforex/askelira GitHub stars?"

Simulates with 1000 agents (developers, HN users, founders, OSS maintainers).
MiroFish fallback: uses Claude sonnet to estimate confidence.

Second agent in the marketing pipeline.
"""

import json
import logging
import os
import re
import sys
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anthropic
from dotenv import load_dotenv

# Add parent dir to path for mirofish_client import
sys.path.insert(0, str(Path(__file__).parent.parent))

log = logging.getLogger("trend_analyzer")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEEDS_DIR = DATA_DIR / "seeds"
SEEDS_DIR.mkdir(parents=True, exist_ok=True)

SUCCESS_PATTERNS_FILE = DATA_DIR / "success_patterns.json"
IMPROVEMENT_PLAN_FILE = DATA_DIR / "improvement_plan.json"

TARGET_REPO = "jellyforex/askelira"
TARGET_URL = f"https://github.com/{TARGET_REPO}"

MODEL = "claude-sonnet-4-5"
MIROFISH_URL = os.getenv("MIROFISH_URL", "http://localhost:5001")
MIN_RUNS = 3
VARIANCE_THRESHOLD = 0.15

ASKELIRA_CONTEXT = f"""
AskElira is an open-source multi-agent prediction system at {TARGET_URL}
It uses 5 AI agents (Alba, David, Vex, Elira, Steven) + MiroFish swarm intelligence
to predict binary YES/NO outcomes on prediction markets (Polymarket, Kalshi).

Key facts:
- MiroFish runs 1000+ AI agents in parallel to simulate crowd behavior
- Predicts: politics, economics, sports, crypto, world events
- ~$0.015 per prediction, open source (MIT)
- Currently ~0 GitHub stars (just launched)
- Goal: 100+ stars in week 1, GitHub trending

Audience: Python developers, ML engineers, algorithmic traders, prediction market enthusiasts
"""


def load_success_patterns(path: Path = SUCCESS_PATTERNS_FILE) -> Dict:
    """Load success_patterns.json from github_scout.py."""
    if not path.exists():
        raise FileNotFoundError(
            f"success_patterns.json not found at {path}\n"
            "Run Phase 1 first: python -m Agents.github_scout"
        )
    with open(path) as f:
        return json.load(f)


def build_tactic_seed(tactic: str, patterns: Dict) -> Path:
    """
    Write a MiroFish-compatible .txt seed file for a single tactic.
    Returns path to the seed file.
    """
    seed_content = f"""# Marketing Tactic Analysis Seed

## Target Repository
Name: AskElira
URL: {TARGET_URL}
Description: Multi-agent binary prediction system using MiroFish swarm intelligence
Current Stars: ~0 (just launched, March 2026)
Target: 100+ GitHub stars in week 1

## Tactic Being Evaluated
"{tactic}"

## AskElira Context
{ASKELIRA_CONTEXT}

## Market Research Context
From analysis of {patterns.get('analyzed_repos', 'N/A')} successful AI repositories:
- Demo video adoption rate: {patterns.get('demo_percentage', 0)*100:.0f}% of trending repos have demo videos
- Average install steps: {patterns.get('avg_install_steps', 5):.1f} commands
- Show HN success rate: {patterns.get('show_hn_success_rate', 0)*100:.0f}% launched on Hacker News

## Common Tactics from Successful Repos
{chr(10).join(f"- {t}" for t in patterns.get('common_tactics', [])[:10])}

## Agent Population for Simulation
Simulate responses from these groups (total ~1000 agents):
- 40% Python/AI developers (GitHub power users, follow trending repos)
- 30% Hacker News community (technical, critical, hate hype, love demos)
- 20% Startup founders (busy, want ROI proof, care about accuracy metrics)
- 10% Open source maintainers (value code quality, documentation, MIT license)

## Simulation Question
Will the tactic "{tactic}" significantly increase GitHub stars for {TARGET_URL}?
Specifically: Does this tactic make developers/HN users more likely to star the repo?
"""

    # Sanitize tactic name for filename
    safe_name = re.sub(r'[^a-z0-9]+', '_', tactic.lower())[:40]
    seed_path = SEEDS_DIR / f"tactic_{safe_name}.txt"

    with open(seed_path, 'w') as f:
        f.write(seed_content)

    log.info(f"[TrendAnalyzer] Seed written: {seed_path.name}")
    return seed_path


def score_tactic_with_mirofish(
    tactic: str,
    seed_path: Path,
    runs: int = MIN_RUNS,
    variance_threshold: float = VARIANCE_THRESHOLD,
) -> Tuple[float, str, bool, List[float]]:
    """
    Run MiroFish simulations for a tactic.

    Returns:
        (avg_confidence: float 0-1, rationale: str, stable: bool, run_scores: list)
    """
    try:
        from mirofish_client import MiroFishClient, MiroFishError, _extract_sim_result
    except ImportError:
        log.warning("[TrendAnalyzer] mirofish_client not importable, using Claude fallback")
        raise

    client = MiroFishClient(base_url=MIROFISH_URL)
    simulation_requirement = (
        f"Predict whether the marketing tactic '{tactic}' will increase GitHub stars "
        f"for the AskElira open-source project ({TARGET_URL}) within 30 days. "
        "Focus on developer community behavior and viral adoption patterns."
    )
    project_name = f"askelira-marketing-tactic-{re.sub(r'[^a-z0-9]+', '-', tactic.lower())[:25]}"

    run_confidences = []
    last_markdown = ""

    for i in range(runs):
        log.info(f"[TrendAnalyzer] MiroFish run {i+1}/{runs} for: {tactic[:50]}")
        try:
            _, _, markdown = client.full_run(seed_path, simulation_requirement, project_name)
            confidence, direction = _extract_sim_result(markdown)
            # For marketing: YES direction = tactic will work
            if direction == "NO":
                confidence = 1.0 - confidence
            run_confidences.append(confidence)
            last_markdown = markdown
        except Exception as e:
            log.warning(f"[TrendAnalyzer] MiroFish run {i+1} failed: {e}")

    if not run_confidences:
        return 0.0, "All MiroFish runs failed", False, []

    avg_conf = statistics.mean(run_confidences)

    # Variance check
    stable = True
    if len(run_confidences) > 1:
        variance = statistics.stdev(run_confidences)
        stable = variance <= variance_threshold
        if not stable:
            log.warning(f"[TrendAnalyzer] High variance ({variance:.2f}) for: {tactic[:50]}")

    # Extract rationale from last report
    rationale = _extract_rationale(last_markdown, tactic)

    return avg_conf, rationale, stable, run_confidences


def _extract_rationale(markdown: str, tactic: str) -> str:
    """Extract a short rationale string from MiroFish report markdown."""
    if not markdown:
        return f"MiroFish simulation completed for tactic: {tactic}"

    # Try to find a summary section
    lines = markdown.split('\n')
    for i, line in enumerate(lines):
        if any(kw in line.upper() for kw in ['SUMMARY', 'CONCLUSION', 'RESULT', 'FINDING']):
            # Return next 2 non-empty lines as rationale
            snippets = []
            for l in lines[i+1:i+5]:
                l = l.strip().lstrip('#').strip()
                if l and not l.startswith('|'):
                    snippets.append(l)
                if len(snippets) >= 2:
                    break
            if snippets:
                return ' '.join(snippets)[:300]

    # Fallback: first 200 chars of non-header content
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and len(line) > 30:
            return line[:300]

    return f"Simulation analysis completed for: {tactic}"


def score_tactic_with_claude(
    tactic: str,
    patterns: Dict,
    anthropic_client: anthropic.Anthropic,
) -> Tuple[float, str]:
    """
    MiroFish fallback: use Claude to estimate confidence.
    Returns (confidence: float 0-1, rationale: str)
    """
    log.info(f"[TrendAnalyzer] Claude fallback scoring: {tactic[:60]}")

    prompt = f"""You are analyzing viral growth tactics for an open-source AI project.

Target: AskElira ({TARGET_URL})
Description: {ASKELIRA_CONTEXT}

Tactic to evaluate: "{tactic}"

Market research from {patterns.get('analyzed_repos', 'N/A')} successful AI repos:
- {patterns.get('demo_percentage', 0)*100:.0f}% have demo videos
- Avg {patterns.get('avg_install_steps', 5):.1f} install steps
- {patterns.get('show_hn_success_rate', 0)*100:.0f}% launched on Show HN

Simulate how ~1000 developers, HN users, founders, and OSS contributors would respond.
Would this tactic meaningfully increase GitHub stars in 30 days?

Respond with JSON only:
{{
  "confidence": 75,
  "rationale": "One or two sentences explaining why this confidence score makes sense for this specific project and audience.",
  "key_driver": "The single most important reason this will/won't work"
}}"""

    try:
        response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        for block in response.content:
            if block.type == "text":
                json_match = re.search(r'\{[\s\S]*\}', block.text)
                if json_match:
                    result = json.loads(json_match.group())
                    confidence = min(max(float(result.get("confidence", 50)) / 100, 0.0), 1.0)
                    rationale = result.get("rationale", "") + " " + result.get("key_driver", "")
                    return confidence, rationale.strip()

        log.warning("[TrendAnalyzer] Claude response had no JSON, using default")
        return 0.5, f"Claude analysis inconclusive for: {tactic}"

    except Exception as e:
        log.error(f"[TrendAnalyzer] Claude scoring failed: {e}")
        return 0.5, f"Scoring failed: {e}"


def score_all_tactics(
    patterns: Dict,
    use_mirofish: bool = True,
    anthropic_client: Optional[anthropic.Anthropic] = None,
) -> List[Dict]:
    """
    Score every tactic from success_patterns recommendations + common_tactics.
    Returns list sorted by confidence descending.
    """
    if anthropic_client is None:
        anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Collect tactics to score
    tactics_to_score = list(patterns.get("recommendations", []))

    # Add common tactics not already in recommendations
    for ct in patterns.get("common_tactics", [])[:5]:
        if ct not in tactics_to_score:
            tactics_to_score.append(ct)

    # Fallback: default tactics if patterns are empty
    if not tactics_to_score:
        tactics_to_score = [
            "Add a 60-second demo video showing AskElira predicting a real market question",
            "Launch on Show HN: Show HN: AskElira – 5 AI agents + MiroFish swarm predict binary outcomes",
            "Simplify installation to 3 commands or fewer",
            "Add badges (stars, license, Python version) to README hero section",
            "Post to r/MachineLearning with real accuracy benchmarks",
        ]

    log.info(f"[TrendAnalyzer] Scoring {len(tactics_to_score)} tactics")

    # Check MiroFish availability
    mirofish_available = False
    if use_mirofish:
        try:
            from mirofish_client import MiroFishClient
            client = MiroFishClient(base_url=MIROFISH_URL)
            mirofish_available = client.ping()
            if mirofish_available:
                log.info("[TrendAnalyzer] MiroFish is reachable — using simulations")
            else:
                log.warning("[TrendAnalyzer] MiroFish unreachable — falling back to Claude")
        except ImportError:
            log.warning("[TrendAnalyzer] mirofish_client not available — using Claude fallback")

    scored = []

    for tactic in tactics_to_score:
        log.info(f"[TrendAnalyzer] Scoring: {tactic[:60]}...")

        if mirofish_available:
            seed_path = build_tactic_seed(tactic, patterns)
            try:
                confidence, rationale, stable, runs = score_tactic_with_mirofish(
                    tactic, seed_path
                )
            except Exception as e:
                log.warning(f"[TrendAnalyzer] MiroFish failed for tactic, using Claude: {e}")
                confidence, rationale = score_tactic_with_claude(tactic, patterns, anthropic_client)
                stable = True
                runs = []
        else:
            confidence, rationale = score_tactic_with_claude(tactic, patterns, anthropic_client)
            stable = True
            runs = []

        scored.append({
            "name": tactic,
            "confidence": int(confidence * 100),
            "rationale": rationale,
            "stable": stable,
            "runs": [int(r * 100) for r in runs],
        })

        log.info(f"[TrendAnalyzer] Score: {int(confidence * 100)}% — {tactic[:50]}")

    # Sort by confidence descending
    scored.sort(key=lambda x: x["confidence"], reverse=True)

    # Add priority rank
    for i, t in enumerate(scored):
        t["priority"] = i + 1

    return scored


def derive_campaign_theme(
    top_tactics: List[Dict],
    anthropic_client: anthropic.Anthropic,
) -> str:
    """
    Synthesize top 3 tactics into a single campaign theme/headline.
    Returns a short string (max 100 chars).
    """
    top3 = top_tactics[:3]
    tactics_text = "\n".join(f"- {t['name']} (confidence: {t['confidence']}%)" for t in top3)

    prompt = f"""Create ONE punchy campaign theme for launching {TARGET_URL} on GitHub.

Top tactics (by confidence):
{tactics_text}

The theme should:
- Be a headline that makes developers want to click
- Emphasize "5 AI agents + MiroFish swarm intelligence"
- Be specific to AskElira (prediction markets, binary outcomes)
- Be ≤80 characters
- NOT be generic hype (no "Revolutionary!" or "Amazing!")

Good examples:
- "Watch 1000 AI agents predict the election in real-time"
- "The swarm that called 3 Fed decisions in a row — open source"
- "5 agents, 1 question, 82% accuracy on prediction markets"

Respond with ONLY the theme string, no quotes, no JSON, no explanation."""

    try:
        response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        theme = response.content[0].text.strip().strip('"').strip("'")
        return theme[:100]
    except Exception as e:
        log.error(f"[TrendAnalyzer] Campaign theme generation failed: {e}")
        return "Watch the swarm think: AskElira live demo"


def build_improvement_plan(scored_tactics: List[Dict], theme: str) -> Dict:
    """Assemble the output dict."""
    return {
        "target_repo": TARGET_REPO,
        "target_url": TARGET_URL,
        "campaign_theme": theme,
        "top_tactic": scored_tactics[0]["name"] if scored_tactics else "",
        "tactics": [
            {
                "name": t["name"],
                "confidence": t["confidence"],
                "rationale": t["rationale"],
                "priority": t["priority"],
                "stable": t["stable"],
            }
            for t in scored_tactics
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def run_analyzer(
    use_mirofish: bool = True,
    save: bool = True,
) -> Dict:
    """
    Main pipeline:
    1. Load success_patterns.json
    2. Score all tactics (MiroFish or Claude fallback)
    3. Derive campaign theme
    4. Build improvement plan
    5. Save to data/improvement_plan.json
    """
    load_dotenv(Path(__file__).parent.parent / ".env")

    log.info("=" * 60)
    log.info("[TrendAnalyzer] STARTING PIPELINE")
    log.info(f"[TrendAnalyzer] Target: {TARGET_URL}")
    log.info("=" * 60)

    patterns = load_success_patterns()
    log.info(f"[TrendAnalyzer] Loaded {len(patterns.get('recommendations', []))} recommendations")

    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    scored = score_all_tactics(patterns, use_mirofish=use_mirofish, anthropic_client=anthropic_client)
    theme = derive_campaign_theme(scored, anthropic_client)
    plan = build_improvement_plan(scored, theme)

    if save:
        with open(IMPROVEMENT_PLAN_FILE, 'w') as f:
            json.dump(plan, f, indent=2)
        log.info(f"[TrendAnalyzer] Saved: {IMPROVEMENT_PLAN_FILE}")

    log.info("=" * 60)
    log.info("[TrendAnalyzer] PIPELINE COMPLETE")
    log.info(f"[TrendAnalyzer] Campaign theme: {theme}")
    log.info(f"[TrendAnalyzer] Top tactic ({scored[0]['confidence']}%): {scored[0]['name'][:60]}")
    log.info("=" * 60)

    # Log cost
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.cost_tracker import log_pipeline_run
        log_pipeline_run(approved=True, sim_confidence=scored[0]["confidence"] / 100 if scored else 0)
    except Exception:
        pass

    return plan


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )

    parser = argparse.ArgumentParser(description="AskElira Trend Analyzer")
    parser.add_argument("--skip-mirofish", action="store_true", help="Use Claude fallback instead of MiroFish")
    args = parser.parse_args()

    plan = run_analyzer(use_mirofish=not args.skip_mirofish)

    print("\n" + "=" * 60)
    print("TREND ANALYZER COMPLETE")
    print("=" * 60)
    print(f"\nTarget: {plan['target_url']}")
    print(f"Campaign theme: {plan['campaign_theme']}")
    print(f"\nTop tactics (by confidence):")
    for t in plan['tactics'][:5]:
        stable_marker = "" if t['stable'] else " [unstable]"
        print(f"  {t['priority']}. [{t['confidence']}%{stable_marker}] {t['name'][:70]}")
    print(f"\nSaved to: {IMPROVEMENT_PLAN_FILE}")
