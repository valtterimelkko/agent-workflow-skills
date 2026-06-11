---
name: context7-docs
description: Fetch up-to-date documentation from Context7 for a library. Use when you need current API syntax, code examples, or official documentation for any library or framework.
---

# Fetch Library Documentation from Context7

Fetch real-time, version-specific documentation and code examples for libraries.

## When to Use

Use this skill when:
- User needs current API documentation for a library
- You need up-to-date syntax examples (your training data may be outdated)
- User asks "show me how to use X" or "what's the latest syntax for Y"
- Implementing features with a specific library
- Troubleshooting library usage issues

## Prerequisites

1. **Context7 API key** available via `CONTEXT7_API_KEY` in the environment or a shell startup file such as `~/.bashrc` (the bundled scripts can read either)
2. **Library ID** in `owner/repo` format (use `context7-search` first if unknown)

## How to Execute

### Fetch Code Examples (Default)

```bash
python3 ./scripts/fetch_docs.py --library "owner/repo"
```

### Fetch Topic-Focused Documentation

```bash
python3 ./scripts/fetch_docs.py --library "owner/repo" --topic "TOPIC"
```

### Fetch Documentation Info (Instead of Code)

```bash
python3 ./scripts/fetch_docs.py --library "owner/repo" --type info
```

### Fetch Specific Version

```bash
python3 ./scripts/fetch_docs.py --library "owner/repo" --version "v15.1.8"
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--library` | Yes | - | Library in `owner/repo` format |
| `--topic` | No | - | Focus on specific feature/topic |
| `--type` | No | code | `code` for snippets, `info` for docs |
| `--version` | No | latest | Specific version tag |
| `--page` | No | 1 | Page number for pagination |

## Examples

### Fetch Next.js Routing Examples

```bash
python3 ./scripts/fetch_docs.py \
  --library "vercel/next.js" \
  --topic "routing"
```

### Fetch Prisma PostgreSQL Setup

```bash
python3 ./scripts/fetch_docs.py \
  --library "prisma/prisma" \
  --topic "postgresql connection"
```

### Fetch React Hooks Documentation

```bash
python3 ./scripts/fetch_docs.py \
  --library "facebook/react" \
  --topic "hooks" \
  --type info
```

### Fetch Specific Version

```bash
python3 ./scripts/fetch_docs.py \
  --library "vercel/next.js" \
  --version "v14.3.0" \
  --topic "app router"
```

## Response Format

```json
{
  "success": true,
  "data": {
    "library": "vercel/next.js",
    "topic": "routing",
    "type": "code",
    "content": {
      "content": "### Dynamic Route Handler\n\nSource: ...\n\n```typescript\nexport async function GET(...) {...}\n```\n\n---\n\n### Another Example\n..."
    }
  }
}
```

## Common Library IDs

| Library | ID | Common Topics |
|---------|-------------|---------------|
| Next.js | `vercel/next.js` | routing, server components, api routes |
| React | `facebook/react` | hooks, state, context, suspense |
| Prisma | `prisma/prisma` | setup, queries, relations, migrations |
| Supabase | `supabase/supabase` | auth, realtime, row level security |
| FastAPI | `fastapi/fastapi` | routing, validation, dependencies |
| Express | `expressjs/express` | middleware, routing, error handling |
| Tailwind | `tailwindlabs/tailwindcss` | configuration, utilities, plugins |

## Workflow Examples

### Example 1: Unknown Library

```
User: "How do I set up authentication with Supabase?"

1. Search for library (if ID unknown):
   python3 ./scripts/resolve_library.py --query "supabase"
   → Returns supabase/supabase

2. Fetch focused documentation:
   python3 ./scripts/fetch_docs.py \
     --library "supabase/supabase" \
     --topic "authentication"
```

### Example 2: Known Library

```
User: "Show me the latest Next.js routing API"

Fetch directly (skip search):
   python3 ./scripts/fetch_docs.py \
     --library "vercel/next.js" \
     --topic "app router"
```

## Error Handling

**Library not found (404):**
- Use `context7-search` to find the correct library ID
- Format must be `owner/repo` (e.g., `vercel/next.js`)

**Topic not matched:**
- Try broader topic keywords
- Omit topic entirely to get general documentation

**Authentication error:**
- Verify CONTEXT7_API_KEY is available in your environment or shell startup file
- Check key is valid

## Best Practices

1. **Use specific topics** - Get focused results with `--topic`
2. **Try code first** - Default `--type code` gives practical examples
3. **Use info for concepts** - `--type info` for documentation/explanations
4. **Check versions** - Use `--version` for version-specific syntax
