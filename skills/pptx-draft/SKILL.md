---
name: pptx-draft
description: Convert PowerPoint presentations to structured markdown for LLM-assisted editing, then convert back to PowerPoint with preserved formatting and layout. Use when you need to draft, edit, or work on .pptx files interactively.
tags: [document, powerpoint, pptx, conversion, editing, drafting, presentation]
version: 1.0.0
---

# PowerPoint Presentation Drafting Skill

Convert Microsoft PowerPoint presentations (.pptx) to structured markdown for easy editing with LLM assistance, then convert back to PowerPoint format with all formatting, layout, and graphics preserved.

## When to Use This Skill

Use this skill when:
- User asks to work on, edit, or draft a PowerPoint presentation
- User wants to convert a .pptx file to a more editable format
- User wants to prepare a final .pptx from a draft markdown
- User mentions: "work on this PowerPoint", "edit this presentation", "draft these slides"

## How It Works

### Phase 1: Convert to Structured Markdown
Converts a .pptx file into a structured markdown file with special markers that preserve the exact structure of the original presentation, including slide layouts, text boxes, tables, and graphics.

### Phase 2: Edit the Draft
You (Claude Code) can now edit the structured markdown file. The structure markers ensure the content maps back perfectly to the PowerPoint template.

### Phase 3: Convert Back to PowerPoint
Converts the edited structured markdown back to a .pptx file, using the original as a template to preserve all formatting, layout, and graphics.

## Usage

### Converting TO Structured Markdown

When user says:
- "Convert [file.pptx] to draft format"
- "Use pptx-draft on [file.pptx]"
- "I want to work on this PowerPoint"
- "Convert presentation.pptx to markdown"

**Steps:**
1. Locate the .pptx file
2. Run the converter script:
   ```bash
   python3 skills-global/pptx-draft/scripts/pptx_draft_converter.py --to-structured <input.pptx> [output.md]
   ```
3. Inform user:
   - Where the draft file was created
   - **CRITICAL**: Remind them to keep the original .pptx file in its current location
   - Explain they can now edit the draft
   - Note: Empty slides will appear as blank placeholder slides in the markdown structure

**Example:**
```bash
python3 skills-global/pptx-draft/scripts/pptx_draft_converter.py --to-structured ~/presentations/Q1_Review.pptx
```

Output: `~/presentations/Q1_Review_DRAFT.md`

### Converting BACK to PowerPoint

When user says:
- "Convert the draft back to PowerPoint"
- "I'm done editing, create the final PowerPoint"
- "Convert [file_DRAFT.md] to pptx"
- "Finalize this presentation"

**Steps:**
1. Locate the structured markdown file (usually ends with `_DRAFT.md`)
2. Run the converter script:
   ```bash
   python3 skills-global/pptx-draft/scripts/pptx_draft_converter.py --to-pptx <draft.md> [output.pptx]
   ```
3. The script will:
   - Check that the original .pptx exists (from metadata)
   - Verify it hasn't been modified
   - Use it as a template
   - Fill in the edited content
   - Create a new `_FINAL.pptx` file
4. Inform user of success and location of final file

**Example:**
```bash
python3 skills-global/pptx-draft/scripts/pptx_draft_converter.py --to-pptx ~/presentations/Q1_Review_DRAFT.md
```

Output: `~/presentations/Q1_Review_FINAL.pptx`

## Structure Markers

The structured markdown uses special markers that you MUST preserve:

### Metadata Block (at top of file)
```markdown
---
PPTX_DRAFT_FORMAT: v1.0
ORIGINAL_PPTX: filename.pptx
ORIGINAL_PATH: /full/path/to/filename.pptx
ORIGINAL_HASH: abc123...
CONVERSION_DATE: 2026-01-19T12:00:00
TOTAL_SLIDES: 5
---
```

**DO NOT MODIFY** the metadata block. The conversion process depends on it.

### Slide Markers
```markdown
[SLIDE:0:layout=Title Slide]

[TEXTBOX:0]
This is the title
[/TEXTBOX:0]

[TEXTBOX:1]
This is the subtitle
[/TEXTBOX:1]

[/SLIDE:0]
```

