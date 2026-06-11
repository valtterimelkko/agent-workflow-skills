---
name: docx-draft
description: "Convert Word documents to structured markdown for LLM-assisted editing, then convert back to Word with preserved formatting. Make sure to use this whenever the user wants to work on, revise, draft, fill in, or collaboratively edit a .docx and then produce a final .docx again. Prefer this over markitdown or docx-to-markdown whenever round-trip editing fidelity matters."
tags: [document, word, docx, conversion, editing, drafting]
version: 1.0.0
---

# Word Document Drafting Skill

Convert Microsoft Word documents (.docx) to structured markdown for easy editing with LLM assistance, then convert back to Word format with all formatting preserved.

## When to Use This Skill

Use this skill when:
- User asks to work on, edit, or draft a Word document
- User wants to convert a .docx file to a more editable format
- User wants to prepare a final .docx from a draft markdown
- User mentions: "work on this docx", "edit this Word file", "draft this document"

## How It Works

### Phase 1: Convert to Structured Markdown
Converts a .docx file into a structured markdown file with special markers that preserve the exact structure of the original document.

### Phase 2: Edit the Draft
You (Claude Code) can now edit the structured markdown file. The structure markers ensure the content maps back perfectly to the Word template.

### Phase 3: Convert Back to Word
Converts the edited structured markdown back to a .docx file, using the original as a template to preserve all formatting.

## Usage

### Converting TO Structured Markdown

When user says:
- "Convert [file.docx] to draft format"
- "Use docx-draft on [file.docx]"
- "I want to work on this Word document"
- "Convert PDR_Form.docx to markdown"

**Steps:**
1. Locate the .docx file
2. Run the converter script:
   ```bash
   python3 ./scripts/docx_draft_converter.py --to-structured <input.docx> [output.md]
   ```
3. Inform user:
   - Where the draft file was created
   - **CRITICAL**: Remind them to keep the original .docx file in its current location
   - Explain they can now edit the draft

**Example:**
```bash
python3 ./scripts/docx_draft_converter.py --to-structured ~/pdr/PDR_Form_Jan2026.docx
```

Output: `~/pdr/PDR_Form_Jan2026_DRAFT.md`

### Converting BACK to Word

When user says:
- "Convert the draft back to Word"
- "I'm done editing, create the final Word document"
- "Convert [file_DRAFT.md] to docx"
- "Finalize this document"

**Steps:**
1. Locate the structured markdown file (usually ends with `_DRAFT.md`)
2. Run the converter script:
   ```bash
   python3 ./scripts/docx_draft_converter.py --to-docx <draft.md> [output.docx]
   ```
3. The script will:
   - Check that the original .docx exists (from metadata)
   - Verify it hasn't been modified
   - Use it as a template
   - Fill in the edited content
   - Create a new `_FINAL.docx` file
4. Inform user of success and location of final file

**Example:**
```bash
python3 ./scripts/docx_draft_converter.py --to-docx ~/pdr/PDR_Form_Jan2026_DRAFT.md
```

Output: `~/pdr/PDR_Form_Jan2026_FINAL.docx`

## Structure Markers

The structured markdown uses special markers that you MUST preserve:

### Metadata Block (at top of file)
```markdown
---
DOCX_DRAFT_FORMAT: v1.0
ORIGINAL_DOCX: filename.docx
ORIGINAL_PATH: /full/path/to/filename.docx
ORIGINAL_HASH: abc123...
CONVERSION_DATE: 2026-01-19T12:00:00
---
```

**DO NOT MODIFY** the metadata block. The conversion process depends on it.

### Paragraph Markers
```markdown
[PARA:0]
This is the content of a paragraph.
[/PARA:0]
```

**Editing rules:**
- Keep the markers intact: `[PARA:N]` and `[/PARA:N]`
- Edit the content between the markers
- Don't change the numbers

