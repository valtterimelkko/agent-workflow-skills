---
name: pi-extension
description: "Create and debug Pi extensions with custom tools, slash commands, UI components, lifecycle event handlers, compaction hooks, and session persistence. ALWAYS use when extending Pi beyond built-ins or troubleshooting extension API behavior. Covers current @earendil-works ExtensionAPI shapes, registerCommand string arguments, registerTool execute signatures, sendMessage/sendUserMessage, ctx.compact(), ctx.reload(), session entries, and common migration pitfalls from older @mariozechner examples."
---

# Pi Extension Development

Build Pi coding-agent extensions with the **current** ExtensionAPI. Use the Pi documentation and examples that come with your installed Pi package as the canonical source when in doubt. Typical locations are the package `docs/`, `examples/extensions/`, and generated type definitions for the installed version.

When implementing or debugging an extension, read the relevant docs/examples for your installed Pi version first and prefer current examples over memory.

## Current API Quick Start

```typescript
// ~/.pi/agent/extensions/my-extension.ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.registerCommand("hello", {
    description: "Say hello",
    handler: async (args, ctx) => {
      // args is the raw string after /hello, not an object.
      ctx.ui.notify(`Hello ${args.trim() || "world"}!`, "info");
    },
  });

  pi.registerTool({
    name: "greet",
    label: "Greet",
    description: "Greet someone by name",
    parameters: Type.Object({ name: Type.String() }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      return {
        content: [{ type: "text", text: `Hello ${params.name}!` }],
        details: {},
      };
    },
  });
}
```

## Extension Locations

Auto-discovered extensions:

| Location | Scope |
|---|---|
| `~/.pi/agent/extensions/*.ts` | Global top-level file |
| `~/.pi/agent/extensions/*/index.ts` | Global directory extension |
| `.pi/extensions/*.ts` | Project-local top-level file |
| `.pi/extensions/*/index.ts` | Project-local directory extension |

Hot-reload auto-discovered extensions with `/reload`.

## Current Command API

Commands are registered with `handler`, and the first parameter is always a **string** containing the raw command tail.

```typescript
pi.registerCommand("goal", {
  description: "Start a goal",
  getArgumentCompletions: async (prefix) => [{ value: "status", label: "status" }],
  handler: async (args, ctx) => {
    const input = args.trim();
    if (!input) {
      ctx.ui.notify("Usage: /goal <objective>", "warning");
      return;
    }
    // ...
  },
});
```

### Migration pitfall: old object args

Do **not** write new commands like this:

```typescript
// Stale/incorrect for current Pi
pi.registerCommand("goal", {
  args: [{ name: "objective" }],
  execute: async (args, ctx) => args.objective,
});
```

Current Pi does not pass schema-shaped command objects. If compatibility with old code is useful, parse defensively:

```typescript
function parseCommandInput(args: unknown): string {
  if (typeof args === "string") return args.trim();
  const objective = (args as { objective?: unknown } | null)?.objective;
  return typeof objective === "string" ? objective.trim() : "";
}
```

## Current Tool API

Tools use `execute(toolCallId, params, signal, onUpdate, ctx)` and return content blocks.

```typescript
import { Type } from "typebox";
import { StringEnum } from "@earendil-works/pi-ai";

pi.registerTool({
  name: "convert",
  label: "Convert",
  description: "Convert text between formats",
  promptSnippet: "Convert text between json, yaml, and toml",
  parameters: Type.Object({
    format: StringEnum(["json", "yaml", "toml"] as const),
    text: Type.String(),
  }),
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    onUpdate?.({ content: [{ type: "text", text: "Converting..." }] });
    if (signal?.aborted) return { content: [{ type: "text", text: "Cancelled" }] };
    return { content: [{ type: "text", text: params.text }], details: { format: params.format } };
  },
});
```

Use `StringEnum` from `@earendil-works/pi-ai` for string enums, especially for Google-compatible schemas.

## Common Events

Current event names include:

```typescript
pi.on("session_start", async (event, ctx) => {});
pi.on("session_before_compact", async (event, ctx) => {});
pi.on("session_compact", async (event, ctx) => {});
pi.on("session_shutdown", async (event, ctx) => {});
pi.on("before_agent_start", async (event, ctx) => {
  return { systemPrompt: event.systemPrompt + "\n\nExtra instructions" };
});
pi.on("agent_end", async (event, ctx) => {});     // once per user/extension prompt
pi.on("turn_end", async (event, ctx) => {});      // can fire multiple times inside one prompt
pi.on("tool_call", async (event, ctx) => {});
pi.on("tool_result", async (event, ctx) => {});
pi.on("input", async (event, ctx) => ({ action: "continue" }));
```

Use `agent_end` when you want one action after a complete agent run. Use `turn_end` only when you explicitly need every internal LLM/tool round; otherwise you can accidentally queue duplicate follow-up messages.

## UI Methods

