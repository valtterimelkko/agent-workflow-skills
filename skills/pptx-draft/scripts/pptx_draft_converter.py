#!/usr/bin/env python3
"""
Bidirectional converter for PowerPoint presentations to/from structured markdown.

This script enables LLM-friendly editing workflows for .pptx files by:
1. Converting .pptx to structured markdown with precise markers
2. Preserving presentation structure for deterministic reverse conversion
3. Converting structured markdown back to .pptx with original formatting

Usage:
    # Convert to structured markdown
    python3 pptx_draft_converter.py --to-structured input.pptx [output.md]

    # Convert back to PowerPoint
    python3 pptx_draft_converter.py --to-pptx draft.md [output.pptx]
"""

import os
import sys
import hashlib
import json
from pathlib import Path
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN


class PptxToStructuredConverter:
    """Convert PowerPoint presentations to structured markdown."""

    def __init__(self, pptx_path):
        self.pptx_path = Path(pptx_path)
        self.prs = Presentation(str(pptx_path))
        self.prs_hash = self._compute_hash()

    def _compute_hash(self):
        """Compute SHA256 hash of the original presentation."""
        with open(self.pptx_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def convert(self):
        """Convert presentation to structured markdown."""
        lines = []

        # Metadata header
        lines.append("---")
        lines.append(f"PPTX_DRAFT_FORMAT: v1.0")
        lines.append(f"ORIGINAL_PPTX: {self.pptx_path.name}")
        lines.append(f"ORIGINAL_PATH: {self.pptx_path.absolute()}")
        lines.append(f"ORIGINAL_HASH: {self.prs_hash}")
        lines.append(f"CONVERSION_DATE: {datetime.now().isoformat()}")
        lines.append(f"TOTAL_SLIDES: {len(self.prs.slides)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.pptx_path.stem}")
        lines.append("")
        lines.append("**IMPORTANT**: Keep the original .pptx file in place until conversion back to PowerPoint is complete.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Extract slides
        for slide_idx, slide in enumerate(self.prs.slides):
            lines.extend(self._format_slide(slide, slide_idx))

        return "\n".join(lines)

    def _format_slide(self, slide, slide_idx):
        """Format a single slide with structure markers."""
        lines = []

        # Determine layout name
        layout_name = slide.slide_layout.name if slide.slide_layout else "Blank"

        lines.append(f"[SLIDE:{slide_idx}:layout={layout_name}]")
        lines.append("")

        # Extract text from shapes
        textbox_idx = 0
        table_idx = 0

        for shape_idx, shape in enumerate(slide.shapes):
            # Handle text frames (text boxes, titles, etc.)
            if hasattr(shape, "text_frame"):
                text_content = shape.text.strip()
                lines.append(f"[TEXTBOX:{textbox_idx}]")
                lines.append(text_content)
                lines.append(f"[/TEXTBOX:{textbox_idx}]")
                lines.append("")
                textbox_idx += 1

            # Handle tables
            elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                lines.extend(self._format_table(shape.table, table_idx))
                table_idx += 1

        lines.append(f"[/SLIDE:{slide_idx}]")
        lines.append("")

        return lines

    def _format_table(self, table, table_idx):
        """Format table with structure markers."""
        lines = [
            f"[TABLE:{table_idx}:rows={len(table.rows)}:cols={len(table.columns)}]",
            ""
        ]

        for row_idx, row in enumerate(table.rows):
            lines.append(f"[ROW:{row_idx}]")
            for col_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                lines.append(f"[CELL:{row_idx},{col_idx}]")
                lines.append(cell_text)
                lines.append(f"[/CELL:{row_idx},{col_idx}]")
            lines.append(f"[/ROW:{row_idx}]")
            lines.append("")

        lines.append(f"[/TABLE:{table_idx}]")
        lines.append("")

        return lines


class StructuredToPptxConverter:
    """Convert structured markdown back to PowerPoint presentation."""

    def __init__(self, md_path):
        self.md_path = Path(md_path)
        self.metadata = {}
        self.raw_content = ""
        self._parse_markdown()

    def _parse_markdown(self):
        """Parse structured markdown file."""
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract metadata
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                metadata_text = parts[1]
                for line in metadata_text.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        self.metadata[key.strip()] = value.strip()

                # Parse the structured content
                self.raw_content = parts[2]

    def verify_original(self):
        """Verify original presentation exists and matches hash."""
        if 'ORIGINAL_PATH' not in self.metadata:
            return False, "No original path in metadata"

        original_path = Path(self.metadata['ORIGINAL_PATH'])

        if not original_path.exists():
            return False, f"Original file not found at {original_path}"

        # Verify hash
        with open(original_path, 'rb') as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()

        expected_hash = self.metadata.get('ORIGINAL_HASH', '')
        if current_hash != expected_hash:
            return False, "Original file has been modified (hash mismatch)"

        return True, str(original_path)

    def convert(self, output_path=None):
        """Convert back to PowerPoint presentation."""
        # Verify original exists
        ok, result = self.verify_original()
        if not ok:
            raise ValueError(f"Cannot convert: {result}")

        original_path = result

        # Load original as template
        prs = Presentation(original_path)

        # Parse structured content
        slides_content = self._parse_structured_content()

        # Update presentation slides
        self._update_presentation(prs, slides_content)

        # Determine output path
        if output_path is None:
            output_path = self.md_path.parent / f"{self.md_path.stem.replace('_DRAFT', '')}_FINAL.pptx"

        # Save
        prs.save(str(output_path))

        return output_path

    def _parse_structured_content(self):
        """Parse structured markers and extract slide content."""
        slides = {}
        lines = self.raw_content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Parse slide
            if line.startswith('[SLIDE:'):
                parts = line.split(':')
                slide_idx = int(parts[1])
                layout_info = ":".join(parts[2:]).rstrip(']')

                textboxes = []
                tables = []
                i += 1

                while i < len(lines) and not lines[i].strip().startswith('[/SLIDE:'):
                    line = lines[i].strip()

                    # Parse textbox
                    if line.startswith('[TEXTBOX:'):
                        tb_idx = int(line.split(':')[1].rstrip(']'))
                        content_lines = []
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith('[/TEXTBOX:'):
                            content_lines.append(lines[i])
                            i += 1
                        textboxes.append({
                            'idx': tb_idx,
                            'text': '\n'.join(content_lines).strip()
                        })

                    # Parse table
                    elif line.startswith('[TABLE:'):
                        parts = line.split(':')
                        table_idx = int(parts[1])
                        table_info = {p.split('=')[0]: p.split('=')[1] for p in parts[2:] if '=' in p}
                        rows = []

                        i += 1
                        current_row = None

                        while i < len(lines) and not lines[i].strip().startswith('[/TABLE:'):
                            line = lines[i].strip()

                            if line.startswith('[ROW:'):
                                row_idx = int(line.split(':')[1].rstrip(']'))
                                current_row = []

                            elif line.startswith('[CELL:'):
                                coords = line.split(':')[1].rstrip(']')
                                cell_content = []
                                i += 1
                                while i < len(lines) and not lines[i].strip().startswith('[/CELL:'):
                                    cell_content.append(lines[i])
                                    i += 1
                                current_row.append('\n'.join(cell_content).strip())

                            elif line.startswith('[/ROW:') and current_row is not None:
                                rows.append(current_row)
                                current_row = None

                            i += 1

                        tables.append({
                            'idx': table_idx,
                            'rows': rows
                        })

                    i += 1

                slides[slide_idx] = {
                    'textboxes': textboxes,
                    'tables': tables
                }

            i += 1

        return slides

    def _update_presentation(self, prs, slides_content):
        """Update presentation with new content from structured markdown."""
        # Get the total number of slides we need
        max_slide_idx = max(slides_content.keys()) if slides_content else -1
        current_slide_count = len(prs.slides)

        # Determine which layout to use for new slides
        # Strategy: Use the most common content layout from existing slides
        layout_to_use = self._find_best_content_layout(prs)

        # Add new slides if needed
        if max_slide_idx >= current_slide_count:
            slides_to_add = max_slide_idx - current_slide_count + 1
            for _ in range(slides_to_add):
                prs.slides.add_slide(layout_to_use)

        # Update all slides (both existing and newly added)
        for slide_idx in sorted(slides_content.keys()):
            if slide_idx >= len(prs.slides):
                # Safety check - should not happen after adding slides above
                continue

            slide = prs.slides[slide_idx]
            slide_data = slides_content[slide_idx]

            self._update_slide_content(slide, slide_data)

    def _find_best_content_layout(self, prs):
        """Find the most appropriate layout for new content slides."""
        # Strategy: Look for layouts with names suggesting content
        # Priority order: "Title and Content", "Content", "Two Content", "Blank"

        preferred_names = [
            "Title and Content",
            "Main headings, text and bullet points",
            "Content",
            "Two Content",
            "Blank"
        ]

        # Try to find a preferred layout
        for name in preferred_names:
            for layout in prs.slide_layouts:
                if layout.name == name:
                    return layout

        # Fallback: use the most common layout from existing slides (excluding title slide)
        layout_counts = {}
        for slide in prs.slides:
            layout_name = slide.slide_layout.name
            if layout_name != "Title Slide":
                layout_counts[layout_name] = layout_counts.get(layout_name, 0) + 1

        if layout_counts:
            most_common_layout_name = max(layout_counts, key=layout_counts.get)
            for layout in prs.slide_layouts:
                if layout.name == most_common_layout_name:
                    return layout

        # Last resort: use first non-title layout
        for layout in prs.slide_layouts:
            if layout.name != "Title Slide":
                return layout

        # Absolute last resort: use any layout
        return prs.slide_layouts[0]

    def _update_slide_content(self, slide, slide_data):
        """Update a single slide's content."""
        textbox_idx = 0
        table_idx = 0

        for shape in slide.shapes:
            # Update text frames
            if hasattr(shape, "text_frame") and textbox_idx < len(slide_data['textboxes']):
                new_text = slide_data['textboxes'][textbox_idx]['text']
                # Clear existing text
                text_frame = shape.text_frame
                text_frame.clear()
                # Add new text
                if new_text:
                    p = text_frame.paragraphs[0]
                    p.text = new_text
                textbox_idx += 1

            # Update tables
            elif shape.shape_type == MSO_SHAPE_TYPE.TABLE and table_idx < len(slide_data['tables']):
                table = shape.table
                table_data = slide_data['tables'][table_idx]
                new_rows = table_data['rows']

                for row_idx, row in enumerate(table.rows):
                    if row_idx < len(new_rows):
                        for col_idx, cell in enumerate(row.cells):
                            if col_idx < len(new_rows[row_idx]):
                                cell.text = new_rows[row_idx][col_idx]

                table_idx += 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Bidirectional converter for PowerPoint presentations and structured markdown'
    )
    parser.add_argument('--to-structured', action='store_true',
                       help='Convert .pptx to structured markdown')
    parser.add_argument('--to-pptx', action='store_true',
                       help='Convert structured markdown to .pptx')
    parser.add_argument('input', help='Input file path')
    parser.add_argument('output', nargs='?', help='Output file path (optional)')

    args = parser.parse_args()

    if args.to_structured:
        # Convert pptx to markdown
        converter = PptxToStructuredConverter(args.input)
        markdown = converter.convert()

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(args.input).parent / f"{Path(args.input).stem}_DRAFT.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"✓ Converted to structured markdown: {output_path}")
        print(f"⚠️  Keep original file in place: {Path(args.input).absolute()}")

    elif args.to_pptx:
        # Convert markdown to pptx
        converter = StructuredToPptxConverter(args.input)
        output_path = converter.convert(args.output)

        print(f"✓ Converted to PowerPoint: {output_path}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
