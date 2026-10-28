# Programme kit

Copy these files into your programme's operations directory (outside every work tree, e.g. `<ops root>/<programme>/`), then replace each `<placeholder>`.

```bash
KIT=<path to this skill>/assets/programme-kit
OPS=<ops root>/<programme>
mkdir -p $OPS && cp $KIT/STATE.md $OPS/STATE.md
cp $KIT/COMMON-host.md $OPS/COMMON.md      # or COMMON-cloud.md for cloud children
cp $KIT/objectives.sh $OPS/objectives.sh
# per lane:
mkdir -p $OPS/<lane> && cp $KIT/lane-brief.md $OPS/<lane>/brief.md
# per review / correction:
cp $KIT/review-brief.md $OPS/reviews/<lane>.md
cp $KIT/correction-brief.md $OPS/<lane>/NN-correction.md
# or run a whole lane with `pi-orch lane run` (default for single-repo lanes with GATES): lane.json + brief.md + review-brief.md in one dir
cp $KIT/lane.json $KIT/review-brief.md $OPS/<lane>/   # then add brief.md
```

- `STATE.md` is the only file you re-read after compaction: keep it ≤ 60 lines, with the RESUME block current.
- `COMMON-*.md` holds programme-wide rules only. The hand-back protocol and host traps live in the `agent-os-child` skill; do not copy them.
- `lane-brief.md` aims for ≤ 800 words and **one** hand-back marker. The `GATES:` block at the end is machine-readable; copy it into the goal's `--goal-verify` where the runtime supports it.
- Principles: `references/multi-phase.md`. Runbooks (verification, merge, deploy, close-out): `references/programme-kit.md`.
- `lane.json` is the template for `pi-orch lane run <lane-dir>` (the default for single-repo lanes with a GATES block): a cheap Class 1 implementer with a cross-family reviewer. Set an absolute `cwd`, the `owner` field (your retention id) and `parentSessionId`, and pick `selector` values from live `/models`; the lane dir also needs `brief.md` (ending in `GATES:`) and `review-brief.md` (with `VERDICT FILE:`). See `references/pi-orch.md`.
