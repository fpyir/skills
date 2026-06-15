# PR Stack Storage Format

Stack records use two files with the same stem:

- `*.toml`: current stack topology.
- `*.events.jsonl`: append-only durable history.

## TOML Topology

Each `*.toml` file stores only current topology:

```toml
version = 1

[stack]
id = "ABC-123"
title = "Build todo app with stacked PRs"
base_ref = "main"

[repo]
github = "example-org/todo-app"
workspace = "/Users/you/code/todo-app"

[[prs]]
id = "ABC-124"
title = "Add todo model and CRUD API routes"
tickets = ["ABC-124"]
branch = "your-name/abc-124-todo-api"
parent = "stack-base"
base_ref = "main"
github_pr = 42
notes = "Durable handoff notes only."
```

See `examples/abc-123-todo-app-stack.toml` for a fuller two-PR stack.

## Fields

- `version`: currently `1`.
- `[stack].id`: stable stack id, usually the issue tracker story key.
- `[stack].title`: human title for the stack.
- `[stack].base_ref`: repository base for the bottom PR, usually `main`.
- `[repo].github`: GitHub repository as `owner/name`.
- `[repo].workspace`: absolute local checkout path.
- `[[prs]].id`: stable PR record id, often an issue tracker ticket key.
- `[[prs]].title`: PR title.
- `[[prs]].tickets`: issue tracker tickets covered by this PR.
- `[[prs]].branch`: Git branch for the PR head.
- `[[prs]].parent`: previous PR id, or `stack-base` for the bottom PR.
- `[[prs]].base_ref`: current GitHub base ref for the PR. This can be the stack base or a PR branch. After a parent is merged, this may be retargeted to `main` while `parent` still records logical stack topology.
- `[[prs]].github_pr`: GitHub PR number.
- `[[prs]].notes`: durable handoff details, decisions, or context.

Do not store CI state, reviewers, issue tracker status, merge commits, deleted branch state, workflow phase, sync state, or temporary plans in TOML.

## Event Logs

Each matching `*.events.jsonl` file stores durable history. It is append-only: one compact JSON object per line.

```json
{"date":"2026-06-15","kind":"add-pr","summary":"Added ABC-124 at the bottom of the stack.","pr_ids":["ABC-124"],"notes":""}
```

Event keys are exactly:

- `date`
- `kind`
- `summary`
- `pr_ids`
- `notes`

Use `record-event` for ordinary event updates instead of hand-editing JSONL.

See `examples/abc-123-todo-app-stack.events.jsonl` and `examples/abc-200-todo-due-dates-stack.events.jsonl` for sample event history.

## Direct Editing

Use direct edits only when the CLI cannot express the required repair.

- Read the target TOML and event log first.
- Keep TOML limited to current topology and durable PR notes.
- Keep event logs append-only; do not rewrite history unless the user explicitly requests a correction.
- Preserve all unrelated stack entries and events.
- Run `python3 stack.py validate <stack>` after manual edits.
- Run `python3 -m unittest tests/test_stack_cli.py` from the skill directory after changing `stack.py`.
