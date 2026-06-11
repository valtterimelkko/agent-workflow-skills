---
name: agy-p
description: "Reference for building scripted and programmatic integrations around the Antigravity CLI (`agy`) non-interactive print mode. ALWAYS use when the user wants to call `agy` from another script, server, subprocess, automation pipeline, CI job, or custom agent harness; when they mention `agy -p`, `agy --print`, `--dangerously-skip-permissions`, conversation resume, headless Antigravity usage, or Google-subscription-backed CLI automation. Covers auth reuse, subprocess patterns, workspace scoping, conversation continuation, stdout caveats, timeouts, logs, permissions, and known sandbox/headless pitfalls." 
---

# agy-p

Use this skill when the task is **not** “how do I use the Antigravity TUI manually?”, but rather:

- “How do I call `agy` from code?”
- “Can another agent/script use my Google-backed Antigravity subscription?”
- “How do I run Antigravity headlessly?”
- “How do I resume an `agy` conversation programmatically?”
- “Why is `agy -p` hanging / asking for permissions / printing weird extra output?”

This skill is about the **CLI subprocess integration path**.

---

## Mental model

`agy` has two distinct modes:

1. **Interactive TUI mode** — plain `agy`
2. **Headless one-shot print mode** — `agy -p` / `agy --print`

For programmatic integrations, prefer **print mode** unless you truly need the live TUI.

The key idea: `agy` authenticates using the same user’s local Antigravity credentials, so a script can usually reuse the existing Google-backed login **without needing a separate API key**.

---

## Fast answer

For a one-shot scripted call, start here:

```bash
agy \
  --dangerously-skip-permissions \
  --print-timeout 10m \
  -p "Summarise the repo and suggest the next 3 actions"
```

Good defaults for integrations:

- set the **working directory** deliberately
- add `--dangerously-skip-permissions` if the task may use tools
- set `--print-timeout` explicitly
- optionally set `--model`
- capture `stdout` and `stderr`
- treat the command as a **subprocess**, not an API

---

## Verified local facts

These were verified locally on this machine with `agy` **1.0.6**:

- Binary path: `<AGY_BIN>`
- `agy --help` exposes: `--print`, `--prompt`, `--dangerously-skip-permissions`, `--print-timeout`, `--model`, `--conversation`, `--continue`, `--sandbox`, `--add-dir`, `--log-file`, `--prompt-interactive`
- `agy --help` also lists shell subcommands: `changelog`, `help`, `install`, `models`, `plugin`, `plugins`, `update`
- `agy models` works non-interactively and currently lists:
  - `Gemini 3.5 Flash (Medium)`
  - `Gemini 3.5 Flash (High)`
  - `Gemini 3.5 Flash (Low)`
  - `Gemini 3.1 Pro (Low)`
  - `Gemini 3.1 Pro (High)`
  - `Claude Sonnet 4.6 (Thinking)`
  - `Claude Opus 4.6 (Thinking)`
  - `GPT-OSS 120B (Medium)`
- A fresh print call like `agy -p "Reply with exactly: AGY_OK"` returned clean stdout
- Output redirection to a file worked locally on Linux in testing
- `--conversation <id>` and `--continue` both worked for follow-up turns
- **Important integration caveat (local observation, not promised contract):** in local testing, resumed print-mode calls emitted prior assistant replies on stdout before the newest reply. Do not assume resumed output is only the latest turn.

---

## Core invocation patterns

### 1) Fresh one-shot call

```bash
agy --dangerously-skip-permissions -p "Explain what this directory does"
```

### 2) Explicit timeout

```bash
agy --dangerously-skip-permissions --print-timeout 15m -p "Run the tests, explain the failures, and suggest a fix"
```

### 3) Explicit model

```bash
agy --dangerously-skip-permissions \
  --model "Gemini 3.5 Flash (Medium)" \
  -p "Summarise the architecture"
```

### 4) Resume a known conversation

```bash
agy --dangerously-skip-permissions \
  --conversation <conversation-id> \
  -p "Continue from the previous context and propose the next step"
```

### 5) Continue the most recent conversation

```bash
agy --dangerously-skip-permissions --continue -p "What should I do next?"
```

### 6) Hybrid start-then-interactive mode

```bash
agy -i "Open the repo and inspect the auth flow"
```

Use `-i` only when you want to **stay interactive** after seeding the prompt.

---

## Programmatic subprocess recipes

### Bash

```bash
#!/usr/bin/env bash
set -euo pipefail

export PATH="/path/to/agy/bin:$PATH"

PROMPT="Summarise the purpose of this repository in 5 bullets."
OUTPUT=$(agy --dangerously-skip-permissions --print-timeout 5m -p "$PROMPT")
printf '%s\n' "$OUTPUT"
```

### Node.js

