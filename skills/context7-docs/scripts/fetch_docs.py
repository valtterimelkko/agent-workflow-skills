#!/usr/bin/env python3
"""
Fetch documentation for a Context7 library.

Usage:
    python3 fetch_docs.py --library "owner/repo" [--topic "topic"] [--type code|info]

Examples:
    python3 fetch_docs.py --library "vercel/next.js"
    python3 fetch_docs.py --library "prisma/prisma" --topic "postgresql setup"
    python3 fetch_docs.py --library "mongodb/docs" --topic "typescript" --type info
    python3 fetch_docs.py --library "vercel/next.js" --version "v15.1.8" --topic "routing"
"""

import argparse
import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from context7_api import (
    get_library_docs,
    parse_library_id,
    output_success,
    output_error
)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch documentation from Context7 for a library'
    )
    parser.add_argument(
        '--library', '-l',
        required=True,
        help='Library in format "owner/repo" (e.g., "vercel/next.js", "prisma/prisma")'
    )
    parser.add_argument(
        '--topic', '-t',
        help='Topic to focus on (e.g., "routing", "authentication", "database setup")'
    )
    parser.add_argument(
        '--type', '-T',
        choices=['code', 'info'],
        default='code',
        help='Type of docs: "code" for code snippets, "info" for documentation (default: code)'
    )
    parser.add_argument(
        '--version', '-v',
        help='Specific version tag (e.g., "v15.1.8")'
    )
    parser.add_argument(
        '--page', '-p',
        type=int,
        default=1,
        help='Page number for pagination (default: 1)'
    )

    args = parser.parse_args()

    # Parse library into owner/repo
    parsed = parse_library_id(args.library)
    if not parsed:
        output_error(
            "invalid_library",
            f"Invalid library format: '{args.library}'. Use format 'owner/repo' (e.g., 'vercel/next.js')"
        )
        sys.exit(1)

    owner, repo = parsed

    result = get_library_docs(
        owner=owner,
        repo=repo,
        topic=args.topic,
        doc_type=args.type,
        version=args.version,
        page=args.page
    )

    if 'error' in result:
        output_error(result.get('error'), result.get('message'))
        sys.exit(1)

    output_success({
        "library": f"{owner}/{repo}",
        "topic": args.topic,
        "type": args.type,
        "version": args.version,
        "page": args.page,
        "content": result
    })


if __name__ == '__main__':
    main()