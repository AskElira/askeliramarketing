"""
campaign.py — AskElira Marketing Entry Point

Viral marketing automation for ANY GitHub repo.
AskElira is the example use case — fork this to market your own project.

Pipeline:
  Phase 1: Alba (github_scout) — scan trending repos for viral tactics
  Phase 2: TrendAnalyzer — score tactics via MiroFish (or Claude fallback)
  Phase 3: Scribe — generate Twitter, Reddit, Show HN, LinkedIn, README content
  Phase 4: Lens — create poster, thumbnail, 60s demo video
  Phase 5: Pixel — generate README diff preview
  Phase 6: Elira Marketing — preview + approval gate

Usage:
  python campaign.py --dry-run
  python campaign.py --phase=2 --skip-mirofish
  python campaign.py --fresh --target=your-username/your-repo
  python campaign.py --verbose
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ------------------------------------------------------------------ #
# Constants
# ------------------------------------------------------------------ #

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TARGET = "jellyforex/askelira"
DEFAULT_TOPICS = "ai-agents,machine-learning,autonomous-ai"

# ------------------------------------------------------------------ #
# Setup
# ------------------------------------------------------------------ #

def setup_logging(verbose: bool = False) -> None:
    """Configure root logger — stdout + data/campaign.log."""
    level = logging.DEBUG if verbose else logging.INFO

    log_format = "%(asctime)s [%(name)s] %(levelname)s %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    try:
        log_file = DATA_DIR / "campaign.log"
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    except Exception:
        pass

    logging.basicConfig(level=level, format=log_format, handlers=handlers)


def validate_environment() -> list:
    """
    Check required environment variables.
    Returns list of critical missing vars.
    Hard fails on ANTHROPIC_API_KEY.
    Warns on optional vars.
    """
    missing_critical = []
    missing_optional = []

    # Critical
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing_critical.append("ANTHROPIC_API_KEY")

    # Important (needed for Phase 1)
    if not os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") == "your_github_token_here":
        missing_optional.append("GITHUB_TOKEN (needed for Phase 1 — create at github.com/settings/tokens)")

    # Optional
    for key in ["OPENAI_API_KEY", "TWITTER_API_KEY", "REDDIT_CLIENT_ID"]:
        if not os.getenv(key):
            missing_optional.append(f"{key} (optional)")

    log = logging.getLogger("campaign")

    if missing_optional:
        log.warning(f"Optional env vars not set: {', '.join(missing_optional)}")

    if missing_critical:
        log.error(f"CRITICAL: Missing required env vars: {', '.join(missing_critical)}")

    return missing_critical


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="ASKELIRA MARKETING — Viral Marketing Automation for Any Repo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python campaign.py --dry-run                     # Safe test (no API calls)
  python campaign.py --phase=1                      # Run only Phase 1 (Alba)
  python campaign.py --phase=2 --skip-mirofish      # Phase 2 with Claude fallback
  python campaign.py --fresh                        # Restart from scratch
  python campaign.py --fresh --target=owner/repo    # Target a different repo
  python campaign.py --verbose                      # Debug logging

Works for any GitHub repo — OSS projects, SaaS products, personal brands, research.
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip all external API calls, use mock/cached data"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        metavar="N",
        help="Run only phase N (1=Alba, 2=TrendAnalyzer, 3=Scribe, 4=Lens, 5=Pixel, 6=Elira)"
    )
    parser.add_argument(
        "--skip-mirofish",
        action="store_true",
        help="Use Claude fallback instead of MiroFish for confidence scoring"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore state.json and restart pipeline from Phase 1"
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        metavar="REPO",
        help=f"Target repo in owner/name format (default: {DEFAULT_TARGET})"
    )
    parser.add_argument(
        "--topics",
        default=DEFAULT_TOPICS,
        help=f"Comma-separated GitHub topics for Phase 1 (default: {DEFAULT_TOPICS})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging"
    )

    return parser


# ------------------------------------------------------------------ #
# Single-phase runner
# ------------------------------------------------------------------ #

def run_single_phase(phase_num: int, args: argparse.Namespace) -> int:
    """Run one phase standalone and exit."""
    log = logging.getLogger("campaign")
    topics = [t.strip() for t in args.topics.split(",")]

    log.info(f"Running single phase: {phase_num}")

    try:
        if phase_num == 1:
            from Agents.github_scout import run_scout
            result = run_scout(topics=topics, min_stars=500, save=True)
            print(f"\nAlba complete: {len(result.get('trending_repos', []))} repos analyzed")
            print(f"Recommendations:")
            for rec in result.get("success_patterns", {}).get("recommendations", []):
                print(f"  • {rec}")

        elif phase_num == 2:
            from Agents.trend_analyzer import run_analyzer
            result = run_analyzer(use_mirofish=not args.skip_mirofish, save=True)
            print(f"\nTrendAnalyzer complete")
            print(f"Campaign theme: {result.get('campaign_theme', 'N/A')}")
            print(f"Top tactic ({result['tactics'][0]['confidence']}%): {result['tactics'][0]['name'][:70]}" if result.get("tactics") else "No tactics scored")

        elif phase_num == 3:
            from Agents.scribe import run_scribe
            results = run_scribe(save=True, target_repo=args.target)
            ok = [k for k,v in results.items() if "error" not in v]
            failed = [k for k,v in results.items() if "error" in v]
            print(f"\nScribe complete: {', '.join(ok)} generated")
            if failed:
                print(f"Failed: {', '.join(failed)}")
            if "twitter" in results and "tweets" in results["twitter"]:
                print(f"\nFirst tweet:")
                print(f"  {results['twitter']['tweets'][0]}")

        elif phase_num == 4:
            from Agents.lens import run_lens
            manifest = run_lens(save=True)
            print(f"\nLens complete (backend: {manifest['backend_used']})")
            print(f"  Poster:    {'✓' if manifest['poster'] else '✗'}")
            print(f"  Thumbnail: {'✓' if manifest['thumbnail'] else '✗'}")
            print(f"  Video:     {'✓' if manifest['demo_video'] else '✗'}")

        elif phase_num == 5:
            from Agents.pixel import run_pixel
            result = run_pixel(save=True)
            print(f"\nPixel complete")
            print(f"  Sections improved: {', '.join(result['sections_improved'])}")
            print(f"  Character delta:   +{result['char_delta']}")
            print(f"  Diff saved to:     {result['saved_to']}")

        elif phase_num == 6:
            from Agents.elira_marketing import run_elira
            approved = run_elira(
                dry_run=args.dry_run,
                skip_mirofish=args.skip_mirofish,
                resume=not args.fresh,
                target_repo=args.target,
            )
            return 0 if approved else 1

        return 0

    except FileNotFoundError as e:
        log.error(f"Missing prerequisite: {e}")
        print(f"\nERROR: {e}")
        return 1
    except Exception as e:
        log.exception(f"Phase {phase_num} failed: {e}")
        return 1


# ------------------------------------------------------------------ #
# Main
# ------------------------------------------------------------------ #

def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Load .env
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Setup logging
    setup_logging(verbose=args.verbose)
    log = logging.getLogger("campaign")

    log.info("=" * 60)
    log.info("ASKELIRA MARKETING — Viral Marketing Automation for Any Repo")
    log.info(f"Target: https://github.com/{args.target}")
    log.info(f"Goal: 100+ GitHub stars in week 1 | GitHub trending")
    log.info("=" * 60)

    # Validate environment
    missing = validate_environment()
    if missing:
        print(f"\nERROR: Missing required environment variables: {', '.join(missing)}")
        print(f"Set them in {env_path}")
        return 1

    # --phase: run single phase and exit
    if args.phase:
        return run_single_phase(args.phase, args)

    # --fresh: clear state
    if args.fresh:
        state_file = DATA_DIR / "state.json"
        if state_file.exists():
            state_file.rename(DATA_DIR / "state.json.bak")
            log.info("Cleared state.json (backed up to state.json.bak)")

    # Full pipeline via Elira orchestrator
    try:
        from Agents.elira_marketing import run_elira
        topics = [t.strip() for t in args.topics.split(",")]

        approved = run_elira(
            dry_run=args.dry_run,
            skip_mirofish=args.skip_mirofish,
            resume=not args.fresh,
            topics=topics,
            target_repo=args.target,
        )

        return 0 if approved else 1

    except KeyboardInterrupt:
        print("\nCampaign interrupted by user.")
        return 0
    except Exception as e:
        log.exception(f"Campaign failed: {e}")
        print(f"\nERROR: {e}")
        print(f"Check data/campaign.log for full details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
