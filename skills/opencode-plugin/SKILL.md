---
name: opencode-plugin
description: "Develop, install, troubleshoot, and integrate OpenCode plugins for the opencode CLI. Use when: writing new OpenCode plugins, porting Pi SDK extensions to OpenCode, registering custom tools via the plugin API, fixing plugin load failures, resolving module dependency issues in plugins, installing plugins globally or per-project, understanding the plugin hook system, or any task involving @opencode-ai/plugin, opencode plugin command, or opencode.json plugin config. Covers: plugin format, Hooks API, tool registration, lifecycle hooks, module resolution, installation methods, edge cases, and troubleshooting."
---

# OpenCode Plugin Development Guide

Complete guide for developing, installing, and troubleshooting plugins for the OpenCode CLI (`opencode`). Validated against OpenCode v1.14.20 and `@opencode-ai/plugin` v1.14.19.

## Plugin Architecture

OpenCode plugins are **ESM JavaScript modules** that export an async function. The function receives a `PluginInput` and returns `Promise<Hooks>`. Plugins register custom tools, hook into the agent lifecycle, and modify behavior at runtime.

```
Plugin function called once at load time
  -> returns Hooks object
    -> hooks are called per-event during the session
```

### Plugin File Structure

```
my-plugin/
├── package.json     # Must have "type": "module", "main": "index.js"
└── index.js         # The plugin code (ESM)
```

Minimal `package.json`:

```json
{
  "name": "my-opencode-plugin",
  "version": "1.0.0",
  "type": "module",
  "main": "index.js",
  "peerDependencies": {
    "@opencode-ai/plugin": ">=1.14.0"
  }
}
```

### Minimal Plugin

```javascript
export default async function MyPlugin(input) {
  return {
    // hooks go here
  };
}
```

This is a valid plugin that does nothing. Every hook is optional.

## The Plugin Function

### PluginInput

The plugin function receives a single argument with these fields:

```javascript
export default async function MyPlugin(input) {
  input.client        // OpenCode SDK client (for server API calls)
  input.project       // Project metadata object
  input.directory     // Project root directory (e.g., "~/my-project")
  input.worktree      // Project worktree root
  input.serverUrl     // URL object for the OpenCode server
  input.$             // BunShell instance for running shell commands
  input.experimental_workspace  // Workspace registration API
}
```

Key fields you'll use most:
- **`input.directory`** — the project root. Use this to derive project slugs, locate config files, resolve relative paths.
- **`input.$`** — BunShell for running commands. Usage: `await $\`git status\`.cwd(dir).quiet().text()`
- **`input.client`** — OpenCode SDK client for making API calls to the running server.

### Hooks

The plugin returns a `Hooks` object. Every hook is optional — only implement what you need.

```javascript
export default async function MyPlugin(input) {
  return {
    tool: { /* register custom tools */ },
    event: async ({ event }) => { /* raw SSE events */ },
    "experimental.chat.system.transform": async (input, output) => { /* inject into system prompt */ },
    "tool.execute.before": async (input, output) => { /* before tool execution */ },
    "tool.execute.after": async (input, output) => { /* after tool execution */ },
    "experimental.session.compacting": async (input, output) => { /* before context compaction */ },
    "chat.message": async (input, output) => { /* new message received */ },
    "chat.params": async (input, output) => { /* modify LLM parameters */ },
    "permission.ask": async (input, output) => { /* modify permission behavior */ },
    "shell.env": async (input, output) => { /* modify shell environment */ },
  };
}
```

## Registering Custom Tools

Tools are registered in the `tool` hook as a map of tool name → tool definition.

### The `tool()` Helper

Import from `@opencode-ai/plugin/tool`:

```javascript
import { tool } from "@opencode-ai/plugin/tool";
```

The `tool()` function takes an object with `description`, `args`, and `execute`:

```javascript
tool({
  description: "What this tool does. The LLM reads this to decide when to use it.",
  args: {
    action: tool.schema.enum(["create", "delete"]),
    name: tool.schema.string().describe("Name of the thing"),
    count: tool.schema.number().optional().describe("How many"),
  },
  async execute(args, context) {
    // args is typed: { action: "create"|"delete", name: string, count?: number }
    // Return a string or { output: string, metadata?: {...} }
    return `Created ${args.name}`;
  },
})
```