```typescript
ctx.ui.notify("Saved", "info");       // "info" | "warning" | "error"
const ok = await ctx.ui.confirm("Delete?", "This cannot be undone");
const choice = await ctx.ui.select("Pick one", ["A", "B"]);
const text = await ctx.ui.editor("Edit text", "initial value");
ctx.ui.setStatus("my-ext", "running");
ctx.ui.setWidget("my-ext", ["line 1", "line 2"]);
```

Do not use unsupported notify types such as `"success"`; use `"info"` unless the message is warning/error.

## Sending Messages

### User messages

```typescript
pi.sendUserMessage("Continue the task");
pi.sendUserMessage("Follow up after current run", { deliverAs: "followUp" });
```

`sendUserMessage()` sends an actual user message and always triggers a turn. If the agent is streaming, provide `deliverAs: "steer" | "followUp"`.

### Custom messages

```typescript
pi.sendMessage(
  {
    customType: "my-extension",
    content: "Context for the model",
    display: true,          // boolean, not a label string
    details: { label: "Optional render metadata" },
  },
  { triggerTurn: true, deliverAs: "followUp" },
);
```

Custom messages participate in context. For state that should **not** be sent to the model, use `pi.appendEntry()` instead.

## Session Persistence

Persist state as custom entries:

```typescript
pi.appendEntry("my-state", { enabled: true, count: 3 });

pi.on("session_start", (_event, ctx) => {
  const entries = ctx.sessionManager.getBranch();
  const latest = [...entries].reverse().find(
    (e) => e.type === "custom" && "customType" in e && e.customType === "my-state",
  );
});
```

Custom entries are not part of LLM context. Custom messages are.

## Compaction Hooks

Use current compaction events for long-running extensions:

```typescript
pi.on("session_before_compact", async (event, ctx) => {
  // event.preparation has messagesToSummarize, previousSummary, tokensBefore, firstKeptEntryId, etc.
  pi.appendEntry("my-state", currentState);
});

pi.on("session_compact", async (event, ctx) => {
  pi.sendMessage(
    {
      customType: "my-context-restored",
      content: "Context compacted. Re-read key files before continuing.",
      display: true,
    },
    { deliverAs: "followUp", triggerTurn: true },
  );
});
```

You can trigger compaction programmatically from event/command contexts with:

```typescript
ctx.compact({
  customInstructions: "Focus on active goal state and modified files",
  onComplete: () => ctx.ui.notify("Compaction complete", "info"),
  onError: (err) => ctx.ui.notify(`Compaction failed: ${err.message}`, "error"),
});
```

## Context and Runtime Helpers

Useful current helpers:

```typescript
ctx.sessionManager.getEntries();
ctx.sessionManager.getBranch();
ctx.sessionManager.getSessionFile();
ctx.getContextUsage();
ctx.getSystemPrompt();
ctx.isIdle();
ctx.hasPendingMessages();
ctx.abort();
ctx.shutdown();
```

Command contexts additionally support session replacement and reload helpers:

```typescript
await ctx.reload();
await ctx.newSession({ withSession: async (newCtx) => newCtx.sendUserMessage("Continue") });
await ctx.switchSession("/path/to/session.jsonl", { withSession: async (newCtx) => {} });
```

After `ctx.reload()`, `ctx.newSession()`, `ctx.fork()`, or `ctx.switchSession()`, do not use captured old `pi` or old `ctx` session-bound objects. Use the replacement callback context where provided.

## Debugging Checklist

1. Read current docs/types, especially `types.d.ts`, before assuming an API shape.
2. Confirm the extension is discovered: top-level `.ts` or directory `index.ts` under an extension folder.
3. Use `/reload` after editing an auto-discovered extension.
4. For command bugs, verify `handler(args, ctx)` treats `args` as a string.
5. For repeated autonomous actions, prefer `agent_end` over `turn_end` unless you need each internal model turn.
6. For compaction bugs, inspect session JSONL for `compaction`, `custom`, and `custom_message`/custom message entries.
7. Use `PI_OFFLINE=1 pi --no-session --no-tools --no-skills -p '/your-command status'` for lightweight command-load smoke tests when the command does not need an LLM.

## Migration Notes from Older Examples

Older extension snippets may show APIs such as:

- `@mariozechner/pi-coding-agent` imports — aliases still often work, but prefer `@earendil-works/pi-coding-agent` in new skills/docs.
- `registerCommand(... execute: ...)` — current API uses `handler`.
- command `args: [{ name }]` metadata and `args.objective` — current command args are raw strings.
- `pi.registerKeyboardShortcut` / `pi.addWidget` / `pi.addOverlay` — current APIs use `registerShortcut`, `ctx.ui.setWidget`, and `ctx.ui.custom(..., { overlay: true })`.
- tool `execute(params, context)` returning plain strings — current tools use `execute(toolCallId, params, signal, onUpdate, ctx)` and content blocks.

When existing code uses a stale pattern, fix the root API mismatch rather than adding symptom workarounds.
