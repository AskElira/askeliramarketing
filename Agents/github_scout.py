"""
GitHub Scout — Marketing Agent (Alba Variant)

Scans GitHub trending, HN front page, and successful AI repos.
Analyzes what made them viral (README, demos, Show HN posts).
Outputs success patterns for MiroFish trend analyzer.

This is the FIRST agent in the marketing pipeline.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger("github_scout")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TRENDING_REPOS_FILE = DATA_DIR / "trending_repos.json"
SUCCESS_PATTERNS_FILE = DATA_DIR / "success_patterns.json"

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Claude config
MODEL = "claude-haiku-4-5-20251001"  # Haiku for web search
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# GitHub API headers (fine-grained PATs use Bearer; classic PATs use token)
_auth_prefix = "Bearer" if (GITHUB_TOKEN or "").startswith("github_pat_") else "token"
GITHUB_HEADERS = {
    "Authorization": f"{_auth_prefix} {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


# ------------------------------------------------------------------ #
# Step 1: Scrape GitHub Trending
# ------------------------------------------------------------------ #

def scrape_github_trending(
    topic: str = "ai-agents",
    min_stars: int = 500,
    timeframe: str = "week"
) -> List[Dict]:
    """
    Scrape GitHub trending repos in a specific topic.
    
    Args:
        topic: Topic to filter (e.g., "ai-agents", "machine-learning")
        min_stars: Minimum stars to consider
        timeframe: "day", "week", or "month"
    
    Returns:
        List of repo dicts with: name, url, stars, description, growth
    """
    log.info(f"[GitHub Scout] Scraping trending repos: topic={topic}, min_stars={min_stars}")
    
    # Calculate date range
    date_map = {
        "day": datetime.now() - timedelta(days=1),
        "week": datetime.now() - timedelta(days=7),
        "month": datetime.now() - timedelta(days=30)
    }
    created_after = date_map.get(timeframe, date_map["week"])
    
    # GitHub Search API query
    query = f"topic:{topic} stars:>{min_stars} created:>{created_after.strftime('%Y-%m-%d')}"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=10"
    
    try:
        response = requests.get(url, headers=GITHUB_HEADERS)
        response.raise_for_status()
        
        data = response.json()
        repos = []
        
        for item in data.get("items", []):
            repos.append({
                "name": item["full_name"],
                "url": item["html_url"],
                "stars": item["stargazers_count"],
                "description": item.get("description", ""),
                "language": item.get("language", "Unknown"),
                "created_at": item["created_at"],
                "topics": item.get("topics", [])
            })
        
        log.info(f"[GitHub Scout] Found {len(repos)} trending repos")
        return repos
        
    except Exception as e:
        log.error(f"[GitHub Scout] GitHub API error: {e}")
        return []


# ------------------------------------------------------------------ #
# Step 2: Analyze Repo Success Tactics
# ------------------------------------------------------------------ #

def analyze_repo_tactics(repo: Dict) -> Dict:
    """
    Analyze a single repo to extract success tactics.
    Uses Claude with web search to find:
    - README quality (hook, demo, install steps)
    - Show HN post (if exists)
    - Demo video/GIF
    - Launch strategy
    
    Args:
        repo: Repo dict from scrape_github_trending()
    
    Returns:
        Dict with tactics: {readme_hook, has_demo_video, show_hn_post, etc.}
    """
    log.info(f"[GitHub Scout] Analyzing tactics for {repo['name']}")
    
    prompt = f"""Analyze this GitHub repo's success tactics:

Repo: {repo['name']}
URL: {repo['url']}
Stars: {repo['stars']:,}
Description: {repo['description']}

Search for:
1. README.md on GitHub (look at the actual repo)
2. Show HN submission (search "Show HN {repo['name'].split('/')[1]} site:news.ycombinator.com")
3. Launch announcement on Twitter/Reddit

Extract:
- README hook (opening line/paragraph)
- Demo video/GIF? (yes/no + URL if exists)
- Installation steps (how many commands?)
- Show HN post (yes/no + score if found)
- Twitter/Reddit presence