`tool.schema` is the Zod library (v4). Available types:
- `tool.schema.string()`, `tool.schema.number()`, `tool.schema.boolean()`
- `tool.schema.enum(["a", "b", "c"])`
- `.optional()`, `.describe("...")`, `.default(value)`

### Tool Execute Context

```javascript
async execute(args, ctx) {
  ctx.sessionID    // current session ID
  ctx.messageID    // current message ID
  ctx.agent        // agent name (e.g., "build")
  ctx.directory    // project directory for this session
  ctx.worktree     // worktree root
  ctx.abort        // AbortSignal for cancellation
  ctx.metadata({ title: "doing X", metadata: { key: "val" } })  // update display
}
```

### Tool Return Values

```javascript
// Simple string
return "Done.";

// With metadata
return {
  output: "Created 3 items",
  metadata: { count: 3, items: [...] }
};
```

### Multi-Action Tool Pattern

When a tool has multiple actions (like "save", "search", "delete"), use an enum parameter and switch on it:

```javascript
tool({
  description: "Manage items. Use 'create' to add, 'list' to view, 'delete' to remove.",
  args: {
    action: tool.schema.enum(["create", "list", "delete"]),
    name: tool.schema.string().optional(),
  },
  async execute(args, ctx) {
    switch (args.action) {
      case "create":
        if (!args.name) return { output: "Error: name required for create", metadata: { error: true } };
        // ... create logic
        return { output: `Created ${args.name}` };
      case "list":
        // ... list logic
        return { output: "Items: ..." };
      case "delete":
        // ... delete logic
        return { output: `Deleted ${args.name}` };
    }
  },
})
```

### Registering Multiple Tools

```javascript
return {
  tool: {
    my_first_tool: tool({ /* ... */ }),
    my_second_tool: tool({ /* ... */ }),
    my_third_tool: tool({ /* ... */ }),
  },
};
```

Tool names in the map become the tool IDs the LLM sees.

## Key Hooks Reference

### `"experimental.chat.system.transform"`

Inject content into the system prompt every turn. This is how you give the LLM persistent context.

```javascript
"experimental.chat.system.transform": async (input, output) => {
  // input.sessionID? — current session (may be undefined)
  // input.model — the model being used
  // output.system — string array, push to append
  output.system.push("<my-context>\nImportant info for the LLM\n</my-context>");
},
```

### `"tool.execute.after"`

Called after every tool execution. Use for logging, extraction, side effects.

```javascript
"tool.execute.after": async (input, output) => {
  // input.tool — tool name (e.g., "read", "bash", "my_custom_tool")
  // input.sessionID — session ID
  // input.callID — call ID
  // input.args — the arguments passed to the tool
  // output.title — displayed title
  // output.output — the tool's output text
  // output.metadata — the tool's metadata
},
```

### `"tool.execute.before"`

Called before every tool execution. Use for validation, modification, or logging.

```javascript
"tool.execute.before": async (input, output) => {
  // input.tool — tool name
  // input.sessionID — session ID
  // input.callID — call ID
  // output.args — you can modify the args before execution
},
```

### `"experimental.session.compacting"`

Called before context compaction. Use to persist data that should survive compaction.

```javascript
"experimental.session.compacting": async (input, output) => {
  // input.sessionID — session being compacted
  // output.context — string array, push context strings to preserve
  // output.prompt — if set, replaces the default compaction prompt entirely
  output.context.push("Key info to preserve: ...");
},
```

### `"event"`

Raw SSE events. Receives every event the OpenCode server emits.

```javascript
event: async ({ event }) => {
  // event.type — event type string
  // event.properties — event payload
},
```

### `"shell.env"`

Modify environment variables for shell commands.

```javascript
"shell.env": async (input, output) => {
  // input.cwd — working directory
  // output.env — env var map, modify in place
  output.env["MY_VAR"] = "my_value";
},
```

### `"chat.message"`

Called when a new user message is received.

```javascript
"chat.message": async (input, output) => {
  // input.sessionID
  // input.agent, input.model, input.messageID
  // output.message — UserMessage object
  // output.parts — Part[] array
},
```

### `"permission.ask"`

Modify permission behavior for tool execution.

```javascript
"permission.ask": async (input, output) => {
  // input — the Permission object
  // output.status — "ask" (default), "deny", or "allow"
  // Set to "allow" to auto-approve, "deny" to auto-deny
},
```

## Plugin Installation

### Installing a Plugin