```javascript
import { spawn } from "node:child_process";

function runAgy({ prompt, cwd, model, conversationId, useContinue = false, timeout = "10m" }) {
  return new Promise((resolve, reject) => {
    const args = ["--dangerously-skip-permissions", "--print-timeout", timeout];

    if (model) args.push("--model", model);
    if (conversationId) args.push("--conversation", conversationId);
    if (useContinue) args.push("--continue");

    args.push("-p", prompt);

    const proc = spawn("agy", args, {
      cwd,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d) => { stdout += d.toString(); });
    proc.stderr.on("data", (d) => { stderr += d.toString(); });

    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`agy exited ${code}\nSTDERR:\n${stderr}\nSTDOUT:\n${stdout}`));
      }
    });
  });
}
```

### Python

```python
import subprocess


def run_agy(prompt, cwd, model=None, conversation_id=None, use_continue=False, timeout="10m"):
    cmd = [
        "agy",
        "--dangerously-skip-permissions",
        "--print-timeout",
        timeout,
    ]

    if model:
        cmd += ["--model", model]
    if conversation_id:
        cmd += ["--conversation", conversation_id]
    if use_continue:
        cmd += ["--continue"]

    cmd += ["-p", prompt]

    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
```

---

## Authentication and subscription reuse

For scripted usage, `agy` usually reuses the **current user’s local login state**.

Relevant files/locations:

- Global settings: `~/.gemini/settings.json`
- Antigravity app data: `~/.gemini/antigravity-cli/`
- Antigravity settings: `~/.gemini/antigravity-cli/settings.json`
- Keybindings: `~/.gemini/antigravity-cli/keybindings.json`
- OAuth credentials commonly present on the machine: `~/.gemini/oauth_creds.json`
- Token file also observed locally: `~/.gemini/antigravity-cli/antigravity-oauth-token`
- Logs: `~/.gemini/antigravity-cli/log/cli-*.log`

Do not print or expose credential file contents in logs, user-facing traces, or telemetry.

Practical guidance:

- Run the subprocess as the **same OS user** who already authenticated in Antigravity.
- Do not invent an API-key flow if the goal is “reuse my CLI subscription/auth state”.
- If auth is missing, `agy` may attempt browser-based sign-in.
- On remote/SSH setups, official docs say it can print a login URL/code flow instead of opening a browser.

---

## Workspace scoping matters

Antigravity scopes work to the launch directory and workspace context.

For integrations, always set `cwd` intentionally.

Why this matters:

- tool access and repo understanding depend on the launch directory
- recent conversation visibility is workspace-sensitive
- project identity may differ between directories
- official Antigravity docs surfaced during research indicate conversation history is scoped to the current working directory

If the integration needs more than one directory in scope, add extra roots with repeated `--add-dir` flags.

Example:

```bash
agy --dangerously-skip-permissions \
  --add-dir /repo/backend \
  --add-dir /repo/shared \
  -p "Check the backend and shared package for duplicated types"
```

---

## Conversation continuity

`agy` exposes two follow-up mechanisms:

- `--conversation <id>` — resume a specific conversation
- `--continue` / `-c` — continue the most recent conversation

### What is a conversation ID?

Locally, Antigravity stores conversations under:

```text
~/.gemini/antigravity-cli/conversations/
```

Observed local format: one SQLite DB per conversation, with filenames like:

```text
24342cb9-f218-4788-b349-5acde3c5df33.db
```

That UUID is usable as the `--conversation` value.

### Important caveat for custom integrations

In local testing on `agy` 1.0.6, resuming with `--conversation` or `--continue` caused stdout to include **earlier assistant final replies before the newest one**. Treat this as an observed behaviour, not a documented stable contract.

Example shape observed:

```text
PREVIOUS_REPLY
PREVIOUS_REPLY_2
NEWEST_REPLY
```

So if you are building a multi-turn wrapper:

- do **not** assume resumed stdout is a single clean answer
- parse defensively
- consider taking the **last non-empty block/line** as the newest answer if your prompt format guarantees that shape
- better yet, ask the model to wrap the final answer in a delimiter you can parse reliably

Example prompt pattern:

```text
Return your final answer only inside:
<AGY_FINAL>
...
</AGY_FINAL>
```

Then parse the last tagged block from stdout.

### Discovering the new conversation ID

There is no verified JSON event stream documented for `agy -p` yet. In practice, an integration may need to:

1. snapshot `~/.gemini/antigravity-cli/conversations/` before the call
2. run a fresh `agy -p ...`
3. inspect the newest/newly-created `*.db` file afterward

Treat this as a pragmatic filesystem-based workaround, not a guaranteed formal API.

---

## Permissions and safety

### Why `--dangerously-skip-permissions` matters

Without it, headless runs can stall when the agent wants approval for:

- running commands
- editing files
- reading outside the default workspace
- other tool actions

For automation, this flag is often necessary.

### But it is genuinely dangerous

It effectively auto-approves tool actions. Only use it when:

- the workspace is controlled
- the prompt is trusted
- the execution environment is appropriately isolated

### Sandbox warning

