#!/usr/bin/env python3
"""
Search for libraries in Context7.

Usage:
    python3 resolve_library.py --query "library name" [--limit N]

Examples:
    python3 resolve_library.py --query "react"
    python3 resolve_library.py --query "next.js" --limit 3
    python3 resolve_library.py --query "mongodb typescript"
"""

import argparse
import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from context7_api import (
    search_libraries,
    output_success,
    output_error
)


def main():
    parser = argparse.ArgumentParser(
        description='Search for libraries in Context7'
    )
    parser.add_argument(
        '--query', '-q',
        required=True,
        help='Library name to search for (e.g., "react", "next.js", "prisma")'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Maximum number of results (default: 10)'
    )

    args = parser.parse_args()

    result = search_libraries(args.query, limit=args.limit)

    if 'error' in result:
        output_error(result.get('error'), result.get('message'))
        sys.exit(1)

    # Handle different response formats
    matches = result.get('results', result.get('matches', result.get('data', [])))
    if isinstance(result, list):
        matches = result

    if not matches:
        output_error(
            "no_matches",
            f"No libraries found matching '{args.query}'. Try a different search term."
        )
        sys.exit(1)

    output_success({
        "query": args.query,
        "count": len(matches),
        "matches": matches
    })


if __name__ == '__main__':
    main()