```bash
# Install from npm
opencode plugin my-plugin-package

# Install from local path
opencode plugin /path/to/my-plugin

# Install globally (in ~/.config/opencode/)
opencode plugin /path/to/my-plugin -g

# Force reinstall
opencode plugin /path/to/my-plugin -g --force
```

### What `opencode plugin` Does

1. Installs the package via npm into the config directory's `node_modules/`
2. Adds the plugin reference to `opencode.json` under the `"plugin"` key
3. The plugin loads on next `opencode serve` start

### Plugin Config Format

In `opencode.json`:

```json
{
  "plugin": [
    "npm-package-name",
    "/absolute/path/to/local/plugin",
    ["plugin-with-options", { "debug": true }]
  ]
}
```

Plugins can be:
- An npm package name (string)
- An absolute local path (string starting with `/`)
- A tuple of `[name/path, options]` where options are passed as the second argument to the plugin function

### Global vs Project Config

- **Global**: `~/.config/opencode/opencode.json` — applies to all projects
- **Project**: `<project>/.opencode/opencode.json` — project-specific

## Module Resolution (Critical Edge Case)

This is the #1 source of plugin failures.

### The Problem

When a plugin is installed via **local path**, OpenCode loads it from that path. But `import` statements like `import { tool } from "@opencode-ai/plugin/tool"` resolve relative to the plugin's directory, NOT relative to the config directory's `node_modules/`. This causes `Cannot find module` errors.

**You will see this in logs as:**
```
ERROR service=plugin path=file:///path/to/plugin error=Cannot find module '@opencode-ai/plugin/tool'
```

### The Fix: Create Symlinks

For each local plugin, create a `node_modules` directory with symlinks to the config directory's packages:

```bash
# For each plugin that imports from @opencode-ai/plugin or zod:
mkdir -p /path/to/my-plugin/node_modules
ln -sf ~/.config/opencode/node_modules/@opencode-ai /path/to/my-plugin/node_modules/@opencode-ai
ln -sf ~/.config/opencode/node_modules/zod /path/to/my-plugin/node_modules/zod
```

This ensures all imports resolve correctly regardless of where the plugin code lives.

### Alternative: Inline the Helper

The `tool()` helper is trivial — it just returns its input and attaches Zod:

```javascript
// Instead of: import { tool } from "@opencode-ai/plugin/tool"
import { z } from "zod";
function tool(input) { return input; }
tool.schema = z;
```

But you still need `zod` to resolve, so the symlink approach is cleaner.

### What's Available Without Symlinks

These Node.js built-in modules always work (no imports needed beyond Node):
- `node:fs/promises`, `node:path`, `node:os`, `node:crypto`
- `node:child_process`, `node:util`, `node:stream`
- Any standard Node.js built-in

## State Management

### Per-Session State

Plugins are loaded once. Use closure variables keyed by `sessionID` for per-session state:

```javascript
const sessions = new Map();

function getSession(sessionID) {
  if (!sessions.has(sessionID)) {
    sessions.set(sessionID, {
      turnCount: 0,
      data: [],
    });
  }
  return sessions.get(sessionID);
}

export default async function MyPlugin(input) {
  return {
    "tool.execute.after": async (input) => {
      const session = getSession(input.sessionID);
      session.turnCount++;
    },
  };
}
```

### Global State

State in the plugin closure survives across sessions within the same `opencode serve` process. It's lost on server restart. Persist important data to disk:

```javascript
import * as fs from "node:fs/promises";
import * as path from "node:path";

async function saveData(filePath, data) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(data), "utf-8");
}

async function loadData(filePath) {
  try { return JSON.parse(await fs.readFile(filePath, "utf-8")); }
  catch { return null; }
}
```

### What Persists Across Restarts

- **Disk files** — anything written to `~/.opencode/` or project dirs
- **Config** — `opencode.json` plugin entries
- **Git state** — worktrees, branches, etc.

### What Doesn't Persist Across Restarts

- In-memory Maps and state variables
- The worktree registry (but actual git worktrees survive on disk)
- Session state cache (reload from disk on startup)

## Shell Commands in Plugins

Use `input.$` (BunShell) for running commands:

