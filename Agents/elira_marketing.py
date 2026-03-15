"""
Elira (Marketing) — Marketing Orchestrator

Coordinates all marketing agents, manages campaign state,
generates terminal preview, and gates approval before any publish.

State file: data/state.json
Preview: ANSI terminal output (no rich library needed)
Approval gate: input("Approve? (y/n): ")

Sixth and final agent in the marketing pipeline.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

log = logging.getLogger("elira_marketing")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "state.json"
CONTENT_DIR = DATA_DIR / "content"
MEDIA_DIR = DATA_DIR / "media"

TARGET_REPO = "jellyforex/askelira"
TARGET_URL = f"https://github.com/{TARGET_REPO}"

# Pipeline phases in order
PHASES = [
    "github_scout",
    "trend_analyzer",
    "scribe",
    "lens",
    "pixel",
]

# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ------------------------------------------------------------------ #
# State management
# ------------------------------------------------------------------ #

def _empty_state() -> Dict:
    """Return a fresh state skeleton."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "campaign_id": f"{today}-001",
        "target_repo": TARGET_REPO,
        "started_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
        "phases": {p: {"status": "pending"} for p in PHASES},
        "approved": False,
        "approval_timestamp": None,
    }


def load_state() -> Dict:
    """Load data/state.json. Returns empty state if missing or corrupt."""
    if not STATE_FILE.exists():
        return _empty_state()
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        # Corrupt state — back it up and start fresh
        STATE_FILE.rename(STATE_FILE.with_suffix(".json.bak"))
        log.warning("[Elira] state.json corrupted — starting fresh")
        return _empty_state()


def save_state(state: Dict) -> None:
    """Write state dict to data/state.json."""
    state["last_updated"] = datetime.utcnow().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def mark_phase_complete(phase: str, output_files: Optional[List[str]] = None) -> None:
    """Update state to mark a phase as complete."""
    state = load_state()
    state["phases"][phase] = {
        "status": "complete",
        "completed_at": datetime.utcnow().isoformat(),
        "output_files": output_files or [],
    }
    save_state(state)
    log.info(f"[Elira] Phase '{phase}' marked complete")


def mark_phase_failed(phase: str, error: str) -> None:
    """Update state to mark a phase as failed."""
    state = load_state()
    state["phases"][phase] = {
        "status": "failed",
        "failed_at": datetime.utcnow().isoformat(),
        "error": error[:500],
    }
    save_state(state)
    log.error(f"[Elira] Phase '{phase}' failed: {error[:100]}")


def get_resume_phase(state: Dict) -> Optional[str]:
    """Return first incomplete phase, or None if all complete."""
    for phase in PHASES:
        status = state["phases"].get(phase, {}).get("status", "pending")
        if status != "complete":
            return phase
    return None


# ------------------------------------------------------------------ #
# Phase runner
# ------------------------------------------------------------------ #

def run_phase(
    phase_name: str,
    dry_run: bool = False,
    skip_mirofish: bool = False,
    topics: Optional[List[str]] = None,
    target_repo: str = TARGET_REPO,
) -> Dict:
    """
    Execute a single pipeline phase.
    In dry_run mode: skips API calls and returns mock data.
    """
    if dry_run:
        log.info(f"[Elira] DRY RUN — skipping actual {phase_name} API calls")
        return {"phase": phase_name, "dry_run": True, "status": "ok"}

    # Add parent to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    if phase_name == "github_scout":
        from Agents.github_scout import run_scout
        result = run_scout(
            topics=topics or ["ai-agents", "machine-learning", "autonomous-ai"],
            min_stars=500,
            save=True,
        )
        return result

    elif phase_name == "trend_analyzer":
        from Agents.trend_analyzer import run_analyzer
        result = run_analyzer(use_mirofish=not skip_mirofish, save=True)
        return result

    elif phase_name == "scribe":
        from Agents.scribe import run_scribe
        result = run_scribe(save=True, target_repo=target_repo)
        return result

    elif phase_name == "lens":
        from Agents.lens import run_lens
        result = run_lens(save=True)
        return result

    elif phase_name == "pixel":
        from Agents.pixel import run_pixel
        result = run_pixel(save=True)
        return result

    else:
        raise ValueError(f"Unknown phase: {phase_name}")


# ------------------------------------------------------------------ #
# Terminal preview
# ------------------------------------------------------------------ #

