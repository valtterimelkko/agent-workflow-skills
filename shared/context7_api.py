#!/usr/bin/env python3
"""
Context7 API client for fetching library documentation.

This module provides:
- Library ID resolution (fuzzy search)
- Documentation fetching with topic filtering
- Token-bounded responses
- JSON output formatting

API Documentation: https://context7.com/docs
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error

# ============================================================================
# CONSTANTS
# ============================================================================

CONTEXT7_BASE_URL = "https://context7.com/api/v2"
DEFAULT_TOKENS = 5000
MIN_TOKENS = 1000
MAX_TOKENS = 50000

# ============================================================================
# CREDENTIAL LOADING
# ============================================================================

def load_api_key():
    """
    Load Context7 API key from environment or ~/.bashrc.

    Checks in order:
    1. CONTEXT7_API_KEY environment variable
    2. ~/.bashrc (parses export CONTEXT7_API_KEY="...")

    Returns:
        str: The Context7 API key

    Raises:
        SystemExit: If key is not found
    """
    # First try environment variable
    api_key = os.environ.get('CONTEXT7_API_KEY')
    if api_key:
        return api_key

    # Fallback: parse from ~/.bashrc
    bashrc_path = os.path.expanduser('~/.bashrc')
    if os.path.exists(bashrc_path):
        try:
            with open(bashrc_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('export CONTEXT7_API_KEY='):
                        # Extract value, handling quotes
                        value = line.split('=', 1)[1].strip()
                        # Remove surrounding quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        if value:
                            return value
        except Exception:
            pass

    output_error(
        "CONTEXT7_API_KEY not found",
        "Key should be set as environment variable: export CONTEXT7_API_KEY='your-key' or in ~/.bashrc"
    )
    sys.exit(1)

def get_headers():
    """
    Get standard Context7 API headers.

    Returns:
        dict: Headers with Authorization
    """
    api_key = load_api_key()
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def output_success(data):
    """
    Output successful JSON response.

    Args:
        data: Dictionary to output as JSON
    """
    result = {"success": True, "data": data}
    print(json.dumps(result, indent=2, ensure_ascii=False))

def output_error(message, details=None):
    """
    Output error JSON response.

    Args:
        message: Error message string
        details: Optional additional details
    """
    result = {"success": False, "error": message}
    if details:
        result["details"] = details
    print(json.dumps(result, indent=2, ensure_ascii=False))

# ============================================================================
# API FUNCTIONS
# ============================================================================

def search_libraries(query, limit=10):
    """
    Search for libraries in Context7.

    Args:
        query: Search query (e.g., "react", "next.js", "mongodb")
        limit: Maximum number of results (default: 10)

    Returns:
        dict: Response with search results
    """
    headers = get_headers()

    params = {'query': query, 'limit': limit}
    url = f"{CONTEXT7_BASE_URL}/search?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            error_data = json.loads(error_body)
            return {"error": error_data.get("error", str(e)), "message": error_data.get("message", error_body)}
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}", "message": error_body}
    except urllib.error.URLError as e:
        return {"error": "connection_error", "message": str(e.reason)}
    except Exception as e:
        return {"error": "unknown_error", "message": str(e)}


def get_library_docs(owner, repo, topic=None, doc_type="code", version=None, page=1):
    """
    Fetch documentation for a Context7 library.

    Args:
        owner: Repository owner (e.g., "vercel")
        repo: Repository name (e.g., "next.js")
        topic: Optional topic to focus on (e.g., "routing", "authentication")
        doc_type: Type of docs - "code" for code snippets, "info" for docs
        version: Optional version tag (e.g., "v15.1.8")
        page: Page number for pagination (default: 1)

    Returns:
        dict: Response with documentation content
    """
    headers = get_headers()

    # Build URL path
    if version:
        url = f"{CONTEXT7_BASE_URL}/docs/{doc_type}/{owner}/{repo}/{version}"
    else:
        url = f"{CONTEXT7_BASE_URL}/docs/{doc_type}/{owner}/{repo}"

    # Build query parameters
    params = {}
    if topic:
        params['topic'] = topic
    if page > 1:
        params['page'] = page

    if params:
        url += '?' + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=60) as response:
            raw_data = response.read().decode('utf-8')
            content_type = response.headers.get('Content-Type', '')

            # API returns plain text for docs, JSON for errors
            if 'application/json' in content_type:
                return json.loads(raw_data)
            else:
                # Return as content dict for plain text responses
                return {
                    "content": raw_data,
                    "library": f"{owner}/{repo}",
                    "topic": topic,
                    "type": doc_type
                }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            error_data = json.loads(error_body)
            return {
                "error": error_data.get("error", str(e)),
                "message": error_data.get("message", error_body)
            }
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}", "message": error_body}
    except urllib.error.URLError as e:
        return {"error": "connection_error", "message": str(e.reason)}
    except Exception as e:
        return {"error": "unknown_error", "message": str(e)}


def parse_library_id(library_id):
    """
    Parse a library ID into owner and repo.

    Args:
        library_id: Library ID in format "owner/repo" or "/owner/repo"

    Returns:
        tuple: (owner, repo) or None if invalid
    """
    path = library_id.lstrip('/')
    parts = path.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_best_match(matches, ecosystem=None):
    """
    Select the best library match from results.

    Ranking criteria:
    1. Exact name match
    2. Trust score
    3. GitHub stars
    4. Ecosystem match (if specified)

    Args:
        matches: List of match objects from resolve_library_id
        ecosystem: Optional ecosystem to prefer (e.g., "javascript", "python")

    Returns:
        dict: Best matching library, or None if no matches
    """
    if not matches:
        return None

    def score_match(match):
        score = 0
        # Trust score is primary factor (0-1 range, multiply by 100)
        score += match.get('trustScore', 0) * 100
        # Stars as secondary factor (log scale to avoid overwhelming)
        import math
        stars = match.get('stars', 0)
        if stars > 0:
            score += min(math.log10(stars) * 5, 25)
        # Ecosystem bonus
        if ecosystem and match.get('ecosystem', '').lower() == ecosystem.lower():
            score += 10
        return score

    sorted_matches = sorted(matches, key=score_match, reverse=True)
    return sorted_matches[0] if sorted_matches else None


def format_library_info(match):
    """
    Format a library match for display.

    Args:
        match: Library match object

    Returns:
        str: Formatted library information
    """
    lines = []
    lines.append(f"**{match.get('name', 'Unknown')}**")
    lines.append(f"  ID: `{match.get('id', 'unknown')}`")
    if match.get('description'):
        lines.append(f"  Description: {match['description']}")
    if match.get('version'):
        lines.append(f"  Version: {match['version']}")
    if match.get('trustScore'):
        lines.append(f"  Trust Score: {match['trustScore']:.2f}")
    if match.get('stars'):
        lines.append(f"  Stars: {match['stars']:,}")
    if match.get('ecosystem'):
        lines.append(f"  Ecosystem: {match['ecosystem']}")
    return '\n'.join(lines)
