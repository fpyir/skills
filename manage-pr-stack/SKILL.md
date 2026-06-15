---
name: manage-pr-stack
description: Manage PR stacks. Use when the user mentions a PR stack, stacked PRs, a Jira story used as a stack identifier, stack records, descendants, rebasing a stack, force-pushing stack branches, importing GitHub PRs into a stack, or updating stack state across GitHub, Jira, local git, and durable stack files.
---

# Manage PR Stack

## Overview

Use this skill to coordinate stacked PR work through structured stack records in this skill directory. The canonical records live in `stacks/*.toml`, with append-only event history in matching `stacks/*.events.jsonl` files.

The stack files are durable coordination state, not a live mirror of GitHub, Jira, or local git. GitHub, Jira, and local git remain authoritative for current external facts when a requested operation depends on them.

Use `stack.py` as the normal interface for reading and updating stack records. Direct TOML or JSONL edits are a fallback for careful repairs that the CLI cannot express.

## Package Files

- `stack.py`: CLI for stack discovery, inspection, validation, topology updates, event logging, and GitHub PR import.
- `docs/storage-format.md`: TOML stack and JSONL event-log format reference.
- `docs/cli-reference.md`: command reference and examples for `stack.py`.
- `stacks/*.toml`: ignored local stack records for real current work.
- `stacks/*.events.jsonl`: ignored local event logs for real current work.
- `examples/*.toml`: tracked example stack records.
- `examples/*.events.jsonl`: tracked example event logs.
- `scripts/stack-rebase`: helper for dry-running, rebasing, and force-pushing linear PR stack branches with explicit `--onto` boundaries and `--force-with-lease`.

## Core Rules

- Prefer `stack.py` for every stack read or write. It understands selectors, validates topology, appends events, and keeps TOML rendering consistent. See `docs/cli-reference.md` for command details.
- Preserve real stack data under `stacks/`. That directory is ignored by git because it contains the user's current local state.
- Do not store transient execution plans in stack files. Store current topology in TOML and durable history in the event log. See `docs/storage-format.md` for the storage contract.
- Do not add compatibility layers, legacy fields, or references to previous formats unless the user explicitly asks.
- Do not refresh external state on first read without a concrete reason. Refresh GitHub, Jira, origin, or local git when the user's request depends on current state, local refs are stale, topology is ambiguous, or a remote operation is about to be performed.
- A direct command such as "rebase the PR for DEL-1878 and rebase the rest of the stack" counts as approval to fetch, inspect current remote state, rebase affected branches, resolve straightforward conflicts, and force-push rebased branches when that is necessary to complete the requested stack operation.
- A direct command such as "I've just pushed a minor adjustment to del-1876; update the PR stack" means propagate the parent branch change through descendants: fetch, identify descendants, rebase in order, resolve straightforward conflicts, force-push rebased descendants, and record what changed.
- Treat "update the PR stack" as an operational request to make the stack current. Treat "update the stack record", "update the stack file", or "record this" as a record-only request.
- Stop and ask before continuing if a rebase conflict is non-trivial, the worktree is dirty with unrelated changes, observed branch topology differs from the stack record, the operation would affect branches outside the requested stack, or the command's intent is ambiguous.
- Do not transition Jira, request reviewers, change GitHub PR bases, merge PRs, or post Slack messages unless the user explicitly requests that external write.
- Use the existing workflow skills for phase-specific work: `implement-ticket`, `raise-my-pr`, `review-pr-feedback`, and `prepare-review-request`.

## Common Workflows

### Locate A Stack

1. Extract Jira story keys, implementation ticket IDs, PR numbers, PR URLs, and branch names from the request.
2. Use `python3 stack.py find <query>` with the most specific identifier first.
3. If exactly one stack matches, use it.
4. If multiple stacks match, show candidates and ask the user to choose.
5. If no stack exists and the user asked to create one, use `add-stack`. Otherwise ask whether to create it.

### Read Stack Context

1. Use `show` for topology and PR URLs.
2. Use `tip` when deciding where a new PR should be based.
3. Use `descendants` when a parent changed, merged, or needs rebasing.
4. Use `validate` before acting on topology.
5. Query GitHub, Jira, origin, or local git only when current external facts matter.

### Add Or Update A PR

1. Prefer `import-pr` when a GitHub PR already exists and `gh` is available.
2. Use `add-to-stack` when the user supplies the needed PR identity, branch, and PR number.
3. Use `--parent` and `--base-ref` only for non-tip insertion or explicit topology repairs.
4. Validate after mutation.
5. Do not add Jira status, reviewers, CI state, merge commits, branch deletion state, or workflow phase fields.

### Mark A Parent Merged

1. Confirm whether the user wants a record-only update or actual GitHub/local branch work.
2. If record-only, use `mark-merged <stack> <target> --base <ref>`.
3. If descendants need rebasing, use `descendants` and `rebase-plan`, then perform the stack rebase workflow if authorized.
4. Record an event describing completed durable work.

### Propagate A Pushed Parent Change

Use this when the user says a branch was pushed or adjusted and asks to update the PR stack.

1. Locate and validate the stack.
2. Fetch origin and inspect local/remote refs for the changed branch and descendants.
3. Identify descendants with `descendants`.
4. Generate a `rebase-plan` from the changed PR onto the requested or inferred parent.
5. Dry-run `scripts/stack-rebase`.
6. Rebase each descendant in order and force-push because the user requested stack propagation.
7. Stop and ask if conflicts are non-trivial, a descendant branch is missing, the local worktree contains unrelated dirty changes, or observed topology differs from the stack record.
8. Append a concise event naming the changed parent and rebased descendant range.

### Prepare A Stack Operation

Use this for rebases, force-pushes, changing PR bases, or stack-wide sync work.

1. Locate the stack, validate it, and gather the external facts needed for the operation.
2. If the user directly requested the operation, proceed without asking for second approval when topology is clear and conflicts are straightforward.
3. Present the proposed operation before acting when the request is exploratory, broad, ambiguous, or risky.
4. Include affected PRs, branch/base sequence, expected force-pushes, and risks when proposing or reporting the operation.
5. Stop and ask if conflicts are non-trivial, branch topology does not match the stack record, or any affected branch is outside the requested stack.
6. After approved or directly requested work is complete, update durable stack state and append an event.

### Coordinate With Other Skills

- After `raise-my-pr`, use `import-pr` or `add-to-stack` for the matching PR.
- Before `implement-ticket`, read stack context if the ticket appears in a stack and surface parent/descendant constraints.
- After `review-pr-feedback`, record durable stack history only if the feedback caused a meaningful stack state change.
- After `prepare-review-request`, record durable stack history only if there is useful handoff context.