def build_terminal_preview(state: Dict) -> str:
    """Build a rich ANSI terminal preview of the campaign."""
    lines = []

    def add(text: str = ""):
        lines.append(text)

    width = 70
    add(f"{BOLD}{CYAN}{'=' * width}{RESET}")
    add(f"{BOLD}{CYAN}  ASKELIRA MARKETING — CAMPAIGN PREVIEW{RESET}")
    add(f"{CYAN}{'=' * width}{RESET}")
    add(f"  {WHITE}Target:{RESET}     {CYAN}{TARGET_URL}{RESET}")
    add(f"  {WHITE}Campaign ID:{RESET} {state.get('campaign_id', 'N/A')}")
    add(f"  {WHITE}Goal:{RESET}        100+ GitHub stars in week 1 | GitHub trending")
    add(f"{GRAY}{'─' * width}{RESET}")

    # Phase status
    add(f"\n  {BOLD}PIPELINE STATUS{RESET}")
    for phase in PHASES:
        p_state = state["phases"].get(phase, {})
        status = p_state.get("status", "pending")
        if status == "complete":
            icon = f"{GREEN}✓{RESET}"
        elif status == "failed":
            icon = f"{RED}✗{RESET}"
        else:
            icon = f"{YELLOW}○{RESET}"
        add(f"    {icon} {phase.replace('_', ' ').title()}")

    add()

    # Improvement plan
    plan_file = DATA_DIR / "improvement_plan.json"
    if plan_file.exists():
        try:
            with open(plan_file) as f:
                plan = json.load(f)
            add(f"{GRAY}{'─' * width}{RESET}")
            add(f"\n  {BOLD}MIROFISH CONFIDENCE SCORES{RESET}")
            add(f"  Theme: {CYAN}{plan.get('campaign_theme', 'N/A')}{RESET}")
            add()
            for t in plan.get("tactics", [])[:5]:
                conf = t.get("confidence", 0)
                color = GREEN if conf >= 70 else YELLOW if conf >= 50 else RED
                stable = "" if t.get("stable", True) else f" {YELLOW}[unstable]{RESET}"
                add(f"  {color}{conf:3d}%{RESET}{stable}  {t.get('name', '')[:60]}")
        except Exception:
            pass

    # Content preview
    twitter_file = CONTENT_DIR / "twitter.json"
    show_hn_file = CONTENT_DIR / "show_hn.json"
    reddit_file = CONTENT_DIR / "reddit.json"

    if any(f.exists() for f in [twitter_file, show_hn_file, reddit_file]):
        add()
        add(f"{GRAY}{'─' * width}{RESET}")
        add(f"\n  {BOLD}CONTENT PREVIEW{RESET}")

        if twitter_file.exists():
            try:
                with open(twitter_file) as f:
                    tweets = json.load(f).get("tweets", [])
                if tweets:
                    add(f"  {WHITE}Twitter (tweet 1/12):{RESET}")
                    add(f"  {GRAY}{tweets[0][:100]}...{RESET}")
            except Exception:
                pass

        if show_hn_file.exists():
            try:
                with open(show_hn_file) as f:
                    hn = json.load(f)
                add(f"  {WHITE}Show HN:{RESET} {hn.get('title', 'N/A')[:80]}")
            except Exception:
                pass

        if reddit_file.exists():
            try:
                with open(reddit_file) as f:
                    reddit = json.load(f)
                add(f"  {WHITE}Reddit:{RESET}  {reddit.get('title', 'N/A')[:80]}")
            except Exception:
                pass

    # Media status
    poster_exists = (MEDIA_DIR / "poster.png").exists()
    video_exists = (MEDIA_DIR / "demo.mp4").exists()
    diff_exists = (DATA_DIR / "readme_diff.md").exists()

    add()
    add(f"{GRAY}{'─' * width}{RESET}")
    add(f"\n  {BOLD}ASSETS{RESET}")
    add(f"  Poster:      {'✓' if poster_exists else '✗ not generated'}")
    add(f"  Demo video:  {'✓' if video_exists else '✗ not generated'}")
    add(f"  README diff: {'✓ data/readme_diff.md' if diff_exists else '✗ not generated'}")

    # Cost summary
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.cost_tracker import get_roi_summary
        roi = get_roi_summary()
        add()
        add(f"{GRAY}{'─' * width}{RESET}")
        add(f"\n  {BOLD}COST SUMMARY{RESET}")
        add(f"  Total API cost: ${roi['total_cost']:.4f}")
        add(f"  Pipeline runs:  {roi['run_count']}")
    except Exception:
        pass

    add()
    add(f"{CYAN}{'=' * width}{RESET}")
    add()

    return "\n".join(lines)


