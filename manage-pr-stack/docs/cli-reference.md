# PR Stack CLI Reference

Run the CLI from the skill directory:

```bash
cd manage-pr-stack
python3 stack.py list
```

The default stack directory is `./stacks` relative to the skill directory.

Use `--stacks-dir PATH` for examples, tests, or temporary fixtures:

```bash
python3 stack.py --stacks-dir examples list
```

Use global `--json` before the command when structured output is useful:

```bash
python3 stack.py --json show ABC-123
```

Stack selectors can be the stack id, filename, filename stem, or a direct TOML path. PR selectors can be a PR id, ticket, branch, or GitHub PR number; `descendants` and `rebase-plan` also accept `stack-base`.

## Read Commands

```bash
python3 stack.py list
python3 stack.py show ABC-123
python3 stack.py find ABC-124
python3 stack.py tip ABC-123
python3 stack.py descendants ABC-123 ABC-124
```

- `list`: stack id, title, repo, PR count, and tip branch.
- `show <stack>`: PRs in stack order with tickets, branch, parent, base ref, and GitHub PR URL.
- `find <query>`: search stack id, title, filename, PR id, ticket, branch, and GitHub PR number.
- `tip <stack>`: current stack tip.
- `descendants <stack> <pr-or-branch>`: downstream PRs in stack order.

Use `--json` for automation:

```bash
python3 stack.py --json descendants ABC-123 ABC-124
```

## Validation

Validate before and after non-trivial changes:

```bash
python3 stack.py validate ABC-123
```

Validation checks:

- schema version and required `[stack]`, `[repo]`, and `[[prs]]` fields
- duplicate PR ids, branches, and GitHub PR numbers
- parent references
- `base_ref` values against stack base or known PR branches
- event log JSONL shape
- event `pr_ids` against known PR ids or tickets

If validation fails, fix the stack record before using it for branch operations. Do not proceed with rebases or force-pushes from an invalid topology unless the user explicitly accepts the risk.

## Mutation Commands

Create a stack:

```bash
python3 stack.py add-stack \
  --id ABC-123 \
  --title "Build todo app with stacked PRs" \
  --github example-org/todo-app \
  --workspace /Users/you/code/todo-app \
  --base-ref main
```

Append a new PR at the top of a stack:

```bash
python3 stack.py add-to-stack ABC-123 \
  --title "Add todo list UI with create and toggle" \
  --ticket ABC-125 \
  --branch your-name/abc-125-todo-list-ui \
  --github-pr 43 \
  --notes "Durable context only."
```

By default, `add-to-stack` uses the current stack tip as parent and the tip branch as base ref. Use `--parent` and `--base-ref` only when adding a PR that is not based on the current tip.

Import or refresh a PR from GitHub:

```bash
python3 stack.py import-pr ABC-123 43
```

`import-pr` uses `gh pr view` and the stack's `[repo].github`. It fails without editing if `gh` is unavailable, GitHub metadata is incomplete, or a new PR is not based on the current stack tip.

Record an event without changing topology:

```bash
python3 stack.py record-event ABC-123 \
  --kind refresh \
  --summary "Checked GitHub PR bases and local refs." \
  --pr ABC-124 \
  --notes "No topology changes."
```

Mark a PR as merged in the stack record:

```bash
python3 stack.py mark-merged ABC-200 ABC-201 --base main --notes "Squash-merged upstream."
```

`mark-merged` retargets immediate descendants' `base_ref` to `--base`, appends a merge event, and can append durable notes to the merged PR. It does not merge the PR, delete branches, store merge commits, update reviewers, or transition issue tracker tickets.

## Rebase Planning

Use `rebase-plan` to generate input for `scripts/stack-rebase`. It performs no git operations:

```bash
python3 stack.py rebase-plan ABC-123 --from ABC-124 --onto origin/main
```

The text output is TSV shaped as:

```text
branch<TAB>new_parent<TAB>old_parent
branch<TAB>new_parent
```

For operational rebases:

1. Locate and validate the stack.
2. Fetch the repo and inspect current refs when needed.
3. Generate a rebase plan from the affected PR or `stack-base`.
4. Dry-run with `scripts/stack-rebase`.
5. Execute and push only when the dry-run is clean and the user's request authorizes the operation.
6. Record a concise event after successful work.

Example:

```bash
python3 stack.py rebase-plan ABC-123 --from ABC-124 --onto origin/main > /tmp/stack.tsv
./scripts/stack-rebase \
  --repo /Users/you/code/todo-app \
  --fetch \
  --plan /tmp/stack.tsv
```

When the dry-run is clean and execution is authorized:

```bash
./scripts/stack-rebase \
  --repo /Users/you/code/todo-app \
  --plan /tmp/stack.tsv \
  --execute \
  --push
```
