#!/usr/bin/env bash
# Single-line goal objectives, one variable per lane. The goal API rejects newlines,
# so the long text stays in the brief file. Source this file, then pass "$OBJ_<LANE>" to
# `pi-orch spawn --goal-objective` / `pi-orch goal <sid> start --goal-objective`.
PARENT="<parent session id>"; OPS="<ops dir>"
OBJ_A="You are an orchestrated child worker: load and follow the orchestrated-child-worker skill. Your session ID is <child sid>; parent session ${PARENT}. Work strictly inside worktree <path> on branch <branch>; owned paths <paths>; never touch <no-go paths>. Read ${OPS}/COMMON.md then ${OPS}/A/brief.md and deliver <outcome> test-first. Done when <gate command> exits 0 and ${OPS}/A/complete.md is written ending with FROZEN. Never push, merge, restart services or touch production. Success criteria are frozen. Then mark the goal achieved and end your turn."
OBJ_A1="You are an orchestrated child worker: load and follow the orchestrated-child-worker skill. Correction 1 for lane A: work strictly inside the same worktree and owned paths, read ${OPS}/A/01-correction.md and deliver its items test-first. Done when <gate command> exits 0 and a Correction 1 section is appended to ${OPS}/A/complete.md with FROZEN last. Then mark the goal achieved and end your turn."
