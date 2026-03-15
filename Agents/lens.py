"""
Lens — Media Producer

Generates campaign media for github.com/jellyforex/askelira:
- Campaign poster (1024x1024 PNG)
- YouTube thumbnail (1280x720 PNG)
- 60-second demo video (MP4, 6 slides × 10s)

Backend priority: DALL-E 3 → Replicate → ffmpeg text-on-color (always available)
ffmpeg degrades gracefully: if not on PATH, returns null and continues.

Fourth agent in the marketing pipeline.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

log = logging.getLogger("lens")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR = DATA_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
SLIDES_DIR = MEDIA_DIR / "slides"
SLIDES_DIR.mkdir(parents=True, exist_ok=True)
CONTENT_DIR = DATA_DIR / "content"

IMPROVEMENT_PLAN_FILE = DATA_DIR / "improvement_plan.json"

TARGET_REPO = "jellyforex/askelira"
TARGET_URL = f"https://github.com/{TARGET_REPO}"

# ------------------------------------------------------------------ #
# Backend detection
# ------------------------------------------------------------------ #

def detect_image_backend() -> str:
    """Returns 'openai', 'replicate', or 'ffmpeg'."""
    if os.getenv("OPENAI_API_KEY"):
        log.info("[Lens] Image backend: DALL-E 3 (OPENAI_API_KEY found)")
        return "openai"
    if os.getenv("REPLICATE_API_TOKEN"):
        log.info("[Lens] Image backend: Replicate (REPLICATE_API_TOKEN found)")
        return "replicate"
    if shutil.which("ffmpeg"):
        log.info("[Lens] Image backend: ffmpeg (text-on-color)")
        return "ffmpeg"
    log.warning("[Lens] No image backend available (no ffmpeg, no OPENAI_API_KEY)")
    return "none"


def has_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


# ------------------------------------------------------------------ #
# Poster + thumbnail generation
# ------------------------------------------------------------------ #

def generate_poster_openai(campaign_theme: str, output_path: Path) -> Optional[Path]:
    """Generate campaign poster via DALL-E 3."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = (
            f"Professional GitHub project launch poster for an AI prediction system. "
            f"Dark navy background (#1a1a2e). White and cyan text. "
            f"Title: 'AskElira'. Subtitle: '{campaign_theme}'. "
            f"Visual: abstract network of connected AI agents. "
            f"Bottom text: 'github.com/jellyforex/askelira'. "
            f"Clean, modern, developer aesthetic. No people, no faces."
        )

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        import requests
        image_url = response.data[0].url
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        output_path.write_bytes(img_response.content)
        log.info(f"[Lens] DALL-E poster saved: {output_path}")
        return output_path

    except Exception as e:
        log.warning(f"[Lens] DALL-E failed: {e}")
        return None