**Editing rules:**
- Keep the markers intact: `[SLIDE:N]` and `[/SLIDE:N]`
- Edit the content between `[TEXTBOX:M]` and `[/TEXTBOX:M]` markers
- Don't change the numbers in markers
- Don't remove or add `[TEXTBOX]` blocks—only edit content within them
- Preserve slide order

### Table Markers Within Slides
```markdown
[SLIDE:2:layout=Title and Content]

[TEXTBOX:0]
Slide Title
[/TEXTBOX:0]

[TABLE:0:rows=3:cols=2]

[ROW:0]
[CELL:0,0]
Header 1
[/CELL:0,0]
[CELL:0,1]
Header 2
[/CELL:0,1]
[/ROW:0]

[ROW:1]
[CELL:1,0]
Data in row 1, column 1
[/CELL:1,0]
[CELL:1,1]
Data in row 1, column 2
[/CELL:1,1]
[/ROW:1]

[/TABLE:0]

[/SLIDE:2]
```

**Editing rules:**
- Keep all markers intact: `[TABLE:N]`, `[ROW:N]`, `[CELL:r,c]`, closing tags
- Edit content between `[CELL:r,c]` and `[/CELL:r,c]`
- Maintain table structure (same number of rows and columns)
- Don't change the numbers in markers

### Adding New Slides

To add a new slide to the markdown draft:

1. **Duplicate an existing slide block** - Copy a `[SLIDE]...[/SLIDE]` block
2. **Update the slide number** - Change `[SLIDE:N]` to the next number (e.g., if last is `[SLIDE:4]`, new one is `[SLIDE:5]`)
3. **Clear the content** - Empty out all `[TEXTBOX]` content between the markers:
   ```markdown
   [SLIDE:5:layout=Title and Content]

   [TEXTBOX:0]

   [/TEXTBOX:0]

   [TEXTBOX:1]

   [/TEXTBOX:1]

   [/SLIDE:5]
   ```
4. **Update metadata** - Change `TOTAL_SLIDES` in the metadata block to the new total
5. **Fill in content** - Add your text between the textbox markers

**Example of adding a new slide:**

Original structure:
```markdown
---
TOTAL_SLIDES: 3
---
...
[SLIDE:2:layout=Title and Content]
[TEXTBOX:0]
Final Slide
[/TEXTBOX:0]
[/SLIDE:2]
```

After adding new slide:
```markdown
---
TOTAL_SLIDES: 4
---
...
[SLIDE:2:layout=Title and Content]
[TEXTBOX:0]
Final Slide
[/TEXTBOX:0]
[/SLIDE:2]

[SLIDE:3:layout=Title and Content]
[TEXTBOX:0]
New Slide Title
[/TEXTBOX:0]
[TEXTBOX:1]
New content goes here
[/TEXTBOX:1]
[/SLIDE:3]
```

## Critical Rules for Editing

When editing a structured markdown file:

1. **Never modify structure markers** - Only edit content between markers
2. **Preserve metadata** - Don't touch the YAML header at the top
3. **Maintain slide structure** - Keep all textbox blocks in place
4. **Respect element order** - Don't reorder `[SLIDE]` blocks
5. **Keep markers paired** - Every `[SLIDE:N]` needs its `[/SLIDE:N]`
6. **Update TOTAL_SLIDES** - When adding/removing slides, update the count in metadata
7. **Don't add empty slides** - The original template's layout is preserved; empty slides represent blank placeholders

## Error Handling

### If Original File is Missing

If the original .pptx is not found during back-conversion:

```
Error: Original file not found at /path/to/original.pptx
```

**Response:**
1. Ask user: "Where is the original .pptx file?"
2. If they can provide it, update the `ORIGINAL_PATH` in metadata
3. If not available, inform them formatting and layout may be lost

### If Original File Was Modified

If the hash doesn't match:

```
Error: Original file has been modified (hash mismatch)
```

**Response:**
Warn the user that the original template was changed. Ask if they want to:
- Proceed anyway (formatting might differ)
- Locate the original unmodified file

### If Slide Count Doesn't Match

If the number of slides in the markdown doesn't match the metadata:

```
Warning: Slide count mismatch (metadata says 5, found 7)
```

