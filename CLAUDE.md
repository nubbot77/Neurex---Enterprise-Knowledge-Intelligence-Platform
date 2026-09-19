# Project instructions

## Keep `docs/Handover.md` current — every completed task

`docs/Handover.md` is the single source of truth for project state. It goes stale the
moment it lags the code, and a stale handover is worse than none: the next session
starts work that is already done.

**Whenever a task from `docs/backend_tasks.md` is finished — or a phase's status
changes — update `docs/Handover.md` in the same turn, before reporting the work as
done.** This is not optional and does not need to be asked for.

What to update, in this order:

1. **`**Last updated:**`** — today's date, absolute.
2. **`**Progress:**`** — completed phases and the running `N of 34 phases` count.
3. **§1 Where to pick up** — the next unstarted task, by phase and task number.
4. **The phase's task table** — flip `⬜` to `✅`, and mark the phase heading `✅`
   when every task in it is done.
5. **§5 Gotchas** — add anything that cost real time, with the evidence that settled
   it. Gotchas are the most valuable part of the file.
6. **§6 Loose ends** — re-check it. Items about uncommitted files, missing tests or
   unpinned images go stale fastest.

Claims in the handover are load-bearing, so only write what was verified. "Migrations
round-trip cleanly" means the round-trip was run; say what was run and when.

## Conventions worth not re-deriving

- Task list and phase numbering: `docs/backend_tasks.md` (34 phases) is authoritative.
  `docs/plan.md` numbers the same work differently — its Phase 2 is the task list's
  Phase 4.
- Identity, tenancy and RBAC rules: `docs/architecture.md` §7. Read it before touching
  anything that decides who may do what.
- Backend layout: `backend/src/` on the import path via `pythonpath`; nothing is
  pip-installed (`[tool.uv] package = false`). One wrapper level only, and never
  repeat a name across nesting levels.
- Run things with `uv run` from `backend/`.
