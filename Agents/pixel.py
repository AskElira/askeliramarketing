"""
Pixel — Interface Manager

Reads README.md and generates improved sections for viral GitHub appeal.
Creates a unified diff preview (data/readme_diff.md).
Does NOT write directly to README.md — preview only.

Target: github.com/jellyforex/askelira

Fifth agent in the marketing pipeline.
"""

import difflib
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anthropic
from dotenv import load_dotenv

log = logging.getLogger("pixel")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

README_PATH = Path(__file__).parent.parent / "README.md"
README_DIFF_FILE = DATA_DIR / "readme_diff.md"
IMPROVEMENT_PLAN_FILE = DATA_DIR / "improvement_plan.json"
CONTENT_DIR = DATA_DIR / "content"

TARGET_REPO = "jellyforex/askelira"
TARGET_URL = f"https://github.com/{TARGET_REPO}"

MODEL = "claude-sonnet-4-5"


def load_readme(path: Path = README_PATH) -> str:
    """Read README.md as a string."""
    if not path.exists():
        raise FileNotFoundError(f"README.md not found at {path}")
    with open(path) as f:
        return f.read()


def load_improvement_plan() -> Dict:
    """Load improvement_plan.json. Returns minimal fallback if missing."""
    if IMPROVEMENT_PLAN_FILE.exists():
        with open(IMPROVEMENT_PLAN_FILE) as f:
            return json.load(f)
    return {
        "campaign_theme": "AskElira: 5 AI agents + MiroFish swarm predict binary outcomes",
        "top_tactic": "Add demo video",
        "tactics": [],
        "target_repo": TARGET_REPO,
    }


def load_content_files() -> Dict:
    """Load content JSONs from data/content/. Non-fatal if empty."""
    content = {}
    if not CONTENT_DIR.exists():
        return content
    for json_file in CONTENT_DIR.glob("*.json"):
        try:
            with open(json_file) as f:
                content[json_file.stem] = json.load(f)
        except Exception:
            pass
    return content


def parse_readme_sections(readme: str) -> Dict[str, str]:
    """
    Parse README into sections by splitting on ## headers.
    Returns dict: {section_name: section_content}.
    """
    sections = {}

    # Split on ## headers (preserve the first section before any ##)
    parts = re.split(r'\n(?=## )', readme)

    for i, part in enumerate(parts):
        if i == 0 and not part.startswith('## '):
            sections['__hero__'] = part
        else:
            lines = part.split('\n', 1)
            header = lines[0].strip().lstrip('#').strip()
            body = lines[1] if len(lines) > 1 else ""
            sections[header] = f"{lines[0]}\n{body}"

    return sections


def generate_hero_section(
    readme: str,
    plan: Dict,
    client: anthropic.Anthropic,
) -> Tuple[str, str]:
    """
    Generate improved hero headline + tagline.
    Returns (section_name, improved_content).
    """
    current_hero = readme[:800]  # First 800 chars

    prompt = f"""Improve the GitHub README hero section for AskElira to maximize GitHub stars.

Current opening:
{current_hero}

Campaign theme: {plan.get('campaign_theme', '')}
Target: {TARGET_URL}

Requirements:
- Keep the H1 title "AskElira" or similar
- Add a punchy tagline that makes developers want to star immediately
- Mention "5 AI agents", "MiroFish swarm", "binary predictions"
- Add GitHub badges (stars, license, Python) placeholder text
- Keep it under 10 lines
- No generic hype — be specific about what it does

Output ONLY the improved markdown content (no JSON wrapper, no explanation)."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    return "hero_headline", response.content[0].text.strip()


def generate_demo_section(
    readme: str,
    plan: Dict,
    content: Dict,
    client: anthropic.Anthropic,
) -> Tuple[str, str]:
    """
    Generate improved demo / quick start section.
    Returns (section_name, improved_content).
    """
    show_hn_title = ""
    if "show_hn" in content:
        show_hn_title = content["show_hn"].get("title", "")

    prompt = f"""Improve the Demo / Quick Start section of the AskElira README.

Campaign theme: {plan.get('campaign_theme', '')}
Show HN title: {show_hn_title}
GitHub: {TARGET_URL}

Requirements:
1. Add a "## Demo" section at the top with a placeholder for demo video:
   > 📺 [60-second demo video coming soon]
   > Watch AskElira predict a real binary market question using swarm intelligence
2. Keep the Quick Start but improve to ≤3 commands
3. Add a "## What It Predicts" section with real examples
4. Include the Show HN title as a callout if it exists

