---
name: review-wo
description: Review a finished work order (status 'review') - check tests, the worker's report and a cross-review by the other agent, then merge it or send it back for rework. Use when Zack says "review WO-xxx", "review what's done", or when the foreman loop finds work in review.
---

# Reviewing a work order

`WO` = `python orchestration/scripts/wo.py`. The worker's files are in its worktree: `../<repo>-worktrees/<WO-ID>/`.

1. **Facts first (cheap):**
   - `orchestration/runs/<WO-ID>/<latest>/summary.json`: exit code, tests PASS/FAIL, commits.
   - The worker's report: `../<repo>-worktrees/<WO-ID>/orchestration/reports/<WO-ID>.md`.
   - Tests FAIL, or zero commits, means rework straight away. Quote the failure.
2. **Cross-review** for any M-size work, anything touching autoloads/schemas/the AI service, or anything that looks off:
   `WO review <WO-ID>`. This runs the *other* agent read-only, so Codex reviews Claude's work and Claude reviews Codex's. Read the `review_file` it prints.
3. **Your check:** go through the acceptance criteria one by one against the report and the verdict. Open diffs only for MUST FIX items or criteria you can't verify any other way (`git -C <worktree> diff main...HEAD --stat` first).
4. **Decide:**
   - **Approve:** if `playtest: true`, stop and ask Zack to try it first. Tell him the worktree path and the "How to test" steps. Otherwise `WO merge <WO-ID>`, then `git add orchestration docs && git commit -m "Foreman: merged <WO-ID>"`, and tick the roadmap checkbox if this finishes an item.
   - **Rework:** `WO rework <WO-ID> "<specific, numbered fixes>"`, then `WO dispatch <WO-ID>`. Notes must be specific enough for an agent with no context.
   - **Second rework still failing:** the work order is the problem, not the worker. Re-scope it, split it, or switch the assignee (`WO set <WO-ID> assignee=claude`).
5. Report back to Zack in one line per work order: merged, in rework (why), or waiting on him.
