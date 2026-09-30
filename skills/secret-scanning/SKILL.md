---
name: secret-scanning
description: "Scan git repositories and directories for committed credentials with gitleaks, and keep credentials out of repos entirely. Use this skill before making any repository public, before the first push of a new repo, before publishing or copying evidence, logs, transcripts or skills into a repo, when adding secret scanning to CI or a pre-commit hook, when auditing an already-public repo's history, and whenever a task handled credential copies (auth.json, models.json with apiKey, tokens). Also use it when someone asks 'is this safe to publish?', 'did we leak a key?', or mentions gitleaks, secret scanning or credential hygiene."
---

# Secret scanning

The goal is to keep credentials out of repositories. Scanning is the check; the
design rule comes first:

> **Credentials live outside the repo tree.** Code reads them from paths or
> environment variables that point outside the repository (for example
> `~/.pi-web-ui/internal-api-token`), and should refuse a credential path that
> resolves inside its own repo. `.gitignore` is only a backstop: one `git add -f`
> or one renamed file defeats it.

## The tool: gitleaks

`gitleaks` is a single binary and needs no account or human step. Check it with
`gitleaks version`. If it is missing, install a pinned release and verify the checksum:

```bash
V=8.30.1; D=$(mktemp -d); cd "$D"
curl -sSfL -o gl.tgz "https://github.com/gitleaks/gitleaks/releases/download/v$V/gitleaks_${V}_linux_x64.tar.gz"
curl -sSfL -o sums.txt "https://github.com/gitleaks/gitleaks/releases/download/v$V/gitleaks_${V}_checksums.txt"
grep "gitleaks_${V}_linux_x64.tar.gz" sums.txt | sed "s/gitleaks_${V}_linux_x64.tar.gz/gl.tgz/" | sha256sum -c -
tar xzf gl.tgz gitleaks && install -m 0755 gitleaks /usr/local/bin/gitleaks; cd /; rm -rf "$D"
```

## Never print a secret

**Always pass `--redact`.** Never print, paste, quote or store a matched value,
including in reports, commit messages, chat or evidence files. Not even partly, and
not "masked in context". Triage from metadata only: rule id, file, line, commit,
the key *name* that matched, and whether the file still exists at HEAD. On some hosts
the agent's permission layer blocks commands that would expose credential values.
Treat that block as correct; do not work around it.

## Commands

| Need | Command |
|---|---|
| Full history of a repo (before publishing; public-repo audit) | `gitleaks git --redact -v <repo>` |
| Working tree or any directory (evidence before copying it into a repo) | `gitleaks dir --redact -v <path>` |
| Only unpushed commits | `gitleaks git --redact --log-opts="origin/main..HEAD" <repo>` |
| Staged changes (pre-commit) | `gitleaks git --pre-commit --staged --redact -v` |
| Machine-readable triage | add `--report-format json --report-path /tmp/gl.json` (the report is redacted too; delete it afterwards) |

Exit code `1` means findings; `0` means none were found.

## Triage

Classify every finding. Most hits of the broad `generic-api-key` rule are harmless.

1. **Identifier false positive:** idempotency keys, UUIDs, digests, config words
   (for example `NoNewPrivileges`). Allowlist them.
2. **Deliberate test fixture:** a fake key planted to test redaction. Prefer an
   obviously fake shape (`sk-test-FAKE…`), and allowlist it.
3. **Possibly real:** anything else, especially in docs, scripts, logs or evidence.
   Treat it as real until its owner confirms otherwise.

For a possibly real credential:
- **Rotate or revoke it first.** Rewriting history does not un-leak a secret that
  was ever public: clones, forks and caches keep it.
- Then tell the owner, with the location (file, line, commit), never the value.
- Rewriting history (`git filter-repo`) and force-pushing are the **owner's
  decision**. Never do them unasked.

## Allowlisting without hiding real leaks

- `.gitleaksignore` holds finding **fingerprints** (`commit:file:rule:line`, no
  secret values). Add a fingerprint only after triage says it is a false positive
  or a fixture.
- An inline `gitleaks:allow` comment on a fixture line also works.
- **Baseline for legacy history:** `gitleaks git --report-path baseline.json …`
  once, then run `--baseline-path baseline.json` in CI, so only *new* findings fail.
  A baseline accepts the old findings; triage them before baselining, and never
  baseline a possibly real credential.

## CI and hooks

GitHub Actions (the official action needs no licence for a personal account's repo):

```yaml
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
```

A local pre-commit hook (`.git/hooks/pre-commit`) is a personal choice: describe it
in the repo's maintainer docs, and don't install it into someone else's clone:

```bash
#!/bin/sh
exec gitleaks git --pre-commit --staged --redact
```

## Before publishing checklist

1. `gitleaks git --redact -v .` over full history, then `gitleaks dir --redact .`.
2. Grep for host-specific or personal data a scanner won't flag: absolute host paths,
   internal hostnames, emails, real session ids, private repo names.
3. Confirm code reads credentials only from outside the repo, and prove the tests
   pass on a machine without your private checkout (for example, `HOME` pointed at an
   empty temp dir).
4. Add the CI job.
5. An independent reviewer re-runs the scan before the first public push.
