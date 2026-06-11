#!/usr/bin/env python3
"""
Full Pipeline Orchestrator

Runs all 3 stages:
1. Discover trends
2. Investigate topics
3. Synthesize SaaS ideas
"""

import sys
import subprocess
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Robust path resolution for imports (works from any working directory)
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_ROOT = SCRIPT_DIR.parent

# Add paths for imports
sys.path.insert(0, str(SCRIPT_DIR))  # For helpers
sys.path.insert(0, str(SKILL_ROOT))  # For skill modules

from helpers.lens_manager import LensManager
from helpers.state_manager import StateManager


def run_stage(script_name: str, args: list, stage_name: str) -> dict:
    """
    Run a stage script and return its output.

    Args:
        script_name: Script filename
        args: Command-line arguments
        stage_name: Human-readable stage name

    Returns:
        Dictionary with result data
    """
    script_path = Path(__file__).parent / script_name
    cmd = ['python3', str(script_path)] + args

    print(f"\n{'='*60}")
    print(f"🚀 {stage_name}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        # Print stdout for user feedback
        if result.stdout:
            print(result.stdout)

        # Print stderr warnings
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            raise RuntimeError(f"{stage_name} failed with code {result.returncode}")

        # Try to parse JSON output
        try:
            # Find JSON block (starts with '{' or '[' on its own line)
            lines = result.stdout.strip().split('\n')
            json_start = None
            for i, line in enumerate(lines):
                if line.strip() in ('{', '['):
                    json_start = i
                    break

            if json_start is not None:
                # Extract JSON lines from start to end
                json_lines = lines[json_start:]
                json_str = '\n'.join(json_lines)
                data = json.loads(json_str)
                return data
            else:
                # Try parsing entire stdout as JSON
                data = json.loads(result.stdout)
                return data
        except json.JSONDecodeError:
            return {'success': True, 'output': result.stdout}

        return {'success': True}

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{stage_name} timed out after 10 minutes")
    except Exception as e:
        raise RuntimeError(f"{stage_name} error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Run full SaaS idea discovery pipeline',
        epilog="""
PIPELINE TIMING EXPECTATIONS:
- Stage 1 (Trend Discovery): ~30-60s
- Stage 2 (Deep Research): ~2-4 min per topic
- Stage 3 (Idea Synthesis): ~30-60s per topic
- Total for 1 topic: ~3-5 minutes
- Total for 3 topics: ~8-12 minutes

Maximum timeout: 10 minutes per stage, 30 minutes total.
        """
    )
    parser.add_argument('--lens', help='Override lens (default: day-of-week rotation)')
    parser.add_argument('--topics', type=int, default=1, help='Number of topics to analyze (max 3)')
    parser.add_argument('--force', action='store_true', help='Re-analyze already-analyzed topics')
    parser.add_argument('--skip-discovery', action='store_true', help='Use existing trends.json')
    parser.add_argument('--output-dir', help='Custom output directory')
    parser.add_argument('--include-viability', action='store_true', help='Include viability scoring (0-100) for ideas')
    parser.add_argument('--pain-threshold', type=int, default=0, help='Minimum pain severity score (0-100) to include idea')
    parser.add_argument('--min-viability', type=int, default=0, help='Minimum viability score (0-100) to include idea')

    args = parser.parse_args()

    # Limit topics to reasonable number
    if args.topics > 3:
        print("⚠️  Limiting to 3 topics (use --topics to adjust)", file=sys.stderr)
        args.topics = 3

    start_time = time.time()

    try:
        # Initialize managers
        lens_manager = LensManager()
        state_manager = StateManager()

        # Get active lens
        lens = lens_manager.get_active_lens(override=args.lens)
        lens_name = lens['name']

        print("=" * 60)
        print("🎯 SaaS Idea Finder - Full Pipeline")
        print("=" * 60)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔭 Lens: {lens_name}")
        print(f"📊 Topics to analyze: {args.topics}")
        print(f"🔄 Force re-analysis: {args.force}")
        if args.include_viability:
            print(f"📈 Viability scoring: Enabled")
        if args.pain_threshold > 0:
            print(f"🔥 Pain threshold: {args.pain_threshold}")
        if args.min_viability > 0:
            print(f"✅ Min viability: {args.min_viability}")

        trends_data = None

        # Stage 1: Discover Trends
        if not args.skip_discovery:
            discover_args = ['--limit', str(args.topics * 2)]  # Get extra for filtering
            if args.lens:
                discover_args.extend(['--lens', args.lens])
            if args.force:
                discover_args.append('--force')

            result = run_stage('discover_trends.py', discover_args, 'Stage 1: Trend Discovery')
            if result.get('success'):
                trends_data = result.get('data', {})
        else:
            # Load existing trends
            output_dir = state_manager.get_output_dir_for_date(stage='discover')
            trends_file = output_dir / 'trends.json'
            if not trends_file.exists():
                print("❌ Error: No existing trends.json found", file=sys.stderr)
                sys.exit(1)

            with open(trends_file, 'r') as f:
                data = json.load(f)
                trends_data = data.get('data', {})

        # Get topics to analyze
        topics = trends_data.get('topics', [])
        if not topics:
            print("❌ No topics found to analyze", file=sys.stderr)
            sys.exit(1)

        # Filter out already-analyzed if not forcing
        if not args.force:
            topics = [t for t in topics if not t.get('already_analyzed', False)]

        if not topics:
            print("ℹ️  All topics already analyzed. Use --force to re-analyze.", file=sys.stderr)
            sys.exit(0)

        # Limit to requested number
        topics = topics[:args.topics]

        print(f"\n📋 Selected {len(topics)} topic(s) for deep analysis:")
        for i, topic in enumerate(topics, 1):
            print(f"   {i}. {topic['name']} (score: {topic['score']})")

        analyzed_count = 0
        all_outputs = []

        # Process each topic
        for i, topic in enumerate(topics, 1):
            topic_name = topic['name']

            print(f"\n{'#'*60}")
            print(f"# Processing Topic {i}/{len(topics)}: {topic_name}")
            print(f"{'#'*60}")

            try:
                # Stage 2: Investigate
                investigate_args = ['--topic', topic_name]
                if args.lens:
                    investigate_args.extend(['--lens', args.lens])

                run_stage('investigate_topic.py', investigate_args, f'Stage 2: Investigating "{topic_name}"')

                # Get research output path
                output_dir = state_manager.get_output_dir_for_date(stage='research')
                safe_topic = topic_name.lower().replace(' ', '-')[:50]
                research_file = output_dir / f"{safe_topic}.md"

                # Stage 3: Synthesize
                synthesize_args = ['--research', str(research_file)]
                if args.lens:
                    synthesize_args.extend(['--lens', args.lens])
                if args.include_viability:
                    synthesize_args.append('--include-viability')
                if args.pain_threshold > 0:
                    synthesize_args.extend(['--pain-threshold', str(args.pain_threshold)])
                if args.min_viability > 0:
                    synthesize_args.extend(['--min-viability', str(args.min_viability)])

                run_stage('synthesize_saas_ideas.py', synthesize_args, f'Stage 3: Generating SaaS Ideas')

                # Get ideas output path
                ideas_dir = state_manager.get_output_dir_for_date(stage='ideas')
                ideas_file = ideas_dir / f"{safe_topic}_ideas.md"

                # Mark as analyzed
                state_manager.mark_topic_analyzed(topic_name, {
                    'lens': lens_name,
                    'output_files': {
                        'research': str(research_file),
                        'ideas': str(ideas_file)
                    }
                })

                all_outputs.append({
                    'topic': topic_name,
                    'research': str(research_file),
                    'ideas': str(ideas_file)
                })

                analyzed_count += 1

            except Exception as e:
                print(f"❌ Error processing topic '{topic_name}': {e}", file=sys.stderr)
                continue

        # Summary
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        print("\n" + "=" * 60)
        print("✅ PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   - Topics analyzed: {analyzed_count}/{len(topics)}")
        print(f"   - Duration: {minutes}m {seconds}s")
        print(f"   - Lens used: {lens_name}")

        if all_outputs:
            print(f"\n📁 Outputs:")
            for output in all_outputs:
                print(f"\n   Topic: {output['topic']}")
                print(f"   Research: {output['research']}")
                print(f"   Ideas: {output['ideas']}")

        # Save summary
        summary_file = state_manager.outputs_dir / f"{datetime.now().strftime('%Y-%m-%d')}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'date': datetime.now().isoformat(),
                'lens': lens_name,
                'topics_analyzed': analyzed_count,
                'duration_seconds': int(duration),
                'outputs': all_outputs
            }, f, indent=2)

        print(f"\n💾 Summary saved: {summary_file}")

        sys.exit(0 if analyzed_count > 0 else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}", file=sys.stderr)
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()