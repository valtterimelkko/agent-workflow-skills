---
name: claude-p
description: "Use when running multi-turn Claude Code CLI sessions programmatically via 'claude -p', integrating Claude into server-side processes, handling stream-json output, managing session continuity across turns, or building systems that spawn claude subprocesses. ALWAYS use when: spawning claude -p subprocesses, handling 'Session ID already in use' errors, working with --session-id vs --resume flags, parsing stream-json events, or implementing Claude Direct-style session management. Covers subprocess lifecycle, session locking, event normalization, token usage extraction, and common pitfalls that cause follow-up messages to silently fail."
---

# claude -p Skill

A reference for using `claude -p` (non-interactive print mode) to run Claude Code sessions programmatically — particularly for multi-turn conversations in server-side code.

This is the **direct CLI approach**, not the Claude Agent SDK. The key binary is `claude`, authenticated via `claude auth login` (subscription auth).

---

## Core invocation

```bash
claude -p "your prompt" \
  --output-format stream-json \
  --verbose \
  --permission-mode acceptEdits \
  --model sonnet \
  --session-id <uuid>     # first turn only — see below
```

`--output-format stream-json --verbose` is required together: `stream-json` alone is rejected in `-p` mode without `--verbose`.

### Auth: subscription, not API key

```typescript
const env = { ...process.env };
delete env.ANTHROPIC_API_KEY;      // forces subscription auth
delete env.ANTHROPIC_AUTH_TOKEN;   // forces subscription auth
// Claude reads <CLAUDE_HOME>/ credentials automatically
```

Check auth status:
```bash
claude auth status --json           # correct flag
# NOT: --output-format json         # wrong, will error
```

---

## Multi-turn sessions — the critical distinction

Claude Code uses a **per-session-id file lock**. The lock persists for several seconds (sometimes indefinitely) after the subprocess exits. This is the single most common source of failures.

### Rule: first turn vs follow-up turns

| Turn | Flag | Why |
|------|------|-----|
| First | `--session-id <uuid>` | Creates the session file |
| Follow-up | `--resume <uuid>` | Continues without triggering the lock |

**`--session-id` on a follow-up always fails with "Session ID already in use"** — even seconds after the first process exited.

```typescript
const sessionFlag = isFirstTurn
  ? ['--session-id', claudeSessionId]
  : ['--resume', claudeSessionId];

spawn('claude', ['-p', prompt, '--output-format', 'stream-json',
  '--verbose', '--permission-mode', 'acceptEdits',
  '--model', model, ...sessionFlag], { ... });
```

Track "has had a first turn" per session:
```typescript
private sessionsWithHistory = new Set<string>();
// After successful first turn:
sessionsWithHistory.add(sessionId);
// On subsequent turns: isFirstTurn = !sessionsWithHistory.has(sessionId)
```

Also check `entry.messageCount > 0` from persistent storage as a fallback for server restarts.

### Capture the confirmed session ID

Claude may assign a slightly different session_id than the one you passed. Always capture it from the `system` event output:

```typescript
// In the stream-json system event:
// {"type":"system","session_id":"<actual-uuid>",...}
// Use THIS id for --resume, not necessarily what you passed to --session-id
```

### Stdin must be closed

Always use `stdio: ['ignore', 'pipe', 'pipe']`. If stdin stays open, Claude waits up to 3 seconds for piped input and warns:
> "no stdin data received in 3s, proceeding without it"

This also means the process lingers and the session lock is held longer.

---

## Subprocess spawn pattern

```typescript
const proc = spawn('claude', [
  '-p', prompt,
  '--output-format', 'stream-json',
  '--verbose',
  '--permission-mode', 'acceptEdits',
  '--model', model,               // 'sonnet' | 'opus' | 'haiku'
  ...sessionFlag,
], {
  cwd: workingDirectory,
  env: claudeEnv,                 // with API keys stripped
  stdio: ['ignore', 'pipe', 'pipe'],
});
```

Stream stdout line-by-line with `readline`:
```typescript
const rl = createInterface({ input: proc.stdout, crlfDelay: Infinity });
rl.on('line', (line) => {
  const events = normalizer.normalize(line, sessionId);
  events.forEach(onEvent);
});
```

Emit `agent_end` **on process exit**, not on receiving the `result` event:
```typescript
proc.on('exit', (code, signal) => {
  rl.close();
  activeProcesses.delete(sessionId);
  if (code !== 0 && signal !== 'SIGTERM') {
    onComplete(new Error(`claude exited ${code}`));
  } else {
    onEvent({ type: 'agent_end', ... });
    onComplete();
  }
});
```

If you emit `agent_end` when the `result` event arrives (before process exit), the UI becomes interactive again while the session lock is still held — the next prompt will fail.