Output ONLY the improved markdown (## Demo section through ## Quick Start), no JSON, no explanation."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )

    return "demo_section", response.content[0].text.strip()


def generate_cta_section(
    plan: Dict,
    content: Dict,
    client: anthropic.Anthropic,
) -> Tuple[str, str]:
    """
    Generate a call-to-action section.
    Returns (section_name, improved_content).
    """
    twitter_tweet = ""
    if "twitter" in content and "tweets" in content["twitter"]:
        tweets = content["twitter"]["tweets"]
        if tweets:
            twitter_tweet = tweets[0]

    prompt = f"""Write a "## Contributing & Star This Repo" section for AskElira's README.

Campaign theme: {plan.get('campaign_theme', '')}
GitHub: {TARGET_URL}
Top tactic: {plan.get('top_tactic', '')}

Requirements:
- Ask for a GitHub star (but not desperately — be direct)
- Show HN link placeholder: [Show HN submission]
- Reddit links: r/MachineLearning, r/algotrading
- Discord/community placeholder
- How to contribute (fork, PR)
- "Built with" credits: Anthropic, MiroFish

Output ONLY the markdown section, no JSON, no explanation."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return "cta_section", response.content[0].text.strip()


def build_diff(original: str, improved: str) -> str:
    """Generate unified diff between original and improved README."""
    original_lines = original.splitlines(keepends=True)
    improved_lines = improved.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        original_lines,
        improved_lines,
        fromfile="README.md (current)",
        tofile="README.md (proposed)",
        lineterm="",
    ))

    return "".join(diff_lines)


def run_pixel(
    plan: Optional[Dict] = None,
    save: bool = True,
) -> Dict:
    """
    Main pipeline:
    1. Load README.md
    2. Load improvement_plan.json
    3. Load content/ files
    4. Generate hero, demo, CTA sections in parallel
    5. Splice improved sections into README
    6. Generate diff
    7. Save to data/readme_diff.md
    """
    load_dotenv(Path(__file__).parent.parent / ".env")

    if plan is None:
        plan = load_improvement_plan()

    readme = load_readme()
    content = load_content_files()

    log.info("=" * 60)
    log.info("[Pixel] STARTING README ANALYSIS")
    log.info(f"[Pixel] README: {len(readme)} chars")
    log.info("=" * 60)

    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Generate 3 section improvements in parallel
    generators = {
        "hero":  lambda: generate_hero_section(readme, plan, anthropic_client),
        "demo":  lambda: generate_demo_section(readme, plan, content, anthropic_client),
        "cta":   lambda: generate_cta_section(plan, content, anthropic_client),
    }

    section_results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in generators.items()}
        for future in as_completed(futures, timeout=120):
            name = futures[future]
            try:
                section_name, content_text = future.result()
                section_results[section_name] = content_text
                log.info(f"[Pixel] Section '{name}' ✓ generated ({len(content_text)} chars)")
            except Exception as e:
                log.error(f"[Pixel] Section '{name}' failed: {e}")

    # Splice improved sections into README
    improved_readme = readme
    sections_improved = []

    if "hero_headline" in section_results:
        # Replace first section (before first ##)
        first_h2_idx = improved_readme.find('\n## ')
        if first_h2_idx > 0:
            improved_readme = section_results["hero_headline"] + "\n\n" + improved_readme[first_h2_idx:].lstrip('\n')
        sections_improved.append("hero_headline")

    if "demo_section" in section_results:
        # Insert demo section after hero, before first ## section
        first_h2_idx = improved_readme.find('\n## ')
        if first_h2_idx > 0:
            improved_readme = (
                improved_readme[:first_h2_idx] +
                "\n\n" + section_results["demo_section"] +
                "\n" + improved_readme[first_h2_idx:]
            )
        sections_improved.append("demo_section")

    if "cta_section" in section_results:
        # Append CTA at end
        improved_readme = improved_readme.rstrip() + "\n\n" + section_results["cta_section"] + "\n"
        sections_improved.append("cta_section")

    # Generate diff
    diff = build_diff(readme, improved_readme)
    char_delta = len(improved_readme) - len(readme)

    result = {
        "diff": diff,
        "sections_improved": sections_improved,
        "char_delta": char_delta,
        "original_chars": len(readme),
        "improved_chars": len(improved_readme),
        "saved_to": str(README_DIFF_FILE),
        "generated_at": datetime.utcnow().isoformat(),
    }

    if save:
        with open(README_DIFF_FILE, 'w') as f:
            f.write(f"# README Improvement Diff\n")
            f.write(f"# Generated: {result['generated_at']}\n")
            f.write(f"# Target: {TARGET_URL}\n")
            f.write(f"# Sections improved: {', '.join(sections_improved)}\n")
            f.write(f"# Character delta: +{char_delta}\n\n")
            f.write("## Unified Diff\n\n```diff\n")
            f.write(diff)
            f.write("\n```\n\n")
            f.write("## Improved README Preview\n\n")
            f.write(improved_readme)
        log.info(f"[Pixel] Diff saved: {README_DIFF_FILE}")

    log.info("=" * 60)
    log.info("[Pixel] README ANALYSIS COMPLETE")
    log.info(f"[Pixel] Sections improved: {', '.join(sections_improved)}")
    log.info(f"[Pixel] Character delta: +{char_delta}")
    log.info("=" * 60)

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )

    result = run_pixel()

    print("\n" + "=" * 60)
    print("PIXEL COMPLETE")
    print("=" * 60)
    print(f"\nSections improved: {', '.join(result['sections_improved'])}")
    print(f"Character delta:   +{result['char_delta']}")
    print(f"Diff saved to:     {result['saved_to']}")
    print(f"\nFirst 10 lines of diff:")
    for line in result['diff'].split('\n')[:10]:
        print(f"  {line}")
