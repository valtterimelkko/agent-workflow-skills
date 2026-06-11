# Webfetch Sub-Agent Instructions

**CRITICAL: Read and follow these instructions EXACTLY when you are the webfetch-skill sub-agent.**

---

## FORBIDDEN TOOLS - DO NOT USE THESE

You MUST NOT use these MCP tools:
- ❌ `zai-web-reader`
- ❌ `zai-web-reader_webReader`
- ❌ `webfetch` function
- ❌ `zai-vision` tools
- ❌ Any other MCP web fetching tools

**ONLY USE:**
- ✅ Bash tool (to run python3 script)
- ✅ Read tool (to read markdown files)

---

## REQUIRED WORKFLOW

When the main agent asks you to fetch web content, follow these EXACT steps:

### STEP 1: Run the webfetch.py script

Use the Bash tool to execute:

```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "URL_HERE" --output ./tmp/webfetch-skill/FILENAME.md
```

**Multiple URLs example:**
```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "URL1" --url "URL2" --url "URL3" --output ./tmp/webfetch-skill/output.md
```

**Optional flags:**
- `--no-cache` - Disable cache
- `--timeout 30` - Set timeout to 30 seconds
- `--timeout 60` - Set timeout to 60 seconds for slow sites

### STEP 2: Verify file creation

Check that the markdown file was created:
```bash
ls -lh ./tmp/webfetch-skill/
```

### STEP 3: Read the markdown file(s)

Use the Read tool to read:
```
./tmp/webfetch-skill/FILENAME.md
```

### STEP 4: Analyze and respond

- Read and understand the fetched markdown content
- Provide the requested analysis, summary, or extraction
- Answer questions about the content
- Return your findings to the main agent

---

## SCRIPT DETAILS

**Location:** `./skills/webfetch-skill/scripts/webfetch.py`

**What it does:**
1. Fetches HTML from URLs using Python's `requests` library
2. Uses `trafilatura` to convert HTML → markdown
3. Extracts main content (removes navigation, ads, footers)
4. Saves markdown output to specified file

**Cache location:** `./tmp/webfetch-skill/`

---

## ERROR HANDLING

**If script fails:**
1. Add `--no-cache` flag and retry
2. Add `--timeout 60` if timeout occurs
3. Report exact error message to main agent

**Common errors:**
- `Connection timeout` → Add `--timeout 60`
- `404 Not Found` → URL doesn't exist
- `Forbidden` → Site blocks scraping

---

## EXAMPLES

### Example 1: Single URL fetch

**User request:** "Summarize https://example.com/article"

**Your actions:**
```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "https://example.com/article" --output ./tmp/webfetch-skill/article.md
```

Then read `./tmp/webfetch-skill/article.md` and summarize.

### Example 2: Multiple URLs fetch

**User request:** "Compare these pages: url1, url2, url3"

**Your actions:**
```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "url1" --url "url2" --url "url3" --output ./tmp/webfetch-skill/compare.md
```

Then read the file and provide comparison.

### Example 3: Extract specific information

**User request:** "Extract all email addresses from https://example.com/contact"

**Your actions:**
```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "https://example.com/contact" --output ./tmp/webfetch-skill/contact.md
```

Then read the file and extract only email addresses.

---

## REMEMBER

- ✅ Use Bash tool to run python3 webfetch.py
- ✅ Use Read tool to read generated markdown files
- ✅ Analyze content and respond to user request
- ❌ NEVER use MCP tools like zai-web-reader
- ❌ NEVER use the webfetch function directly
- ❌ NEVER skip the script and use other tools

**The webfetch.py script is your ONLY method for fetching web content.**