---

## stream-json event sequence

```
{"type":"system","subtype":"init","session_id":"<uuid>","tools":[...],"model":"claude-sonnet-4-6",...}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_...","name":"Read","input":{...}}],...},...}
{"type":"rate_limit_event","rate_limit_info":{"status":"allowed","rateLimitType":"five_hour","isUsingOverage":false,...},...}
{"type":"user","message":{"content":[{"type":"tool_result","content":"...","tool_use_id":"toolu_...","is_error":false}]},...}
{"type":"assistant","message":{"content":[{"type":"text","text":"The file contains..."}],...},...}
{"type":"result","subtype":"success","result":"...","session_id":"<uuid>","usage":{...},"total_cost_usd":0.05,...}
```

### Token usage IS available

The `result` event exposes full token data — don't return zeros:
```typescript
// result event data:
{
  usage: {
    input_tokens: 3,
    cache_creation_input_tokens: 12413,
    cache_read_input_tokens: 11171,
    output_tokens: 54
  },
  total_cost_usd: 0.05
}
```

### Event → NormalizedEvent mapping

| stream-json type | Normalized type | Notes |
|---|---|---|
| `system` (init) | `session_init` | Capture `session_id` here |
| `assistant` (tool_use content) | `tool_execution_start` | One per tool block |
| `user` (tool_result content) | `tool_execution_end` | Matches by `tool_use_id` |
| `assistant` (text content) | `message_start` + `message_update` + `message_end` | Emit all three |
| `rate_limit_event` | `rate_limit` | Forward quota info to UI |
| `result` | `claude_result` | Store usage; emit `agent_end` on subprocess exit instead |
| (subprocess exit) | `agent_end` | Emit here, not from `result` |

---

## Session concurrency

Each session UUID is independent — multiple sessions can run simultaneously without interfering. The lock is per-UUID.

Within a single session, only one turn can run at a time. Queue follow-up prompts server-side:

```typescript
if (isRunning(sessionId)) {
  // Wait for current turn to finish before spawning next
  await waitUntilIdle(sessionId, 30_000);
}
```

If a second `claude -p` starts for a session that hasn't fully released its lock, retry with backoff (the lock typically releases within a few seconds of process exit when using `--resume`):

```typescript
proc.on('exit', (code) => {
  if (code !== 0 && stderr.includes('is already in use') && retries < 5) {
    const delay = 1500 + retries * 1000;
    setTimeout(() => spawn(options, onEvent, onComplete, retries + 1), delay);
    return;
  }
  // ... normal completion
});
```

---

## Model aliases

Claude Code subscription accepts short aliases — use these, not provider-qualified IDs:

| Alias | Maps to |
|---|---|
| `sonnet` | Latest Sonnet |
| `opus` | Latest Opus |
| `haiku` | Latest Haiku |

**Don't** pass `anthropic/sonnet` or `claude-sonnet-4-6` — those work in the API but may fail or behave unexpectedly via the CLI subscription path.

Normalize any incoming model string:
```typescript
function normalizeAlias(model: string): 'opus' | 'sonnet' | 'haiku' {
  const lower = model.toLowerCase();
  if (lower.includes('opus')) return 'opus';
  if (lower.includes('haiku')) return 'haiku';
  return 'sonnet';
}
```

---

## Session files

Claude stores session history in:
```
<CLAUDE_HOME>/projects/<cwd-encoded>/<session-uuid>.jsonl
```

This is Claude Code's internal format — don't write to it. Maintain your own session log (a separate JSONL) if you need to replay history to reconnecting clients.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `--session-id` on follow-up turns | "Session ID already in use", silent failure | Use `--resume` for turns 2+ |
| Emitting `agent_end` from `result` event | UI accepts input while session is locked | Emit `agent_end` on subprocess exit only |
| `stdin: 'pipe'` (open stdin) | 3s delay + lingering lock | Use `stdio: ['ignore', 'pipe', 'pipe']` |
| `ANTHROPIC_API_KEY` in subprocess env | Uses API billing instead of subscription | Strip API key from subprocess env |
| `claude auth status --output-format json` | Command errors | Use `--json` flag |
| Returning zeros for token/cost | Misleads users; data is available | Read from `result.usage` and `result.total_cost_usd` |
| Adding session stats that show "N/A" for Claude Direct | Confusing UI | Actually parse `result` event — token data is there |
| Treating session info endpoint as unsupported for Claude Direct | Missing feature | It's implementable; the `result` event has full usage data |

The last two rows reflect a specific anti-pattern: an implementation was added that returned zero tokens/cost for Claude sessions under the assumption the data wasn't available. It was reverted because the data IS in the `result` event — always parse it rather than returning placeholder values.