```javascript
export default async function MyPlugin(input) {
  const $ = input.$;

  return {
    tool: {
      mytool: tool({
        description: "Runs things",
        args: { cmd: tool.schema.string() },
        async execute(args, ctx) {
          // Simple command
          const output = await $\`git status\`.cwd(ctx.directory).quiet().text();

          // With environment
          const result = await $.env({ PATH: "/usr/bin" })\`echo hello\`.quiet().text();

          // Don't throw on non-zero exit
          const out = await $\`some-command\`.nothrow().quiet().text();

          return output;
        },
      }),
    },
  };
}
```

Alternatively, use Node.js `child_process`:

```javascript
import { exec as execCb } from "node:child_process";
import { promisify } from "node:util";
const execAsync = promisify(execCb);

const { stdout } = await execAsync("git status", { cwd: directory, maxBuffer: 10 * 1024 * 1024 });
```

Node `exec` is often simpler for dynamic arguments. BunShell's template literal doesn't handle variable interpolation in command arguments well.

## Complete Plugin Examples

### Example 1: Simple Note-Taking Tool

```javascript
import { tool } from "@opencode-ai/plugin/tool";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import * as os from "node:os";

const NOTES_DIR = path.join(os.homedir(), ".opencode", "notes");

async function ensureDir(d) { await fs.mkdir(d, { recursive: true }); }

export default async function NotesPlugin(input) {
  return {
    tool: {
      notes: tool({
        description: "Manage project notes. Save and retrieve notes for this project.",
        args: {
          action: tool.schema.enum(["save", "read", "list", "delete"]),
          title: tool.schema.string().optional().describe("Note title"),
          content: tool.schema.string().optional().describe("Note content"),
        },
        async execute(args, ctx) {
          const projectNotes = path.join(NOTES_DIR, path.basename(ctx.directory));
          await ensureDir(projectNotes);

          switch (args.action) {
            case "save": {
              if (!args.title || !args.content) return "Error: title and content required";
              const filePath = path.join(projectNotes, `${args.title}.md`);
              await fs.writeFile(filePath, args.content);
              return `Saved note: ${args.title}`;
            }
            case "read": {
              if (!args.title) return "Error: title required";
              const content = await fs.readFile(
                path.join(projectNotes, `${args.title}.md`), "utf-8"
              ).catch(() => null);
              return content || `Note "${args.title}" not found`;
            }
            case "list": {
              const files = await fs.readdir(projectNotes).catch(() => []);
              return files.length > 0
                ? `Notes:\n${files.map(f => `- ${f.replace(".md", "")}`).join("\n")}`
                : "No notes yet";
            }
            case "delete": {
              if (!args.title) return "Error: title required";
              await fs.unlink(path.join(projectNotes, `${args.title}.md`)).catch(() => {});
              return `Deleted note: ${args.title}`;
            }
          }
        },
      }),
    },
  };
}
```

### Example 2: Auto-Documentation Tool with System Prompt Injection