**Response:**
Verify with user that they intended to add slides. Update `TOTAL_SLIDES` in metadata if needed.

## Example Workflow

**Initial request:**
> User: "I need to work on Q1_Review.pptx"

**Your response:**
```
I'll convert Q1_Review.pptx to a structured draft format so we can work on it together.

[Run conversion command]

✓ Created Q1_Review_DRAFT.md

⚠️ Important: Keep the original Q1_Review.pptx file in its current location.
You'll need it to convert back to PowerPoint format when you're done.

You can now tell me what slides you'd like to work on, and I'll help you draft the content.
The presentation has 5 slides. You can edit text on any slide, or add new slides by following the
markdown structure (I can help with this).
```

**During editing:**
> User: "Update slide 1 with new title and subtitle"

**Your response:**
```
I'll edit slide 1 in the structured draft. I'll make sure to keep all the structure
markers intact while updating the content.

[Edit content between appropriate markers]

Done! Slide 1 now has the new title and subtitle. Would you like to work on another slide?
```

**Adding slides:**
> User: "Add two new slides at the end"

**Your response:**
```
I'll add two new blank slides to the end of the presentation and update the metadata.

[Add new slide blocks to markdown]

Done! I've added slides 6 and 7 to your presentation. They're currently blank and ready for content.
You can tell me what to add to each new slide, and I'll fill them in.
```

**Finalization:**
> User: "I'm happy with the draft. Convert it back to PowerPoint."

**Your response:**
```
I'll convert your draft back to PowerPoint format now.

[Run back-conversion command]

✓ Created Q1_Review_FINAL.pptx

Your final PowerPoint is ready! All formatting and layout from the original template have been preserved.
```

## Validation Tool

After converting back to PowerPoint, you can optionally validate the conversion quality:

```bash
python3 skills-global/pptx-draft/scripts/pptx_draft_validator.py <original.pptx> <final.pptx> [--verbose]
```

The validator checks:
- Slide count (original vs final)
- Layout preservation
- Content structure (textboxes, tables)
- Visual elements (images, shapes)
- Potential issues like content cramming

**When to use the validator:**
- After adding new slides to verify they were created
- When content seems off or cramped
- To verify complex conversions with tables or heavy content
- When troubleshooting conversion issues

## Technical Notes

-- Converter script: `skills-global/pptx-draft/scripts/pptx_draft_converter.py`
-- Validator script: `skills-global/pptx-draft/scripts/pptx_draft_validator.py`
- Requires `python-pptx` library
- Preserves: slide layouts, text formatting, table structures, graphics, images
- Does not preserve: animations, transitions, speaker notes (unless included in text boxes)
- Best for: text-based edits, content updates, adding/removing slides
- Slide order is deterministic and must be maintained in the markdown
- New slides automatically use the most appropriate content layout from the original presentation

## Tips

1. **Always inform users** about keeping the original file in place
2. **Use Read tool** to examine structure markers before editing
3. **Edit systematically** - work slide by slide
4. **Validate structure** after editing if user made manual changes
5. **Be explicit** when content is complete and ready for conversion
6. **Plan slide additions** - discuss layout and content before adding new slides
7. **Preserve blank slides** - they're part of the template structure; don't delete them unless instructed

## Common Patterns

### Working on a slide
```
1. Read the draft file to locate the slide
2. Find the relevant [SLIDE:N] section
3. Edit content within [TEXTBOX] markers
4. Confirm changes with user
```

### Multi-turn editing
```
1. User provides content for slide 1 → Edit [SLIDE:0]
2. User provides content for slide 2 → Edit [SLIDE:1]
3. User reviews all slides → Make adjustments
4. User approves → Convert back to PowerPoint
```

### Adding multiple slides
```
1. Determine new slide count and layout
2. Add new [SLIDE] blocks with sequential numbering
3. Update TOTAL_SLIDES in metadata
4. Fill in content as user provides it
```

### Table editing
```
1. Locate slide containing [TABLE:N]
2. Find specific cells by [CELL:row,col]
3. Fill in cell content
4. Maintain all cell markers and row/column count
```

---

This skill enables efficient collaborative presentation editing whilst maintaining perfect fidelity to the original PowerPoint presentation format and layout.
