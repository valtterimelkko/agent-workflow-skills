---
name: context7-search
description: Search for libraries in Context7. Use when the user mentions a library by name and you need to find its exact Context7 ID before fetching documentation.
---

# Search for Libraries in Context7

Search for libraries in the Context7 documentation database. This helps identify the correct `owner/repo` format needed for fetching documentation.

## When to Use

Use this skill when:
- User mentions a library by informal name (e.g., "next", "prisma", "mongo")
- You need to discover the exact library identifier
- User wants to compare multiple related libraries
- Library name is ambiguous or has multiple versions

**Skip this skill** when you already know the exact library (e.g., `vercel/next.js`). Use `context7-docs` directly instead.

## Prerequisites

Make `CONTEXT7_API_KEY` available either in the current environment or in a shell startup file such as `~/.bashrc`. The bundled scripts can read either form.

## How to Execute

### Basic Library Search

```bash
python3 ./scripts/resolve_library.py --query "LIBRARY_NAME"
```

### Limit Results

```bash
python3 ./scripts/resolve_library.py --query "LIBRARY_NAME" --limit 5
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--query` | Yes | - | Library name to search (fuzzy matching) |
| `--limit` | No | 10 | Maximum number of results |

## Example Queries

```bash
# Search for Next.js
python3 ./scripts/resolve_library.py --query "next.js"

# Search for Prisma
python3 ./scripts/resolve_library.py --query "prisma" --limit 5

# Search for MongoDB driver
python3 ./scripts/resolve_library.py --query "mongodb"
```

## Response Format

```json
{
  "success": true,
  "data": {
    "query": "next.js",
    "count": 3,
    "matches": [
      {
        "id": "/vercel/next.js",
        "title": "Next.js",
        "description": "React framework for full-stack web applications",
        "stars": 131745,
        "trustScore": 10,
        "versions": ["v15.1.8", "v14.3.0", "v13.5.11"]
      }
    ]
  }
}
```

## Selecting the Best Match

After getting results, select the best library based on:

1. **Trust score** - Higher is better (0-10 scale)
2. **Stars** - More stars indicates popularity
3. **Description relevance** - Match to user's specific needs
4. **VIP status** - VIP libraries are official/verified

## Common Library IDs

For frequently used libraries, you can skip search and use directly:

| Library | ID |
|---------|-------------|
| Next.js | `vercel/next.js` |
| React | `facebook/react` |
| Prisma | `prisma/prisma` |
| Supabase | `supabase/supabase` |
| FastAPI | `fastapi/fastapi` |
| Express | `expressjs/express` |
| Django | `django/django` |

## Workflow

```
1. User asks about a library (e.g., "How do I use Prisma?")
     |
2. Run context7-search to find library ID
     |
3. Select best match from results (e.g., prisma/prisma)
     |
4. Use context7-docs skill with the library ID
```

## Error Handling

**No matches found:**
- Try simpler search term (e.g., "next" instead of "next.js framework")
- Try the library's official name
- Check spelling

**API error:**
- Verify the API key is available in your environment or shell startup file
- Check network connectivity