```javascript
import { tool } from "@opencode-ai/plugin/tool";
import * as fs from "node:fs/promises";
import * as path from "node:path";

const docBuffer = new Map();

export default async function AutoDocPlugin(input) {
  const projectDir = input.directory;
  const docPath = path.join(projectDir, "AUTO_API_DOC.md");

  async function loadDoc() {
    try { return await fs.readFile(docPath, "utf-8"); }
    catch { return ""; }
  }

  return {
    tool: {
      document_api: tool({
        description: "Document an API endpoint or function. Records documentation that persists across sessions.",
        args: {
          name: tool.schema.string().describe("Function/endpoint name"),
          description: tool.schema.string().describe("What it does"),
          params: tool.schema.string().optional().describe("Parameters as JSON"),
          returns: tool.schema.string().optional().describe("Return value"),
        },
        async execute(args, ctx) {
          let doc = (await loadDoc()) || "# API Documentation\n\n";
          const entry = `\n## ${args.name}\n${args.description}\n` +
            (args.params ? `\n**Params**: ${args.params}\n` : "") +
            (args.returns ? `\n**Returns**: ${args.returns}\n` : "");
          doc += entry;
          await fs.writeFile(docPath, doc);
          return `Documented: ${args.name}`;
        },
      }),
    },

    "experimental.chat.system.transform": async (input, output) => {
      const doc = await loadDoc();
      if (doc) {
        output.system.push(`<api-docs>\n${doc}\n</api-docs>`);
      }
    },

    "experimental.session.compacting": async (input, output) => {
      const doc = await loadDoc();
      if (doc) output.context.push(doc);
    },
  };
}
```

### Example 3: Porting a Pi SDK Extension

When porting from Pi SDK's `pi.registerTool()` / `pi.on()` pattern:

| Pi SDK | OpenCode Plugin |
|---|---|
| `pi.registerTool({ name: "x", ... })` | `tool: { x: tool({ ... }) }` |
| `pi.registerCommand("x", ...)` | No equivalent — use tools instead |
| `pi.on("session_start", fn)` | Load state in plugin function body |
| `pi.on("before_agent_start", fn)` | `"experimental.chat.system.transform"` hook |
| `pi.on("turn_end", fn)` | `"tool.execute.after"` hook (approximate) |
| `pi.on("tool_call", fn)` | `"tool.execute.before"` hook |
| `pi.on("tool_result", fn)` | `"tool.execute.after"` hook |
| `pi.on("session_before_compact", fn)` | `"experimental.session.compacting"` hook |
| `ctx.sessionManager.getSessionFile()` | Use `ctx.sessionID` + disk paths |
| `ctx.cwd` | `input.directory` or `ctx.directory` (in tool execute) |
| Pi TypeBox schemas (`Type.Object`) | Zod schemas (`tool.schema`) |
| `pi-tui` rendering (Box, Text) | Not available — tools return strings |

Key differences when porting:
- **No slash commands**: OpenCode plugins can't register `/commands`. Use tools instead.
- **No TUI rendering**: Return plain strings from tools, not TUI components.
- **Schema change**: TypeBox (`Type.Object({...})`) → Zod (`{ key: tool.schema.string() }`)
- **State initialization**: Do it in the plugin function body, not in a "session_start" handler.

## Troubleshooting

### Plugin Not Loading

Check logs for `ERROR service=plugin`:

```bash
# If running via opencode serve, check stderr for:
# ERROR service=plugin path=... error=Cannot find module '...'
```

Common causes:
1. **Module resolution failure** — see "Module Resolution" section above
2. **Missing `"type": "module"`** in package.json — plugins MUST be ESM
3. **Syntax error** in plugin code — test with `node -e "import('/path/to/plugin/index.js').then(m => console.log(typeof m.default))"`
4. **Wrong export** — must export `default` as an async function

### Plugin Loads But Tools Don't Appear

- Tool names in the `tool` map must match exactly what's returned
- Check that `tool()` helper is called correctly (description, args, execute)
- Verify the tool description isn't empty — the LLM won't use tools without descriptions

### Module Resolution Errors

The error looks like:
```
Cannot find module '@opencode-ai/plugin/tool' from '/path/to/plugin/index.js'
```

Fix: create symlinks (see "Module Resolution" section). Verify with:
```bash
node -e "import('/path/to/plugin/index.js').then(m => console.log('OK:', typeof m.default)).catch(e => console.error('FAIL:', e.message))"
```

### Plugin Causes OpenCode to Crash

- Wrap all hook bodies in try/catch — a thrown error in a hook can crash the server
- Don't do synchronous blocking I/O in hooks
- Don't modify `output` properties that aren't documented

### Verifying Plugin Installation

```bash
# Check config
cat ~/.config/opencode/opencode.json | grep -A5 plugin

# Check the plugin loads
node -e "import('/path/to/plugin/index.js').then(m => console.log('Plugin loads, type:', typeof m.default))"

# List installed packages
ls ~/.config/opencode/node_modules/ | grep -i plugin-name
```

### Testing Without Restarting

For local path plugins, you can edit the plugin code in place. Changes take effect on the next `opencode serve` start. There's no hot reload.

### Running Without Plugins

```bash
opencode serve --pure --port 4096
```

The `--pure` flag disables all external plugins. Useful for isolating plugin-caused issues.

## Installation Persistence

Plugins survive:
- **`opencode upgrade`** — config file and local paths aren't touched
- **System reboots** — config is on disk, systemd restarts the service
- **Pi Web UI restarts** — Pi Web UI starts a new `opencode serve` which re-reads config

Plugins DON'T survive:
- **In-memory state** — lost on any process restart (persist to disk)
- **API breaking changes** — major OpenCode version bumps may change the Hooks interface

## Security Considerations

- Plugins run in the same process as OpenCode — they have full access
- Validate inputs in tool execute functions before passing to shell commands
- Don't expose secrets in tool descriptions or metadata
- Use `ctx.abort` to respect cancellation signals
- Don't write to arbitrary paths — validate and sanitize user input