def approval_gate(preview: str) -> bool:
    """Print preview and prompt for approval. Returns True if approved."""
    print(preview)
    print(f"{BOLD}Campaign ready for review.{RESET}")
    print(f"Content will NOT be published automatically.")
    print(f"Review data/content/ and data/readme_diff.md for full details.\n")

    try:
        answer = input(f"{BOLD}Approve this campaign? (y/n): {RESET}").strip().lower()
        return answer in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print(f"\n{YELLOW}Campaign approval cancelled.{RESET}")
        return False


# ------------------------------------------------------------------ #
# Main orchestrator
# ------------------------------------------------------------------ #

def run_elira(
    dry_run: bool = False,
    skip_mirofish: bool = False,
    resume: bool = True,
    topics: Optional[List[str]] = None,
    target_repo: str = TARGET_REPO,
) -> bool:
    """
    Main marketing orchestrator.
    Runs all phases, shows preview, gates approval.
    Returns True if campaign was approved.
    """
    load_dotenv(Path(__file__).parent.parent / ".env")

    log.info("=" * 60)
    log.info("[Elira Marketing] STARTING CAMPAIGN ORCHESTRATION")
    log.info(f"[Elira Marketing] Target: {TARGET_URL}")
    log.info(f"[Elira Marketing] Dry run: {dry_run} | Skip MiroFish: {skip_mirofish}")
    log.info("=" * 60)

    state = load_state() if resume else _empty_state()

    start_phase = get_resume_phase(state) if resume else PHASES[0]

    if start_phase is None:
        log.info("[Elira Marketing] All phases already complete — showing preview")
    else:
        start_idx = PHASES.index(start_phase)
        for phase in PHASES[start_idx:]:
            log.info(f"\n[Elira Marketing] Running phase: {phase}")
            try:
                run_phase(
                    phase,
                    dry_run=dry_run,
                    skip_mirofish=skip_mirofish,
                    topics=topics,
                    target_repo=target_repo,
                )
                mark_phase_complete(phase)
            except Exception as e:
                mark_phase_failed(phase, str(e))
                log.error(f"[Elira Marketing] Phase '{phase}' failed: {e}")
                raise

    # Show preview and approval gate
    state = load_state()
    preview = build_terminal_preview(state)
    approved = approval_gate(preview)

    # Update state
    state = load_state()
    state["approved"] = approved
    state["approval_timestamp"] = datetime.utcnow().isoformat()
    save_state(state)

    if approved:
        log.info("[Elira Marketing] Campaign APPROVED")
        print(f"\n{GREEN}{BOLD}✓ Campaign approved!{RESET}")
        print(f"Next steps:")
        print(f"  1. Review {CONTENT_DIR}/twitter.json — post thread manually")
        print(f"  2. Review {CONTENT_DIR}/show_hn.json — submit to news.ycombinator.com/submit")
        print(f"  3. Review {CONTENT_DIR}/reddit.json — post to r/MachineLearning")
        print(f"  4. Review {DATA_DIR}/readme_diff.md — apply README improvements")
        print(f"\nAll content targets: {TARGET_URL}")
    else:
        log.info("[Elira Marketing] Campaign REJECTED")
        print(f"\n{YELLOW}Campaign not approved.{RESET}")
        print("Edit content in data/content/ and re-run when ready.")

    return approved


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )

    parser = argparse.ArgumentParser(description="Elira Marketing Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls")
    parser.add_argument("--skip-mirofish", action="store_true", help="Claude fallback")
    parser.add_argument("--fresh", action="store_true", help="Ignore state.json")
    parser.add_argument("--preview-only", action="store_true", help="Just show preview, no approval gate")
    args = parser.parse_args()

    if args.preview_only:
        state = load_state()
        print(build_terminal_preview(state))
    else:
        run_elira(
            dry_run=args.dry_run,
            skip_mirofish=args.skip_mirofish,
            resume=not args.fresh,
        )