Output as JSON:
{{
  "readme_hook": "...",
  "has_demo": true/false,
  "demo_url": "...",
  "install_steps": 3,
  "show_hn": {{"exists": true, "score": 234, "url": "..."}},
  "launch_tactics": ["..."]
}}
"""
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract JSON from response
        content = response.content
        for block in content:
            if block.type == "text":
                # Try to extract JSON
                json_match = re.search(r'\{[\s\S]*\}', block.text)
                if json_match:
                    tactics = json.loads(json_match.group())
                    log.info(f"[GitHub Scout] Extracted tactics for {repo['name']}")
                    return tactics
        
        log.warning(f"[GitHub Scout] No tactics JSON found for {repo['name']}")
        return {}
        
    except Exception as e:
        log.error(f"[GitHub Scout] Error analyzing {repo['name']}: {e}")
        return {}


# ------------------------------------------------------------------ #
# Step 3: Build Success Pattern Summary
# ------------------------------------------------------------------ #

def build_success_patterns(repos_with_tactics: List[Dict]) -> Dict:
    """
    Analyze all trending repos and extract common success patterns.
    
    Args:
        repos_with_tactics: List of repos with tactics analyzed
    
    Returns:
        Dict with aggregated patterns:
        {
            "common_readme_hooks": [...],
            "demo_percentage": 0.8,
            "avg_install_steps": 3.2,
            "show_hn_success_rate": 0.6,
            "recommended_tactics": [...]
        }
    """
    log.info("[GitHub Scout] Building success pattern summary")
    
    total = len(repos_with_tactics)
    if total == 0:
        return {}
    
    # Aggregate patterns
    has_demo_count = sum(1 for r in repos_with_tactics if r.get("tactics", {}).get("has_demo", False))
    install_steps = [r.get("tactics", {}).get("install_steps", 5) for r in repos_with_tactics if r.get("tactics")]
    show_hn_count = sum(1 for r in repos_with_tactics if r.get("tactics", {}).get("show_hn", {}).get("exists", False))
    
    patterns = {
        "analyzed_repos": total,
        "demo_percentage": round(has_demo_count / total, 2),
        "avg_install_steps": round(sum(install_steps) / len(install_steps), 1) if install_steps else 5,
        "show_hn_success_rate": round(show_hn_count / total, 2),
        "common_tactics": [],
        "readme_hooks": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Extract common tactics
    for repo in repos_with_tactics:
        tactics = repo.get("tactics", {})
        
        # Collect README hooks
        hook = tactics.get("readme_hook", "")
        if hook and len(hook) < 200:
            patterns["readme_hooks"].append({
                "repo": repo["name"],
                "hook": hook
            })
        
        # Collect launch tactics
        launch_tactics = tactics.get("launch_tactics", [])
        patterns["common_tactics"].extend(launch_tactics)
    
    # Deduplicate tactics
    patterns["common_tactics"] = list(set(patterns["common_tactics"]))
    
    # Recommendations
    recommendations = []
    if patterns["demo_percentage"] > 0.7:
        recommendations.append("Add demo video/GIF (70%+ of successful repos have one)")
    if patterns["avg_install_steps"] <= 3:
        recommendations.append(f"Simplify installation to ≤{int(patterns['avg_install_steps'])} commands")
    if patterns["show_hn_success_rate"] > 0.5:
        recommendations.append("Launch on Show HN (50%+ of trending repos did)")
    
    patterns["recommendations"] = recommendations
    
    log.info(f"[GitHub Scout] Success patterns: {len(recommendations)} recommendations")
    return patterns


# ------------------------------------------------------------------ #
# Step 4: Main Pipeline
# ------------------------------------------------------------------ #

def run_scout(
    topics: List[str] = ["ai-agents", "machine-learning", "llm"],
    min_stars: int = 500,
    save: bool = True
) -> Dict:
    """
    Run the full GitHub Scout pipeline.
    
    Steps:
    1. Scrape GitHub trending for each topic
    2. Analyze tactics for each repo
    3. Build aggregated success patterns
    4. Save to data/ directory
    
    Args:
        topics: List of GitHub topics to search
        min_stars: Minimum stars to consider
        save: Save results to JSON files
    
    Returns:
        Dict with trending_repos and success_patterns
    """
    log.info("=" * 60)
    log.info("[GitHub Scout] STARTING PIPELINE")
    log.info("=" * 60)
    
    all_repos = []
    
    # Step 1: Scrape trending repos
    for topic in topics:
        repos = scrape_github_trending(topic=topic, min_stars=min_stars)
        all_repos.extend(repos)
    
    # Deduplicate by name
    seen = set()
    unique_repos = []
    for repo in all_repos:
        if repo["name"] not in seen:
            seen.add(repo["name"])
            unique_repos.append(repo)
    
    log.info(f"[GitHub Scout] Total unique repos: {len(unique_repos)}")
    
    # Step 2: Analyze tactics (limit to top 5 for speed)
    repos_with_tactics = []
    for repo in unique_repos[:5]:
        tactics = analyze_repo_tactics(repo)
        repos_with_tactics.append({
            **repo,
            "tactics": tactics
        })
    
    # Step 3: Build success patterns
    patterns = build_success_patterns(repos_with_tactics)
    
    # Step 4: Save results
    if save:
        with open(TRENDING_REPOS_FILE, 'w') as f:
            json.dump(repos_with_tactics, f, indent=2)
        log.info(f"[GitHub Scout] Saved trending repos: {TRENDING_REPOS_FILE}")
        
        with open(SUCCESS_PATTERNS_FILE, 'w') as f:
            json.dump(patterns, f, indent=2)
        log.info(f"[GitHub Scout] Saved success patterns: {SUCCESS_PATTERNS_FILE}")
    
    log.info("=" * 60)
    log.info("[GitHub Scout] PIPELINE COMPLETE")
    log.info("=" * 60)
    
    return {
        "trending_repos": repos_with_tactics,
        "success_patterns": patterns
    }


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )
    
    # Run scout
    result = run_scout(
        topics=["ai-agents", "machine-learning", "autonomous-ai"],
        min_stars=500,
        save=True
    )
    
    print("\n" + "=" * 60)
    print("✅ GITHUB SCOUT COMPLETE")
    print("=" * 60)
    print(f"\nFound {len(result['trending_repos'])} trending repos")
    print(f"\nSuccess Pattern Recommendations:")
    for i, rec in enumerate(result['success_patterns'].get('recommendations', []), 1):
        print(f"  {i}. {rec}")
    print(f"\nData saved to:")
    print(f"  - {TRENDING_REPOS_FILE}")
    print(f"  - {SUCCESS_PATTERNS_FILE}")
    print()
