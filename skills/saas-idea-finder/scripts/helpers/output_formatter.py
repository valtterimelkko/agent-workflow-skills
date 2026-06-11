#!/usr/bin/env python3
"""Output formatting utilities for consistent JSON and markdown outputs."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def format_success_json(data: Any) -> Dict[str, Any]:
    """
    Format successful result as standardized JSON structure.

    Args:
        data: The result data to wrap

    Returns:
        Dictionary with success=True and data
    """
    return {
        "success": True,
        "data": data
    }


def format_error_json(error_type: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Format error result as standardized JSON structure.

    Args:
        error_type: Error category (e.g., 'api_error', 'credential_error')
        message: Human-readable error message
        details: Optional additional error context

    Returns:
        Dictionary with success=False, error type, and message
    """
    result = {
        "success": False,
        "error": error_type,
        "message": message
    }
    if details:
        result["details"] = details
    return result


def write_json_output(data: Dict[str, Any], filepath: str) -> None:
    """
    Write JSON data to file with atomic write and pretty formatting.

    Args:
        data: Dictionary to write as JSON
        filepath: Output file path
    """
    output_path = Path(filepath).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then rename (atomic operation)
    temp_path = output_path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    temp_path.replace(output_path)


def write_markdown_output(content: str, filepath: str, metadata: Optional[Dict] = None) -> None:
    """
    Write markdown content to file with optional YAML frontmatter.

    Args:
        content: Markdown content to write
        filepath: Output file path
        metadata: Optional frontmatter metadata (dict)
    """
    output_path = Path(filepath).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_content = content

    # Add YAML frontmatter if metadata provided
    if metadata:
        frontmatter_lines = ["---"]
        for key, value in metadata.items():
            if isinstance(value, str):
                frontmatter_lines.append(f"{key}: \"{value}\"")
            else:
                frontmatter_lines.append(f"{key}: {value}")
        frontmatter_lines.append("---\n")
        final_content = "\n".join(frontmatter_lines) + "\n" + content

    with open(output_path, 'w') as f:
        f.write(final_content)