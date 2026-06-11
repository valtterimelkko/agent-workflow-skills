#!/usr/bin/env python3
"""
Stage 2: Investigate Topic

Uses GPT Researcher to conduct deep research on a trending topic.
Reuses the environment setup pattern from deeper-research skill.
"""

import asyncio
import sys
import os
import time
import argparse
from pathlib import Path

# Robust path resolution for imports (works from any working directory)
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_ROOT = SCRIPT_DIR.parent
SHARED_DIR = Path(__file__).resolve().parents[3] / 'shared'

# Add paths for imports
sys.path.insert(0, str(SCRIPT_DIR))  # For helpers
sys.path.insert(0, str(SKILL_ROOT))  # For skill modules
sys.path.insert(0, str(SHARED_DIR))  # For shared utilities

from credentials import load_credential, CredentialNotFound
from helpers.lens_manager import LensManager
from helpers.state_manager import StateManager

# Set environment variables BEFORE importing GPTResearcher
os.environ.setdefault("RETRIEVER", "duckduckgo")

# Load OpenRouter API key using shared credential loader
try:
    api_key = load_credential(
        "OPENROUTER_API_KEY",
        required=True
    )
    os.environ["OPENROUTER_API_KEY"] = api_key
except CredentialNotFound as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)

# Configure OpenRouter
os.environ.setdefault("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENAI_API_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENROUTER_LIMIT_RPS", "1")

# Configure LLM models
os.environ.setdefault("FAST_LLM", "openrouter:deepseek/deepseek-chat")
os.environ.setdefault("SMART_LLM", "openrouter:deepseek/deepseek-chat")
os.environ.setdefault("STRATEGIC_LLM", "openrouter:deepseek/deepseek-chat")

# Set OPENAI_API_KEY for embeddings compatibility
if not os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENROUTER_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]

os.environ.setdefault("EMBEDDING", "openai:text-embedding-3-small")

# Import GPTResearcher after environment configuration
sys.path.insert(0, os.path.expanduser("~/gpt-researcher-env/lib/python3.12/site-packages"))
from gpt_researcher import GPTResearcher


async def research_topic(topic: str, lens_name: str, breadth: int = 3, depth: int = 2) -> str:
    """
    Research a topic using GPT Researcher with lens context.

    Args:
        topic: Topic to research
        lens_name: Lens name for context
        breadth: Research breadth
        depth: Research depth

    Returns:
        Markdown research report
    """
    # Get research focus from lens
    lens_manager = LensManager()
    research_focus = lens_manager.get_research_focus(lens_name)

    # Build context-aware query
    focus_context = ", ".join(research_focus[:3]) if research_focus else ""
    query = f"{topic}. Focus on: {focus_context}" if focus_context else topic

    print(f"📝 Researching: {topic}")
    print(f"🎯 Focus areas: {focus_context}")

    # Configure deep research if breadth/depth specified
    if breadth > 0 and depth > 0:
        os.environ["DEEP_RESEARCH_BREADTH"] = str(breadth)
        os.environ["DEEP_RESEARCH_DEPTH"] = str(depth)
        os.environ["DEEP_RESEARCH_CONCURRENCY"] = "4"

    # Initialize researcher
    researcher = GPTResearcher(
        query=query,
        report_type="research_report",
        report_format="markdown",
        report_source="web",
        verbose=True
    )

    # Conduct research
    print("🔍 Gathering sources from web...")
    await researcher.conduct_research()

    print("⏳ Synthesizing comprehensive report...")
    report = await researcher.write_report()

    sources = researcher.get_research_sources()
    print(f"✅ Research complete! Sources used: {len(sources) if sources else 'N/A'}")

    return report


async def main():
    parser = argparse.ArgumentParser(description='Research a topic using GPT Researcher')
    parser.add_argument('--topic', required=True, help='Topic to research')
    parser.add_argument('--keywords', help='Additional keywords (comma-separated)')
    parser.add_argument('--lens', help='Lens context for research')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--breadth', type=int, default=1, help='Research breadth (default: 1 for faster research)')
    parser.add_argument('--depth', type=int, default=1, help='Research depth (default: 1 for faster research)')

    args = parser.parse_args()

    start_time = time.time()

    try:
        # Get lens for context
        if args.lens:
            lens_name = args.lens
        else:
            lens_manager = LensManager()
            lens = lens_manager.get_active_lens()
            lens_name = lens['name']

        print(f"🔬 Starting deep investigation...")
        print(f"📋 Topic: {args.topic}")
        print(f"🔭 Lens: {lens_name}")

        # Research the topic
        report = await research_topic(args.topic, lens_name, args.breadth, args.depth)

        # Determine output path
        if args.output:
            output_path = Path(args.output).expanduser()
        else:
            state_manager = StateManager()
            output_dir = state_manager.get_output_dir_for_date(stage='research')
            # Sanitize topic name for filename
            safe_topic = args.topic.lower().replace(' ', '-').replace('/', '-')[:50]
            output_path = output_dir / f"{safe_topic}.md"

        # Save report
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata frontmatter
        metadata = f"""---
topic: "{args.topic}"
lens: "{lens_name}"
date: "{time.strftime('%Y-%m-%d')}"
research_breadth: {args.breadth}
research_depth: {args.depth}
---

"""
        final_report = metadata + report

        with open(output_path, 'w') as f:
            f.write(final_report)

        duration = time.time() - start_time

        print(f"\n✅ Investigation complete!")
        print(f"   - Duration: {duration:.1f}s")
        print(f"   - Output: {output_path}")

        sys.exit(0)

    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Research failed after {duration:.1f}s: {e}", file=sys.stderr)
        import traceback
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())