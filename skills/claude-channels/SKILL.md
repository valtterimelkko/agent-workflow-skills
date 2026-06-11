---
name: claude-channels
description: "Build MCP channel plugins that push external events into a running Claude Code interactive session and bridge bidirectional communication. Use when: building a custom channel plugin for Claude Code, bridging Claude Code to a web UI or chat platform, understanding the channels protocol (notification format, reply tools, sender gating, permission relay), integrating Claude Code with external systems via WebSocket or HTTP, replacing claude -p with interactive Claude Code for better subscription quota, wrapping Claude Code in a custom interface, or working with @modelcontextprotocol/sdk for Claude Code channel plugins. ALWAYS use when the user mentions Claude Code channels, --channels, channel plugins, channel reference, push events into Claude Code, Claude Code WebSocket bridge, or wants to connect an external app to a live Claude Code session."
---

# Claude Code Channels

> **Source:** This skill is based on the official [Channels reference](https://code.claude.com/docs/en/channels-reference) from Anthropic's Claude Code documentation. Always consult it for the latest protocol details.

Build channel plugins that push webhooks, alerts, chat messages, and external events into a running Claude Code session. Channels are MCP server plugins that bridge external systems into Claude Code's interactive agent loop — the same session you'd normally use from the terminal.

## Why Channels Matter

Channels solve a specific problem: you want Claude Code to react to things happening outside the terminal while preserving its context, tools, and agent loop. Unlike `claude -p` (which starts a fresh one-shot subprocess per prompt), channels push events into a **long-lived interactive Claude Code session** that maintains working memory, MCP tools, and accumulated knowledge across messages.

The other major motivation is **quota economics**. Starting June 15, 2026, Anthropic separated quotas:

| Path | Quota pool | Limit |
|------|-----------|-------|
| **Interactive** Claude Code (terminal, channels, Remote Control, Claude Cowork) | Main subscription quota | Generous |
| Agent SDK + `claude -p` | $20/month SDK credit | Limited |

Channels use the **main subscription quota** because they run inside an interactive session.

## Architecture

A channel is an MCP server that Claude Code spawns as a subprocess over stdio. It also runs a network listener (WebSocket or HTTP) for external applications:

```
┌──────────────┐                    ┌──────────────────┐
│  External     │ ◄── WebSocket ──► │  Channel Plugin   │
│  Application  │    or HTTP        │  (MCP server)     │
└──────────────┘                    └────────┬─────────┘
                                             │ stdio (MCP)
                                      ┌──────▼──────────┐
                                      │  Claude Code     │
                                      │  (interactive    │
                                      │   session)       │
                                      └──────────────────┘
```

Events are **delivered as XML `<channel>` tags** in Claude's context — NOT as raw user prompts. The `instructions` field in the server constructor tells Claude what `<channel>` tag format to expect and how to respond.

- **One-way channels**: Forward alerts, webhooks, CI failures. Claude acts but doesn't reply through the channel. Omit `tools: {}` from capabilities.
- **Two-way channels (chat bridges)**: Expose a `reply` MCP tool. Claude calls it to send messages back.

## Requirements

- **Claude Code v2.1.80+** (v2.1.81+ for permission relay) — research preview
- **Bun**, **Node.js**, or **Deno** (Bun is standard; pre-built plugins use it)
- **`@modelcontextprotocol/sdk`** npm package
- Anthropic auth via claude.ai subscription or Console API key
- **Not available** on Bedrock, Vertex AI, or Foundry
- Team/Enterprise orgs must explicitly enable channels

Channels are in **research preview**. Non-allowlisted channels require `--dangerously-load-development-channels`.

## Starting Claude Code with a Channel

```bash
# During research preview — development flag for local/non-allowlisted channels:
claude --dangerously-load-development-channels server:webhook
claude --dangerously-load-development-channels plugin:myplugin@mymarketplace

# From marketplace (after allowlisting or org policy):
claude --channels plugin:channel-name

# Resume an existing session:
claude -c --dangerously-load-development-channels server:webhook
```

**Important**: `--dangerously-load-development-channels` is per-entry. Combining it with `--channels` does NOT extend bypass to `--channels` entries. Each needs its own.

## Building a Channel Plugin

### Plugin Structure

```
my-channel/
├── .claude-plugin/
│   └── plugin.json          # Metadata (optional; can use raw .mcp.json)
├── server.ts                 # Entry point
├── package.json
└── tsconfig.json
```

### Minimal One-Way Webhook Receiver

This complete example listens on port 8788, forwards every `POST` body to Claude as a `<channel>` tag:

```typescript
#!/usr/bin/env bun
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

// Create the MCP server with channel capability declared
const mcp = new Server(
  { name: 'webhook', version: '0.0.1' },
  {
    capabilities: {
      experimental: { 'claude/channel': {} },  // REQUIRED: registers the notification listener
    },
    // Goes into Claude's system prompt — tells it what <channel> tags to expect
    instructions:
      'Events from the webhook channel arrive as <channel source="webhook" ...>. ' +
      'They are one-way: read them and act, no reply expected.',
  },
);

// Connect to Claude Code over stdio
await mcp.connect(new StdioServerTransport());

// HTTP listener: every POST body forwarded to Claude
Bun.serve({
  port: 8788,
  hostname: '127.0.0.1',  // localhost-only; nothing outside this machine can POST
  async fetch(req) {
    const body = await req.text();
    await mcp.notification({
      method: 'notifications/claude/channel',
      params: {
        content: body,  // becomes the body of the <channel> tag
        meta: { path: new URL(req.url).pathname, method: req.method },
        // each meta key becomes an attribute on the <channel> tag
      },
    });
    return new Response('ok');
  },
});
```

Register in `.mcp.json`:
```json
{
  "mcpServers": {
    "webhook": { "command": "bun", "args": ["./server.ts"] }
  }
}
```

Test:
```bash
claude --dangerously-load-development-channels server:webhook
# In another terminal:
curl -X POST localhost:8788 -d "build failed on main: https://ci.example.com/run/1234"
```

Claude receives:
```xml
<channel source="webhook" path="/" method="POST">
build failed on main: https://ci.example.com/run/1234
</channel>
```

## The Channel Contract

### Server Constructor Options

The `Server` constructor takes `(info, options)` where `options` has:

| Field | Required | Description |
|-------|----------|-------------|
| `capabilities.experimental['claude/channel']` | **Yes** | `{}`. Registers the channel notification listener. |
| `capabilities.experimental['claude/channel/permission']` | No | `{}`. Opts in to permission relay (v2.1.81+). |
| `capabilities.tools` | Two-way only | `{}`. Enables tool discovery for `reply` tool. |
| `instructions` | Recommended | String added to Claude's system prompt. Tell Claude what `<channel>` tag attributes to expect, whether to reply, and which tool to use. |

Do NOT put `tools: {}` for one-way channels. Omit it entirely.

### Notification Format — Pushing Events INTO Claude

Call `mcp.notification()` with method `notifications/claude/channel`:

```typescript
await mcp.notification({
  method: 'notifications/claude/channel',
  params: {
    content: string,           // Required: event body → becomes <channel> tag body
    meta: Record<string, string>, // Optional: each entry becomes a <channel> tag attribute
  },
});
```

**Meta key restrictions**: must be identifiers — letters, digits, and underscores only. Hyphens and other characters are **silently dropped**.

The event arrives in Claude's context as an XML tag:
```xml
<channel source="your-channel" severity="high" run_id="1234">
build failed on main
</channel>
```

The `source` attribute is auto-set from your server name.

**Delivery behavior**: Notifications are NOT acknowledged. `await` resolves when the message is written to the transport — not when Claude processes it. Events queue into the session and are processed in order. Multiple events arriving while Claude is busy are delivered together on the next turn.

### Exposing a Reply Tool — Two-Way Channel

For two-way channels, register a tool that Claude calls to respond. Use `setRequestHandler` with `ListToolsRequestSchema` and `CallToolRequestSchema`:

```typescript
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'reply',
    description: 'Send a message back over this channel',
    inputSchema: {
      type: 'object',
      properties: {
        chat_id: { type: 'string', description: 'The conversation to reply in' },
        text: { type: 'string', description: 'The message to send' },
      },
      required: ['chat_id', 'text'],
    },
  }],
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === 'reply') {
    const { chat_id, text } = req.params.arguments as { chat_id: string; text: string };
    // Send outbound — via WebSocket, SSE, or your chat platform's API
    sendToClient(chat_id, text);
    return { content: [{ type: 'text', text: 'sent' }] };
  }
  throw new Error(`unknown tool: ${req.params.name}`);
});
```

Also update `instructions` so Claude knows to call the reply tool:
```typescript
instructions:
  'Messages arrive as <channel source="webhook" chat_id="...">. ' +
  'Reply with the reply tool, passing the chat_id from the tag.',
```

### Gating Inbound Messages

Gate on **sender identity** (not chat/room identity) before forwarding to Claude. Otherwise it's a prompt injection vector:

```typescript
const allowed = new Set(['dev', 'ci-bot']);

// In your inbound handler:
const sender = req.headers.get('X-Sender') ?? '';
if (!allowed.has(sender)) return new Response('forbidden', { status: 403 });

// Only then forward to Claude:
await mcp.notification({ method: 'notifications/claude/channel', params: { content: body, meta: {} } });
```

The built-in Telegram/Discord channels gate on sender ID from the platform's message object (`message.from.id`, not `message.chat.id` in group chats).

### Permission Relay — Approve Tool Use Remotely

Permission relay (v2.1.81+) forwards Claude Code's tool-use approval prompts to your channel so users can approve/deny from another device. The local terminal dialog stays open too — whichever answer arrives first wins.

**Three components:**

**1. Declare the capability** in `Server` constructor:
```typescript
capabilities: {
  experimental: {
    'claude/channel': {},
    'claude/channel/permission': {},  // opt in to permission relay
  },
  tools: {},
},
```

**2. Handle incoming permission requests** — Claude Code pushes them via `notifications/claude/channel/permission_request`:
```typescript
import { z } from 'zod';

const PermissionRequestSchema = z.object({
  method: z.literal('notifications/claude/channel/permission_request'),
  params: z.object({
    request_id: z.string(),     // 5 lowercase letters (a-km-z, never 'l')
    tool_name: z.string(),      // e.g. "Bash", "Write"
    description: z.string(),    // human-readable summary
    input_preview: z.string(),  // tool args as JSON, truncated to ~200 chars
  }),
});

mcp.setNotificationHandler(PermissionRequestSchema, async ({ params }) => {
  sendToClient(
    `Claude wants to run ${params.tool_name}: ${params.description}\n\n` +
    `Reply "yes ${params.request_id}" or "no ${params.request_id}"`,
  );
});
```

`request_id` is five letters from `a-z` excluding `l` (never ambiguous as `1` or `I`). Only the channel sees this ID — it's not shown in the terminal dialog.

**3. Intercept verdict replies** in your inbound handler. The verdict format is `yes <id>` or `no <id>`. Match it BEFORE forwarding as chat:

```typescript
// [a-km-z] is the ID alphabet (skips 'l'); /i tolerates phone autocorrect caps
const PERMISSION_REPLY_RE = /^\s*(y|yes|n|no)\s+([a-km-z]{5})\s*$/i;

// Inside your inbound message handler, before forwarding to Claude:
const m = PERMISSION_REPLY_RE.exec(body);
if (m) {
  await mcp.notification({
    method: 'notifications/claude/channel/permission',
    params: {
      request_id: m[2].toLowerCase(),  // normalize autocorrect caps
      behavior: m[1].toLowerCase().startsWith('y') ? 'allow' : 'deny',
    },
  });
  return new Response('verdict recorded');
}
// Not a verdict — fall through to normal chat forwarding
```

## Reference Implementations

### `claude-socket` — WebSocket Bridge
**[github.com/cunicopia-dev/claude-socket](https://github.com/cunicopia-dev/claude-socket)** (Apache 2.0) — A general-purpose WebSocket bridge for Claude Code's channel system. Architecture: `App ↔ WebSocket ↔ claude-socket (MCP stdio) ↔ Claude Code`. Supports session multiplexing, permission relay, message history, auto-reconnect, and a zero-dependency browser client.

### Official Plugin Sources
Study these for production patterns (pairing flows, file attachments, message editing):
- [All official channel plugins](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins)
- [fakechat](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/fakechat) — web UI demo with SSE + reply tool

## Augmenting Channels with Hooks

Channels capture what Claude **voluntarily** calls (reply tool). For guaranteed event capture (every tool execution, session lifecycle), combine with **Claude Code hooks**, which fire at lifecycle points and can HTTP POST to a local receiver in your channel plugin.

### Hooks Configuration (for example `~/.claude/settings.json`)

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{"type": "http", "url": "http://127.0.0.1:3101/hook/post-tool-use"}]
    }],
    "Stop": [{
      "matcher": "*",
      "hooks": [{"type": "http", "url": "http://127.0.0.1:3101/hook/stop"}]
    }],
    "SessionStart": [{
      "matcher": "*",
      "hooks": [{"type": "http", "url": "http://127.0.0.1:3101/hook/session-start"}]
    }],
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{"type": "http", "url": "http://127.0.0.1:3101/hook/user-prompt"}]
    }]
  }
}
```

| Hook | Captured Data |
|------|--------------|
| PostToolUse | `tool_name`, `tool_input`, `tool_output`, `tool_call_id`, `tool_error` |
| Stop | `usage` (`input_tokens`, `output_tokens`, `cache_read`, `cache_write`), `stop_reason` |
| SessionStart | `model`, `cwd`, `tools`, `session_id` |
| UserPromptSubmit | `prompt_text`, `timestamp` |

### Hybrid Architecture (Channels + Hooks)

```
┌──────────────────────────────────────────────────────────┐
│                Channel Plugin (Bun process)                │
│                                                          │
│    WebSocket Server (:3100)  ← Your App connects here    │
│    MCP Server (stdio)       ↔ Claude Code                │
│    HTTP Hook Receiver (:3101) ← Hooks POST here          │
│                                                          │
│    Event Bridge:                                          │
│      WS prompt → notifications/claude/channel → Claude    │
│      Hook POST → WS event broadcast                       │
│      Claude reply tool → WS reply event                   │
└──────────────────────────────────────────────────────────┘
```

Channels handle **intentional** communication (prompts, replies). Hooks handle **guaranteed** events (tool execution, session lifecycle).

## Interactive Mode Implications

Using `--channels` means Claude Code runs in **interactive mode** (not `-p` headless). Key constraints:

- **No `--output-format stream-json`** — only works with `--print` / `-p`
- **No per-tool NDJSON on stdout** — stdout is terminal-formatted text
- **No `--include-partial-messages`** (streaming text deltas)
- **Stdout is not machine-readable** — use hooks for event data

Sessions persist automatically to `<CLAUDE_HOME>/projects/<encoded-cwd>/<session-id>.jsonl`. Resume with:

```bash
claude -c --dangerously-load-development-channels server:webhook
claude --resume <session-id> --dangerously-load-development-channels server:webhook
```

## Integration Patterns

### Web UI Bridge
`Browser ↔ WebSocket ↔ channel-plugin (MCP) ↔ Claude Code`
- Map browser UI sessions to `chat_id` in meta attributes
- Broadcast `reply` tool output to all clients viewing that session
- Use hooks for rich event data (tool cards, usage stats)
- Maintain history buffer for late-joining clients

### Chat Platform Bot
`Chat App ↔ Bot API ↔ channel-plugin (MCP) ↔ Claude Code`
- Plugin polls platform API for new messages, pushes as channel notifications
- Uses reply tool to send responses back via platform API
- Gate on `message.from.id`, not `message.chat.id`

### CI/CD Monitor
`CI System → Webhook → channel-plugin → Claude Code`
- One-way channel receives build failures, test results
- Claude investigates and can create commits/PRs
- No reply tool needed

### Multi-Client Session Sharing
Multiple clients share one Claude session: use `--permission-mode acceptEdits` with permission relay, and all clients see the same state and can approve/reject tool calls.

## Comparison: Channels vs Other Approaches

| Feature | `claude -p` | Agent SDK | Channels | Remote Control |
|---------|------------|-----------|----------|----------------|
| **Quota pool** | $20 SDK credit | $20 SDK credit | Main subscription | Main subscription |
| **Session model** | One-shot subprocess | SDK-managed | Long-lived interactive | Long-lived interactive |
| **Event detail** | stream-json (full) | Typed messages (full) | Reply+status (simple) | Terminal UI only |
| **Custom UI** | Parse NDJSON | SDK callbacks | WebSocket/HTTP bridge | claude.ai only |
| **Permissions** | dontAsk flags | canUseTool callback | Channel relay | Terminal prompt |
| **Root bypass** | Blocked v2.1.100+ | Works in SDK | N/A (interactive) | N/A |
| **Multi-turn** | --resume flag | sessionId option | Native (interactive) | Native |

## Common Pitfalls

1. **Wrong notification method.** Must be `notifications/claude/channel` with `{ content, meta }`, NOT `notifications/message`.
2. **No reply tool for two-way.** Without a reply tool, Claude acts on notifications but your client gets no feedback.
3. **No sender gating.** Anyone who can reach your endpoint can inject text into Claude. Gate on sender ID.
4. **Forgetting `instructions`.** Without the `instructions` string, Claude doesn't know what `<channel>` tags to expect or how to reply.
5. **Quota confusion.** `claude --channels` = interactive quota (generous). `claude -p --mcp-config` = SDK credit (limited). The `--channels` flag is what routes to the better pool.
6. **Meta key hyphens.** Meta keys must be identifiers (letters, digits, underscores). Hyphens and special characters are silently dropped from `<channel>` tag attributes.

## Troubleshooting

- **"not on approved allowlist"**: Use `--dangerously-load-development-channels server:name` or `plugin:name@marketplace`.
- **Session lock on resume**: Remove stale `last-prompt` entries from `<CLAUDE_HOME>/projects/<encoded-cwd>/<session-id>.jsonl`.
- **dontAsk silently blocking**: `dontAsk` denies unauthorised tools. Use `acceptEdits` for channels.
- **Hooks not firing**: Use `127.0.0.1` (not `localhost`), check JSON syntax (no trailing commas), respond within 10 seconds.
- **"blocked by org policy"**: Team/Enterprise admin must enable channels in org settings.

## Key Docs

- [Channels reference](https://code.claude.com/docs/en/channels-reference) — the canonical protocol spec
- [Channels overview](https://code.claude.com/docs/en/channels)
- [Hooks reference](https://code.claude.com/docs/en/hooks)
- [MCP guide](https://code.claude.com/docs/en/mcp)
- [Plugin marketplace](https://code.claude.com/docs/en/discover-plugins)
- [Remote Control](https://code.claude.com/docs/en/remote-control)
- [Model Context Protocol](https://modelcontextprotocol.io)
