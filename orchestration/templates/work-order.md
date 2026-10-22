---
id: {id}
title: {title}
status: draft
assignee: {assignee}
fallback: true
size: {size}
phase: {phase}
depends_on: [{depends_on}]
gpu: {gpu}
playtest: false
created: {created}
---
## Goal
One or two sentences: what exists when this is done, and why it matters.

## Context
- Read first: `AGENTS.md`, plus any design doc sections that apply (`docs/design-decisions.md` §…).
- Related work orders / existing code to build on:

## Files in scope
- `path/to/file_or_folder`  (create | modify)

Out of scope: anything not listed. If you need to touch another file, keep it minimal and say why in your report.

## Requirements
1.
2.
3.

## Acceptance criteria
- [ ] Concrete, checkable outcome
- [ ] Tests added or updated, and they pass (`orchestration/config.json` → `test_command`)
- [ ] Report written to `orchestration/reports/{id}.md`

## Notes for the worker
Hints, constraints, gotchas, examples of expected data. Delete if none.
