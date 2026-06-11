#!/usr/bin/env python3
"""
Bidirectional converter for Word documents to/from structured markdown.

This script enables LLM-friendly editing workflows for .docx files by:
1. Converting .docx to structured markdown with precise markers
2. Preserving document structure for deterministic reverse conversion
3. Converting structured markdown back to .docx with original formatting

Usage:
    # Convert to structured markdown
    python3 docx_draft_converter.py --to-structured input.docx [output.md]

    # Convert back to Word
    python3 docx_draft_converter.py --to-docx draft.md [output.docx]
"""

import os
import sys
import hashlib
import json
from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


class DocxToStructuredConverter:
    """Convert Word documents to structured markdown."""

    def __init__(self, docx_path):
        self.docx_path = Path(docx_path)
        self.doc = Document(str(docx_path))
        self.doc_hash = self._compute_hash()

    def _compute_hash(self):
        """Compute SHA256 hash of the original document."""
        with open(self.docx_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def convert(self):
        """Convert document to structured markdown."""
        lines = []

        # Metadata header
        lines.append("---")
        lines.append(f"DOCX_DRAFT_FORMAT: v1.0")
        lines.append(f"ORIGINAL_DOCX: {self.docx_path.name}")
        lines.append(f"ORIGINAL_PATH: {self.docx_path.absolute()}")
        lines.append(f"ORIGINAL_HASH: {self.doc_hash}")
        lines.append(f"CONVERSION_DATE: {datetime.now().isoformat()}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.docx_path.stem}")
        lines.append("")
        lines.append("**IMPORTANT**: Keep the original .docx file in place until conversion back to Word is complete.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Extract content with structure markers
        element_idx = 0
        para_idx = 0
        table_idx = 0

        for element in self.doc.element.body:
            if element.tag.endswith('p'):  # Paragraph
                para = self.doc.paragraphs[para_idx]
                if para.text.strip():
                    lines.append(f"[PARA:{element_idx}]")
                    lines.append(para.text)
                    lines.append(f"[/PARA:{element_idx}]")
                    lines.append("")
                    element_idx += 1
                para_idx += 1

            elif element.tag.endswith('tbl'):  # Table
                table = self.doc.tables[table_idx]
                lines.extend(self._format_table(table, table_idx, element_idx))
                element_idx += 1
                table_idx += 1

        return "\n".join(lines)

    def _format_table(self, table, table_idx, element_idx):
        """Format table with structure markers."""
        lines = [
            f"[TABLE:{element_idx}:rows={len(table.rows)}:cols={len(table.columns)}]",
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

        lines.append(f"[/TABLE:{element_idx}]")
        lines.append("")

        return lines


class StructuredToDocxConverter:
    """Convert structured markdown back to Word document."""

    def __init__(self, md_path):
        self.md_path = Path(md_path)
        self.metadata = {}
        self.content = []
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
        """Verify original document exists and matches hash."""
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
        """Convert back to Word document."""
        # Verify original exists
        ok, result = self.verify_original()
        if not ok:
            raise ValueError(f"Cannot convert: {result}")

        original_path = result

        # Load original as template
        doc = Document(original_path)

        # Parse structured content and map to elements
        elements = self._parse_structured_content()

        # Update document elements
        self._update_document(doc, elements)

        # Determine output path
        if output_path is None:
            output_path = self.md_path.parent / f"{self.md_path.stem.replace('_DRAFT', '')}_FINAL.docx"

        # Save
        doc.save(str(output_path))

        return output_path

    def _parse_structured_content(self):
        """Parse structured markers and extract content."""
        elements = []
        lines = self.raw_content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Parse paragraph
            if line.startswith('[PARA:'):
                element_idx = int(line.split(':')[1].rstrip(']'))
                content_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('[/PARA:'):
                    content_lines.append(lines[i])
                    i += 1
                elements.append({
                    'type': 'paragraph',
                    'idx': element_idx,
                    'text': '\n'.join(content_lines).strip()
                })

            # Parse table
            elif line.startswith('[TABLE:'):
                parts = line.split(':')
                element_idx = int(parts[1])
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

                elements.append({
                    'type': 'table',
                    'idx': element_idx,
                    'rows': rows
                })

            i += 1

        return elements

    def _update_document(self, doc, elements):
        """Update document with new content from structured markdown."""
        element_idx = 0
        para_idx = 0
        table_idx = 0

        for element in doc.element.body:
            if element.tag.endswith('p'):  # Paragraph
                para = doc.paragraphs[para_idx]
                if para.text.strip():
                    # Find matching element
                    matching = [e for e in elements if e['type'] == 'paragraph' and e['idx'] == element_idx]
                    if matching:
                        para.text = matching[0]['text']
                    element_idx += 1
                para_idx += 1

            elif element.tag.endswith('tbl'):  # Table
                table = doc.tables[table_idx]
                # Find matching element
                matching = [e for e in elements if e['type'] == 'table' and e['idx'] == element_idx]
                if matching:
                    new_rows = matching[0]['rows']
                    for row_idx, row in enumerate(table.rows):
                        if row_idx < len(new_rows):
                            for col_idx, cell in enumerate(row.cells):
                                if col_idx < len(new_rows[row_idx]):
                                    cell.text = new_rows[row_idx][col_idx]
                element_idx += 1
                table_idx += 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Bidirectional converter for Word documents and structured markdown'
    )
    parser.add_argument('--to-structured', action='store_true',
                       help='Convert .docx to structured markdown')
    parser.add_argument('--to-docx', action='store_true',
                       help='Convert structured markdown to .docx')
    parser.add_argument('input', help='Input file path')
    parser.add_argument('output', nargs='?', help='Output file path (optional)')

    args = parser.parse_args()

    if args.to_structured:
        # Convert docx to markdown
        converter = DocxToStructuredConverter(args.input)
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

    elif args.to_docx:
        # Convert markdown to docx
        converter = StructuredToDocxConverter(args.input)
        output_path = converter.convert(args.output)

        print(f"✓ Converted to Word document: {output_path}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