The docs present `--sandbox` as a way to restrict terminal execution, but public issue tracker research found an open issue showing that combining:

```bash
--sandbox --dangerously-skip-permissions
```

may undermine sandbox guarantees by auto-approving sandbox bypass prompts.

As of June 2026, treat this combination as **not a strong security boundary** unless you have independently verified the behaviour in your exact environment/version.

If you need real isolation, prefer external containment such as:

- a container
- a VM
- a locked-down dedicated workspace user
- filesystem/network restrictions outside Antigravity itself

---

## Headless reliability notes

Public issue tracker research shows at least one open `1.0.6` bug report for `agy -p` hanging in some non-TTY headless environments, especially Windows / redirected subprocess scenarios.

Local Linux testing here did succeed for:

- plain `agy -p`
- redirected stdout to file
- resumed conversations via `--conversation`

So the right guidance is:

- **test in the exact target environment**
- do not assume Linux and Windows behave the same
- add watchdog timeouts at the parent-process level even if you also set `--print-timeout`

A robust wrapper should enforce both:

1. `agy --print-timeout ...`
2. an outer subprocess timeout from the parent language/runtime

---

## Models

List models dynamically with:

```bash
agy models
```

Do not hardcode the full model catalogue forever; it can change.

If the integration accepts a model name from a user, either:

- validate it against `agy models`, or
- provide a controlled allowlist sourced from a recent `agy models` check.

---

## Logs and debugging

When scripted runs fail, inspect:

- `stderr` from the subprocess
- latest CLI logs in `~/.gemini/antigravity-cli/log/cli-*.log`

Useful commands:

```bash
agy --version
agy --help
agy models
agy plugin list
ls -lt ~/.gemini/antigravity-cli/log/cli-*.log | head
```

If you need per-run logfile isolation, pass `--log-file /absolute/path/to/agy.log` and archive that alongside stdout/stderr in your wrapper.

Useful things to read:

- `~/.gemini/settings.json`
- `~/.gemini/antigravity-cli/settings.json`
- `~/.gemini/antigravity-cli/keybindings.json`
- the latest log file

Look for signs of:

- auth failure
- missing workspace access
- permission-review blocking
- model lookup failure
- sandbox behaviour surprises

---

## Plugins and related commands

Programmatic wrappers may also need these shell-level commands:

- `agy help`
- `agy plugin list`
- `agy plugins` (alias surface)
- `agy plugin install <target>`
- `agy plugin enable <name>`
- `agy plugin disable <name>`
- `agy plugin validate [path]`
- `agy update`
- `agy changelog`
- `agy install --help`

This is still all **shell CLI surface**, not an HTTP API.

---

## Recommended wrapper policy

If you are designing a reusable integration layer, prefer this policy:

1. **Verify binary first** with `agy --version`
2. **Verify auth state indirectly** with a trivial `agy -p` smoke test
3. **Pin `cwd` explicitly**
4. **Set `--print-timeout` explicitly**
5. **Use `--dangerously-skip-permissions` only when needed**
6. **Capture stdout, stderr, exit code, duration**
7. **Inspect logs on failure**
8. **Treat resumed-conversation stdout as parseable-but-messy**
9. **Add an outer timeout in the parent process**
10. **Use external sandboxing if risk matters**

---

## Suggested smoke tests

### Minimal

```bash
agy -p "Reply with exactly: OK"
```

### Tool-using

```bash
agy --dangerously-skip-permissions -p "List the files in the current directory and summarise what kind of project this is"
```

### Resume-specific

```bash
agy --dangerously-skip-permissions -p "Reply with exactly: TURN1"
# detect newest conversation ID
agy --dangerously-skip-permissions --conversation <id> -p "Reply with exactly: TURN2"
```

Check whether the second stdout contains only `TURN2` or accumulated prior replies too.

---

## What to say when advising a user

When the user wants a custom integration, the default recommendation is:

- yes, `agy` has a programmatic path via `-p` / `--print`
- yes, it can usually reuse the same user’s local Antigravity/Google subscription login
- yes, another script/agent can spawn it as a subprocess
- but it is **CLI automation**, not a stable formal SDK/API
- you must handle permissions, timeouts, cwd/workspace scoping, and resume-output quirks carefully

If the user needs a more durable machine interface than subprocess wrapping, say so plainly.

---

## Verification checklist

Before concluding an integration design is sound, verify all of these:

- `agy --version` works
- `agy models` works
- a fresh `agy -p` call works
- auth is already available for the target OS user
- the chosen `cwd` is correct
- any required extra roots are passed with `--add-dir`
- permission behaviour is understood
- timeout behaviour is tested
- resumed conversation parsing is tested
- `--log-file` behaviour is tested if you rely on custom run logs
- logs are readable on failure
- security boundaries do not rely solely on `--sandbox` + `--dangerously-skip-permissions`

If you need to inspect behaviour rather than guess, run the real command and look at the latest files in `~/.gemini/antigravity-cli/`.