def generate_poster_ffmpeg(
    campaign_theme: str,
    output_path: Path,
    width: int = 1024,
    height: int = 1024,
    bg_color: str = "0x1a1a2e",
    text_color: str = "white",
) -> Optional[Path]:
    """Generate a poster PNG using ffmpeg lavfi + drawtext."""
    if not has_ffmpeg():
        log.warning("[Lens] ffmpeg not found — skipping poster")
        return None

    # Escape special chars for ffmpeg drawtext
    def esc(s: str) -> str:
        return s.replace("'", "\\'").replace(":", "\\:").replace("[", "\\[").replace("]", "\\]")

    title_text = esc("AskElira")
    theme_text = esc(campaign_theme[:60])
    url_text = esc("github.com/jellyforex/askelira")
    tagline_text = esc("5 AI agents + MiroFish swarm intelligence")

    vf = (
        f"drawtext=text='{title_text}':fontsize=72:fontcolor=white:x=(w-tw)/2:y=h*0.25:fontfile=/System/Library/Fonts/Helvetica.ttc,"
        f"drawtext=text='{tagline_text}':fontsize=28:fontcolor=0x00d4ff:x=(w-tw)/2:y=h*0.42,"
        f"drawtext=text='{theme_text}':fontsize=22:fontcolor=0xcccccc:x=(w-tw)/2:y=h*0.52,"
        f"drawtext=text='{url_text}':fontsize=20:fontcolor=0x888888:x=(w-tw)/2:y=h*0.80"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={width}x{height}:d=1",
        "-vf", vf,
        "-frames:v", "1",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and output_path.exists():
            log.info(f"[Lens] ffmpeg poster saved: {output_path}")
            return output_path
        else:
            # Try simpler version without font file (cross-platform)
            vf_simple = (
                f"drawtext=text='AskElira':fontsize=72:fontcolor=white:x=(w-tw)/2:y=h*0.25,"
                f"drawtext=text='5 AI agents + MiroFish swarm':fontsize=28:fontcolor=cyan:x=(w-tw)/2:y=h*0.42,"
                f"drawtext=text='github.com/jellyforex/askelira':fontsize=20:fontcolor=gray:x=(w-tw)/2:y=h*0.80"
            )
            cmd[cmd.index(vf)] = vf_simple
            result2 = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result2.returncode == 0 and output_path.exists():
                log.info(f"[Lens] ffmpeg poster saved (simple): {output_path}")
                return output_path
            log.warning(f"[Lens] ffmpeg poster failed: {result.stderr[:200]}")
            return None
    except Exception as e:
        log.warning(f"[Lens] ffmpeg poster error: {e}")
        return None


def generate_thumbnail_ffmpeg(
    campaign_theme: str,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
) -> Optional[Path]:
    """Generate YouTube thumbnail at 1280x720 via ffmpeg."""
    if not has_ffmpeg():
        return None

    def esc(s: str) -> str:
        return s.replace("'", "\\'").replace(":", "\\:").replace("[", "\\[").replace("]", "\\]")

    theme_short = campaign_theme[:50]

    vf = (
        f"drawtext=text='AskElira':fontsize=96:fontcolor=white:x=(w-tw)/2:y=h*0.20,"
        f"drawtext=text='{esc(theme_short)}':fontsize=36:fontcolor=cyan:x=(w-tw)/2:y=h*0.55,"
        f"drawtext=text='github.com/jellyforex/askelira':fontsize=24:fontcolor=gray:x=(w-tw)/2:y=h*0.82"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x1a1a2e:s={width}x{height}:d=1",
        "-vf", vf,
        "-frames:v", "1",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and output_path.exists():
            log.info(f"[Lens] Thumbnail saved: {output_path}")
            return output_path
        log.warning(f"[Lens] Thumbnail failed: {result.stderr[:200]}")
        return None
    except Exception as e:
        log.warning(f"[Lens] Thumbnail error: {e}")
        return None


# ------------------------------------------------------------------ #
# Demo video (6 slides × 10s = 60s)
# ------------------------------------------------------------------ #

SLIDE_SCRIPTS = [
    # (title_text, subtitle_text, body_text)
    (
        "AskElira",
        "Binary Outcome Prediction",
        "5 AI agents + MiroFish swarm intelligence"
    ),
    (
        "The Problem",
        "Predicting YES/NO outcomes is hard",
        "Markets misprice events | Human bias is everywhere"
    ),
    (
        "The Solution",
        "Swarm intelligence beats individual analysis",
        "1000 AI agents simulate crowd behavior | 3 independent runs"
    ),
    (
        "The Pipeline",
        "Alba → David → Vex → Elira → Steven",
        "Research → Simulate → Audit → Decide → Execute"
    ),
    (
        "Real Results",
        "~65% accuracy on prediction markets",
        "$0.015 per prediction | Self-hostable | MIT license"
    ),
    (
        "Get Started",
        "3 commands to your first prediction",
        "github.com/jellyforex/askelira"
    ),
]


def create_slide_ffmpeg(
    slide_num: int,
    title: str,
    subtitle: str,
    body: str,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    duration: int = 10,
) -> Optional[Path]:
    """Create a single slide PNG via ffmpeg."""
    if not has_ffmpeg():
        return None

    def esc(s: str) -> str:
        return s.replace("'", " ").replace(":", " ").replace("[", "(").replace("]", ")")

    vf = (
        f"drawtext=text='{esc(title)}':fontsize=72:fontcolor=white:x=(w-tw)/2:y=h*0.20,"
        f"drawtext=text='{esc(subtitle)}':fontsize=36:fontcolor=cyan:x=(w-tw)/2:y=h*0.48,"
        f"drawtext=text='{esc(body)}':fontsize=22:fontcolor=0xaaaaaa:x=(w-tw)/2:y=h*0.65,"
        f"drawtext=text='{slide_num}/6':fontsize=18:fontcolor=0x666666:x=w*0.92:y=h*0.92"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x1a1a2e:s={width}x{height}:d=1",
        "-vf", vf,
        "-frames:v", "1",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and output_path.exists():
            return output_path
        return None
    except Exception:
        return None


def assemble_demo_video(
    slides: List[Path],
    output_path: Path,
    slide_duration: int = 10,
) -> Optional[Path]:
    """Concatenate slide PNGs into a 60s MP4 using ffmpeg concat demuxer."""
    if not has_ffmpeg() or not slides:
        log.warning("[Lens] Cannot assemble video: ffmpeg not available or no slides")
        return None

    # Write concat file
    concat_path = MEDIA_DIR / "concat_list.txt"
    with open(concat_path, 'w') as f:
        for slide in slides:
            f.write(f"file '{slide.absolute()}'\n")
            f.write(f"duration {slide_duration}\n")
        # Repeat last slide to avoid ffmpeg trailing frame issue
        if slides:
            f.write(f"file '{slides[-1].absolute()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_path),
        "-vf", "fps=25,scale=1280:720",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            log.info(f"[Lens] Demo video saved: {output_path} ({size_mb:.1f} MB)")
            return output_path
        log.warning(f"[Lens] Video assembly failed: {result.stderr[:300]}")
        return None
    except Exception as e:
        log.warning(f"[Lens] Video assembly error: {e}")
        return None


# ------------------------------------------------------------------ #
# Main pipeline
# ------------------------------------------------------------------ #

def run_lens(
    plan: Optional[Dict] = None,
    content: Optional[Dict] = None,
    save: bool = True,
) -> Dict:
    """
    Main pipeline:
    1. Load improvement_plan.json (or use injected plan)
    2. Detect image backend
    3. Generate poster → data/media/poster.png
    4. Generate thumbnail → data/media/thumbnail.png
    5. Create 6 slides → data/media/slides/
    6. Assemble demo video → data/media/demo.mp4
    7. Return manifest dict
    """
    load_dotenv(Path(__file__).parent.parent / ".env")

    if plan is None:
        if IMPROVEMENT_PLAN_FILE.exists():
            with open(IMPROVEMENT_PLAN_FILE) as f:
                plan = json.load(f)
        else:
            log.warning("[Lens] No improvement_plan.json — using defaults")
            plan = {
                "campaign_theme": "Watch the swarm think: AskElira live demo",
                "top_tactic": "Add demo video",
                "target_repo": TARGET_REPO,
            }

    campaign_theme = plan.get("campaign_theme", "AskElira: AI prediction swarm")

    log.info("=" * 60)
    log.info("[Lens] STARTING MEDIA PRODUCTION")
    log.info(f"[Lens] Theme: {campaign_theme}")
    log.info("=" * 60)

    backend = detect_image_backend()

    # Generate poster
    poster_path = MEDIA_DIR / "poster.png"
    poster = None
    if backend == "openai":
        poster = generate_poster_openai(campaign_theme, poster_path)
    if poster is None:  # fallback
        poster = generate_poster_ffmpeg(campaign_theme, poster_path)

    # Generate thumbnail
    thumbnail_path = MEDIA_DIR / "thumbnail.png"
    thumbnail = generate_thumbnail_ffmpeg(campaign_theme, thumbnail_path)

    # Create slides
    slides = []
    for i, (title, subtitle, body) in enumerate(SLIDE_SCRIPTS, 1):
        slide_path = SLIDES_DIR / f"slide_{i:02d}.png"
        result = create_slide_ffmpeg(i, title, subtitle, body, slide_path)
        if result:
            slides.append(result)
            log.info(f"[Lens] Slide {i}/6 created")

    # Assemble demo video
    video_path = MEDIA_DIR / "demo.mp4"
    video = None
    if slides:
        video = assemble_demo_video(slides, video_path)

    manifest = {
        "poster": str(poster) if poster else None,
        "thumbnail": str(thumbnail) if thumbnail else None,
        "demo_video": str(video) if video else None,
        "slides": [str(s) for s in slides],
        "backend_used": backend,
        "target_repo": plan.get("target_repo", TARGET_REPO),
        "generated_at": datetime.utcnow().isoformat(),
    }

    if save:
        manifest_path = MEDIA_DIR / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        log.info(f"[Lens] Manifest saved: {manifest_path}")

    log.info("=" * 60)
    log.info("[Lens] MEDIA PRODUCTION COMPLETE")
    log.info(f"[Lens] Poster: {'✓' if poster else '✗'}")
    log.info(f"[Lens] Thumbnail: {'✓' if thumbnail else '✗'}")
    log.info(f"[Lens] Demo video: {'✓' if video else '✗'} ({len(slides)} slides)")
    log.info("=" * 60)

    return manifest


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )

    manifest = run_lens()

    print("\n" + "=" * 60)
    print("LENS COMPLETE")
    print("=" * 60)
    print(f"\nBackend used: {manifest['backend_used']}")
    print(f"Poster:       {'✓ ' + manifest['poster'] if manifest['poster'] else '✗ not generated'}")
    print(f"Thumbnail:    {'✓ ' + manifest['thumbnail'] if manifest['thumbnail'] else '✗ not generated'}")
    print(f"Demo video:   {'✓ ' + manifest['demo_video'] if manifest['demo_video'] else '✗ not generated'}")
    print(f"Slides:       {len(manifest['slides'])} slides created")