### Table Markers
```markdown
[TABLE:5:rows=4:cols=3]

[ROW:0]
[CELL:0,0]
Header 1
[/CELL:0,0]
[CELL:0,1]
Header 2
[/CELL:0,1]
[CELL:0,2]
Header 3
[/CELL:0,2]
[/ROW:0]

[ROW:1]
[CELL:1,0]
Data in row 1, column 1
[/CELL:1,0]
[CELL:1,1]
Data in row 1, column 2
[/CELL:1,1]
[CELL:1,2]
Data in row 1, column 3
[/CELL:1,2]
[/ROW:1]

[/TABLE:5]
```

**Editing rules:**
- Keep all markers intact: `[TABLE:N]`, `[ROW:N]`, `[CELL:r,c]`, closing tags
- Edit content between `[CELL:r,c]` and `[/CELL:r,c]`
- Maintain table structure (same number of rows and columns)
- Don't change the numbers in markers

## Critical Rules for Editing

When editing a structured markdown file:

1. **Never modify structure markers** - Only edit content between markers
2. **Preserve metadata** - Don't touch the YAML header at the top
3. **Maintain table structure** - Keep the same number of rows/columns
4. **Respect element order** - Don't reorder `[PARA]` or `[TABLE]` blocks
5. **Keep markers paired** - Every `[PARA:N]` needs its `[/PARA:N]`

## Error Handling

### If Original File is Missing

If the original .docx is not found during back-conversion:

```
Error: Original file not found at /path/to/original.docx
```

**Response:**
1. Ask user: "Where is the original .docx file?"
2. If they can provide it, update the `ORIGINAL_PATH` in metadata
3. If not available, inform them formatting may be lost

### If Original File Was Modified

If the hash doesn't match:

```
Error: Original file has been modified (hash mismatch)
```

**Response:**
Warn the user that the original template was changed. Ask if they want to:
- Proceed anyway (formatting might differ)
- Locate the original unmodified file

## Example Workflow

**Initial request:**
> User: "I need to work on Quarterly_Review_Form_Jan2026.docx"

**Your response:**
```
I'll convert Quarterly_Review_Form_Jan2026.docx to a structured draft format so we can work on it together.

[Run conversion command]

✓ Created Quarterly_Review_Form_Jan2026_DRAFT.md

⚠️ Important: Keep the original Quarterly_Review_Form_Jan2026.docx file in its current location.
You'll need it to convert back to Word format when you're done.

You can now tell me what sections you'd like to work on, and I'll help you draft the content.
```

**During editing:**
> User: "Fill in the Part 1 section with my achievements"

**Your response:**
```
I'll edit the Part 1 section in the structured draft. I'll make sure to keep all the structure
markers intact while updating the content.

[Edit content between appropriate markers]

Done! The Part 1 section now includes your achievements. Would you like to work on another section?
```

**Finalization:**
> User: "I'm happy with the draft. Convert it back to Word."

**Your response:**
```
I'll convert your draft back to Word format now.

[Run back-conversion command]

✓ Created Quarterly_Review_Form_Jan2026_FINAL.docx

Your final Word document is ready! All formatting from the original template has been preserved.
```

## Technical Notes

- Script location: `./scripts/docx_draft_converter.py`
- Requires `python-docx` library
- Preserves: paragraph styles, table structures, document sections
- Does not preserve: images, complex formatting, embedded objects
- Best for: forms, templates, text-heavy documents

## Tips

1. **Always inform users** about keeping the original file in place
2. **Use Read tool** to examine structure markers before editing
3. **Edit systematically** - work section by section
4. **Validate structure** after editing if user made manual changes
5. **Be explicit** when content is complete and ready for conversion

## Common Patterns

### Working on a section
```
1. Read the draft file to locate the section
2. Find the relevant [PARA] or [TABLE] markers
3. Edit content within markers
4. Confirm changes with user
```

### Multi-turn editing
```
1. User provides content for section A → Edit [PARA:X]
2. User provides content for section B → Edit [PARA:Y]
3. User reviews → Make adjustments
4. User approves → Convert back to Word
```

### Table filling
```
1. Identify table by [TABLE:N] marker
2. Locate specific cells by [CELL:row,col]
3. Fill in cell content
4. Maintain all cell markers
```

---

This skill enables efficient collaborative document drafting while maintaining perfect fidelity to the original Word document format.
